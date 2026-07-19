import os
import json
import base64
import logging
from http.server import BaseHTTPRequestHandler

import gspread
from google.oauth2.service_account import Credentials
import requests


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


TRIGGER_DAYS = int(os.getenv('TRIGGER_DAYS', '7'))
SHEET_ID = os.getenv('SHEET_ID', '')
SHEET_TAB = os.getenv('SHEET_TAB', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '')
GOOGLE_CREDENTIALS_B64 = os.getenv('GOOGLE_CREDENTIALS_B64', '')


COL_DUE_DATE = 'Due Date'
COL_COUNTDOWN = 'Countdown (Days)'
COL_ACTIONS = 'ACTIONS'
COL_PIC = 'PIC'
COL_PROGRESS = 'PROGRESS'

SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def is_vercel_cron(headers):
    return 'x-vercel-cron-schedule' in headers


def load_google_creds():
    if not GOOGLE_CREDENTIALS_B64:
        raise ValueError('GOOGLE_CREDENTIALS_B64 env var is empty')

    creds_json = base64.b64decode(GOOGLE_CREDENTIALS_B64).decode('utf-8')
    creds_dict = json.loads(creds_json)

    return Credentials.from_service_account_info(creds_dict,
                                                 scopes=SHEETS_SCOPES)


def fetch_due_rows():
    creds = load_google_creds()
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    worksheet = sheet.worksheet(SHEET_TAB)
    all_values = worksheet.get_all_values()
    if not all_values:
        logger.warning('Sheet "%s" is empty', SHEET_TAB)
        return []

    raw_headers = all_values[0]
    header_indices = {}
    for idx, h in enumerate(raw_headers):
        key = str(h).strip()
        if key and key not in header_indices:
            header_indices[key] = idx

    records = []
    for row in all_values[1:]:
        record = {}
        for key, idx in header_indices.items():
            record[key] = row[idx] if idx < len(row) else ''
        records.append(record)

    logger.info('Read %d rows from sheet "%s"', len(records), SHEET_TAB)

    due_rows = []

    for i, row in enumerate(records, start=2):
        try:
            actions = str(row.get(COL_ACTIONS, '')).strip()
            if not actions:
                continue

            countdown_raw = row.get(COL_COUNTDOWN)
            try:
                countdown = float(countdown_raw)
            except (TypeError, ValueError):
                logger.warning('Row %d: non-numeric countdown "%s", skipping',
                               i, countdown_raw)
                continue

            progress = str(row.get(COL_PROGRESS, '')).strip()
            if progress.upper() == 'COMPLETED':
                continue

            if 0 <= countdown < TRIGGER_DAYS:
                due_date = str(row.get(COL_DUE_DATE, '')).strip()
                pic = str(row.get(COL_PIC, '')).strip()

                if countdown == int(countdown):
                    countdown_disp = int(countdown)
                else:
                    countdown_disp = countdown

                due_rows.append({
                    'actions': actions,
                    'pic': pic,
                    'due_date': due_date,
                    'countdown': countdown_disp,
                    'progress': progress if progress else '(no status)',
                })

        except Exception:
            logger.error('Row %d: unexpected error', i, exc_info=True)
            continue

    logger.info('Found %d row(s) due within %d days',
                len(due_rows), TRIGGER_DAYS)
    return due_rows


def build_message(due_rows):
    if not due_rows:
        return (
            "StanexBot Daily Check-in\n"
            "\n"
            "All clear! No tasks are due in the next "
            f"{TRIGGER_DAYS} days. The team is on top of everything.\n"
            "\n"
            "---\n"
            "This is an automated message from StanexBot"
        )

    header = ("StanexBot Daily Check-in" if len(due_rows) <= 2
              else f"StanexBot Daily Check-in - {len(due_rows)} tasks need attention")

    lines = [
        header,
        "",
        f"{len(due_rows)} task(s) approaching deadline in the next {TRIGGER_DAYS} days:",
        "",
    ]

    for i, row in enumerate(due_rows, start=1):
        days = ("1 day" if row['countdown'] == 1
                else f"{row['countdown']} days")
        urgency = "URGENT" if row['countdown'] <= 2 else ""
        detail = []
        if row['pic']:
            detail.append(f"PIC: {row['pic']}")
        if row['due_date']:
            detail.append(f"Due: {row['due_date']}")
        detail.append(f"{days} remaining")
        status_tag = f"[{row['progress']}]"
        if urgency:
            status_tag = f"[{row['progress']}]  {urgency}"
        detail.append(status_tag)

        lines.append(f"{i}. {row['actions']}")
        lines.append(f"   {'  |  '.join(detail)}")
        lines.append("")

    lines.append("---")
    lines.append("This is an automated message from StanexBot")

    return '\n'.join(lines)


def send_telegram_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': GROUP_CHAT_ID,
        'text': text,
        'disable_web_page_preview': True,
    }

    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    if not data.get('ok'):
        raise RuntimeError(f'Telegram API error: {data}')

    logger.info('Message sent to chat %s', GROUP_CHAT_ID)
    return data


def validate_env():
    missing = []
    for var in ['SHEET_ID', 'SHEET_TAB', 'TELEGRAM_BOT_TOKEN',
                'GROUP_CHAT_ID', 'GOOGLE_CREDENTIALS_B64']:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise ValueError(f'Missing env vars: {", ".join(missing)}')


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if not is_vercel_cron(self.headers):
            logger.warning('Rejected non-cron request from %s',
                           self.client_address)
            self.send_error(403, 'Forbidden: cron-only endpoint')
            return

        try:
            validate_env()
            due_rows = fetch_due_rows()
            message = build_message(due_rows)
            send_telegram_message(message)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('OK\n'.encode('utf-8'))

        except Exception as e:
            logger.error('Cron job failed: %s', e, exc_info=True)
            try:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'ERROR: {e}\n'.encode('utf-8'))
            except Exception:
                pass

    def log_message(self, fmt, *args):
        logger.info(fmt % args)
