# PrepBot - PrepTech Daily WhatsApp (Telegram) Reminder Bot

A serverless Telegram bot that reads a Google Sheet daily, checks which tasks are due within 7 days, and sends a summary reminder to a Telegram group.

**Runs on Vercel (free tier). No Docker, no browser, no session management.**

---

## Architecture

```
Vercel Cron (daily 00:00 UTC / 08:00 MYT)
    |
    v
/api/cron (Python serverless function)
    |
    +--> Google Sheets API (gspread) -- reads task rows
    +--> Telegram Bot API (HTTP POST) -- sends summary to group
    |
    v
  Exit (scales to zero)
```

---

## Prerequisites

| What | Why |
|---|---|
| A **GitHub** account | To host the code and connect to Vercel |
| A **Vercel** account (free Hobby plan) | To deploy and run the bot |
| A **Telegram** account | To create the bot and the group |
| A **Google Cloud** account (free) | To enable Sheets API and create a service account |
| The PrepTech Google Sheet | Source of tasks/reminders |

---

## Step-by-Step Setup

### 1. Create the Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` to BotFather
3. Follow the prompts:
   - Name: `PrepTech Reminder` (or any display name)
   - Username: `preptech_reminder_bot` (must end with `bot`, must be unique)
4. BotFather replies with a **token** — copy it and save it somewhere safe.
   ```
   Use this token to access the HTTP API:
   1234567890:AAFbcdEfghIJklmnOPqrstUVwxyz-ABCdefg
   ```

### 2. Create the Telegram Group & Get the Chat ID

1. In Telegram, create a **New Group**
2. Add at least **one other person** (Telegram groups need 2+ members)
3. Add your bot to the group:
   - Open the group → tap group name → **Add Members**
   - Search for your bot's username (e.g., `@preptech_reminder_bot`)
   - **Promote the bot to admin** (so it can send messages):
     - Group Info → Administrators → Add Admin → select your bot
4. Send any message in the group (e.g., "test")
5. Open your browser and visit this URL (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
6. Look for `"chat":{"id":` in the response. It will be a **negative number** like `-1001234567890`.
   ```json
   {
     "ok": true,
     "result": [{
       "message": {
         "chat": {
           "id": -1001234567890,
           "title": "PrepTech Team"
         }
       }
     }]
   }
   ```
7. Copy the chat ID (including the minus sign). This is your `GROUP_CHAT_ID`.

### 3. Set Up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. **Create a new project** (or select an existing one):
   - Click the project dropdown at the top → **New Project**
   - Name: `PrepBot` → Create
3. **Enable the Google Sheets API**:
   - Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
   - Search for **Google Sheets API** → Click it → **Enable**
4. **Create a Service Account**:
   - Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
   - Click **+ Create Credentials** → **Service Account**
   - Name: `prepbot-sheets` → **Done**
   - After creation, click the service account email
   - Go to the **Keys** tab → **Add Key** → **Create New Key** → **JSON**
   - A JSON file downloads to your computer (e.g., `prepbot-xxxxx-xxxxx.json`)
5. **Share your Google Sheet** with the service account:
   - Open the PrepTech Google Sheet in your browser
   - Click **Share** (top-right)
   - Paste the service account email (looks like `prepbot-sheets@prepbot-xxxxx.iam.gserviceaccount.com`)
   - Give **Editor** access (the bot only reads, but Editor is needed for the API)
   - Click **Send**
6. **Get your Sheet ID**:
   - Open your Google Sheet
   - The URL looks like: `https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit`
   - The long string between `/d/` and `/edit` is your **Sheet ID**
   - Copy this string
7. **Note your sheet tab name**:
   - Look at the tab name at the bottom of your sheet (e.g., "Plan of Action" or "Sheet1")
   - This is your `SHEET_TAB`

### 4. Base64-Encode the Google Credentials

Vercel serverless functions have no filesystem, so we encode the JSON into an environment variable.

**On Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content -Raw -Path "prepbot-xxxxx.json"))) | Set-Clipboard
```

**On Mac / Linux:**
```bash
base64 -w 0 prepbot-xxxxx.json
```

The output is a long string of characters. Copy it — this is your `GOOGLE_CREDENTIALS_B64`.

### 5. Deploy to Vercel

1. **Push this repo to GitHub**:
   ```bash
   git init
   git add -A
   git commit -m "Initial commit - PrepBot"
   git remote add origin https://github.com/YOUR_USERNAME/stanexbot.git
   git branch -M main
   git push -u origin main
   ```
2. Go to [Vercel](https://vercel.com) → **New Project**
3. Import your GitHub repo (`stanexbot`)
4. Vercel auto-detects Python. No build command or framework needed.
5. **Under Environment Variables, add these:**

   | Variable | Value | Where to find it |
   |---|---|---|
   | `TELEGRAM_BOT_TOKEN` | `1234567890:AAFbcd...` | Step 1 (BotFather) |
   | `GROUP_CHAT_ID` | `-1001234567890` | Step 2 (getUpdates) |
   | `SHEET_ID` | `1AbCdEfGh...` | Step 3.6 (Sheet URL) |
   | `SHEET_TAB` | `Plan of Action` | Step 3.7 (tab name) |
   | `GOOGLE_CREDENTIALS_B64` | `eyJ0eXBlIjoic2Vydmlj...` | Step 4 (base64 output) |

6. Click **Deploy**

### 6. Verify Cron is Active

1. In Vercel dashboard, go to your project → **Cron Jobs**
2. You should see one job: `0 0 * * *` at path `/api/cron`
3. Status should show: **Active**

### 7. Test It

To manually trigger the bot without waiting for the cron:

```bash
curl -H "x-vercel-cron-schedule: 0 0 * * *" \
     https://YOUR_PROJECT.vercel.app/api/cron
```

You can also trigger it from Vercel's Cron Jobs dashboard.

Check your Telegram group — you should see the first reminder message.

---

## How It Works

### Cron Schedule

- **08:00 AM MYT (Asia/Kuala Lumpur)** = **00:00 UTC** every day
- Vercel cron triggers a GET request to `/api/cron`
- Precision: triggers between 08:00–08:59 MYT (Vercel Hobby precision is ±59 min)

### Sheet Reading Logic

The bot reads your Google Sheet and looks for columns with these exact headers:

| Header | What it contains |
|---|---|
| `Due Date` | The task deadline date |
| `Countdown (Days)` | Number of days left (must be pre-computed in the sheet) |
| `ACTIONS` | Task name / description |
| `PIC` | Person in charge / owner |
| `PROGRESS` | Status (e.g. In Progress, Pending, COMPLETED) |

**Trigger conditions (both must be true):**
1. `Countdown (Days)` is a number AND `0 <= Countdown (Days) < 7`
2. `PROGRESS` is NOT `COMPLETED` (case-insensitive)

Blank rows and rows with non-numeric countdown values are safely skipped.

### Message Format

**When tasks are due:**
```
PREPTECH DAILY REMINDER

3 task(s) due within 7 days:

1) Submit quarterly report
   PIC: Ahmad | Due: 2026-07-25 | 3 days left | [In Progress]

2) Review pull requests
   PIC: Siti | Due: 2026-07-22 | 1 day left | [Pending]

3) Update CI pipeline
   PIC: John | Due: 2026-07-24 | 2 days left | [In Progress]

---
Sent by PrepBot via Vercel Cron
```

**When everything is on track:**
```
PREPTECH DAILY REMINDER

All tasks on track - no deadlines in the next 7 days.

---
Sent by PrepBot via Vercel Cron
```

---

## Configuration

### Change the Trigger Window

Set the `TRIGGER_DAYS` env var in Vercel. Default is `7`.

Example: to alert only when 3 or fewer days remain:
- Env var: `TRIGGER_DAYS` = `3`

### Security

The cron endpoint (`/api/cron`) checks for the `x-vercel-cron-schedule` header that Vercel attaches to every cron-triggered request. External requests (from browsers) receive a `403 Forbidden` response.

### Failsafe / Removing the Bot

If you want to stop the bot:
1. **Vercel**: Go to Cron Jobs → Pause or Delete the cron job
2. **Telegram**: Remove the bot from the group
3. **Telegram**: Send `/revoke` to @BotFather to revoke the token

---

## Troubleshooting

| Problem | Check |
|---|---|
| "Missing env vars" error | Verify all 5 env vars are set in Vercel > Settings > Environment Variables |
| "403 Forbidden" | The `x-vercel-cron-schedule` header is missing — cron works, manual curl without header blocked (by design) |
| "non-numeric countdown" warning | A row in the sheet has text in the Countdown column. Either fix the formula or the bot skips it safely. |
| "Module not found: gspread" | Make sure `requirements.txt` is committed and Vercel ran `pip install` during deploy |
| Telegram message not showing | (1) Bot is admin in the group? (2) Chat ID is correct and negative? (3) Token is correct? |
| Google Sheets auth fails | (1) Credentials base64 is correct? (2) Sheet is shared with the service account email? (3) Sheets API is enabled? |
| Sheet tab not found | The tab name in `SHEET_TAB` must match exactly (case-sensitive, include spaces) |
| Cron not running | Check Vercel > Cron Jobs tab — is it active? Check Vercel > Logs for errors |
| Message sent but empty | Check that column headers in your Sheet match EXACTLY: `Due Date`, `Countdown (Days)`, `ACTIONS`, `PIC`, `PROGRESS` |

---

## Vercel Free Tier Notes

- **100 cron jobs** per project (you use 1)
- **Daily minimum interval** (matches your 08:00 once-daily schedule)
- **±59 minute scheduling precision** (message arrives between 08:00–08:59 MYT)
- **No cron job cost** — included in all plans
- **Function costs are negligible** — ~3 seconds per invocation, well within free tier

---

## Local Development (Optional)

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/stanexbot.git
cd stanexbot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set env vars for local testing
$env:TELEGRAM_BOT_TOKEN="your_token"
$env:GROUP_CHAT_ID="-1001234567890"
$env:SHEET_ID="your_sheet_id"
$env:SHEET_TAB="Plan of Action"
$env:GOOGLE_CREDENTIALS_B64="your_base64_string"

# Run the function logic directly
python -c "
import json, os
from api.cron import validate_env, fetch_due_rows, build_message, send_telegram_message
validate_env()
rows = fetch_due_rows()
msg = build_message(rows)
print(msg)
send_telegram_message(msg)
"
```
