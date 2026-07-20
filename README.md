# StanexBot

**Automated daily task deadline reminders for your team, delivered straight to Telegram.**

StanexBot reads your team's project tracker in Google Sheets every morning at 08:00 AM (MYT), identifies tasks approaching their deadline, and posts a clean summary to your Telegram group so nothing slips through the cracks.

> **Free to run.** Deployed on Vercel's Hobby tier. No servers, no Docker, no maintenance.

---

## Table of Contents

- [How It Works](#how-it-works)
- [What You'll Need](#what-youll-need)
- [Setup Guide](#setup-guide)
  - [1. Create a Telegram Bot](#1-create-a-telegram-bot)
  - [2. Set Up the Telegram Group](#2-set-up-the-telegram-group)
  - [3. Configure Google Sheets Access](#3-configure-google-sheets-access)
  - [4. Encode Your Credentials](#4-encode-your-credentials)
  - [5. Deploy to Vercel](#5-deploy-to-vercel)
  - [6. Verify & Test](#6-verify--test)
- [How the Logic Works](#how-the-logic-works)
- [Configuration Options](#configuration-options)
- [Message Examples](#message-examples)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Local Development](#local-development)

---

## How It Works

```
Every morning at 08:00 AM MYT (00:00 UTC)

  Vercel Cron wakes up
        |
        v
  Python function runs (~3 seconds)
        |
        +--> Reads your Google Sheet via Google Sheets API
        +--> Filters rows where deadline is 7 days or closer
        +--> Skips rows already marked COMPLETED
        |
        v
  Posts a formatted summary to your Telegram group
        |
        v
  Function exits. Zero cost until tomorrow.
```

- No browser. No Chrome. No Docker. No Xvfb.
- Sessionless. Credentials live in Vercel environment variables.
- Runs in ~3 seconds. Costs $0/month on Vercel's free tier.

---

## What You'll Need

| Resource | Purpose |
|---|---|
| A **GitHub** account | Hosts the source code |
| A **Vercel** account (free Hobby plan) | Deploys and runs the scheduled function |
| A **Telegram** account | Creates the bot and manages the group |
| A **Google Cloud** account (free tier) | Provides API access to your Google Sheet |
| Your Google Sheet | The task tracker StanexBot reads from |

---

## Setup Guide

### 1. Create a Telegram Bot

1. Open Telegram and message **@BotFather**.
2. Send `/newbot` and follow the prompts:
   - **Display name**: `StanexBot` (or any name you prefer)
   - **Username**: Must be unique and end in `bot` (e.g., `stanex_reminder_bot`)
3. BotFather will reply with an **access token**. Save this securely.
   ```
   Use this token to access the HTTP API:
   8825280276:AAEOyzUz3YRxJBHSKLWMJxSamrNSPFqusv0
   ```

### 2. Set Up the Telegram Group

1. In Telegram, create a **New Group** for your team.
2. Add at least one other person (Telegram requires 2+ members for a group).
3. Add the bot to the group:
   - Open group info → **Add Members** → search for your bot's username.
   - **Promote the bot to Administrator** so it can post messages.
4. Send any message in the group (e.g., "hello").
5. Retrieve the group chat ID by visiting this URL in your browser:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
6. In the JSON response, find `"chat":{"id":`. It will be a **negative number** (e.g., `-1001234567890`). Copy the full value, including the minus sign.

### 3. Configure Google Sheets Access

#### 3.1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Click the project dropdown (top-left) → **New Project**.
3. Name it `StanexBot` → **Create**.

#### 3.2. Enable the Sheets API

1. Navigate to [APIs & Services > Library](https://console.cloud.google.com/apis/library).
2. Search for **Google Sheets API** → select it → click **Enable**.

> **Important:** This is the most commonly missed step. If you skip it, the bot will fail with a `403` error.

#### 3.3. Create a Service Account

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).
2. Click **+ Create Credentials** → **Service Account**.
3. Name: `stanexbot-sheets` → **Done**.
4. Click the newly created service account email in the list.
5. Switch to the **Keys** tab → **Add Key** → **Create New Key** → **JSON**.
6. A `.json` file downloads to your computer. Keep it safe — this is your key.

#### 3.4. Share Your Sheet with the Service Account

1. Open your Google Sheet in the browser.
2. Click **Share** (top-right corner).
3. Paste the service account email address from the JSON file (looks like `stanexbot-sheets@<project-id>.iam.gserviceaccount.com`).
4. Set permission to **Editor**.
5. Click **Send**.

#### 3.5. Locate Your Sheet ID and Tab Name

- **Sheet ID**: Open your sheet. The URL will look like:
  ```
  https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit
  ```
  The long string between `/d/` and `/edit` is your Sheet ID.

- **Tab Name**: The exact text on the tab at the bottom of your sheet (e.g., `Plan of Action`). This is case-sensitive.

### 4. Encode Your Credentials

Vercel serverless functions have no persistent filesystem, so the Google service account JSON must be stored as an environment variable. Encode it to base64:

**Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content -Raw -Path "stanexbot-xxxxx.json"))) | Set-Clipboard
```

**Mac / Linux:**
```bash
base64 -w 0 stanexbot-xxxxx.json
```

The output is a long string — this is your `GOOGLE_CREDENTIALS_B64`.

### 5. Deploy to Vercel

1. **Push the repository to GitHub** (if you haven't already):
   ```bash
   git init
   git add -A
   git commit -m "Initial commit - StanexBot"
   git remote add origin https://github.com/YOUR_USERNAME/stanexbot.git
   git branch -M main
   git push -u origin main
   ```

2. Log in to [Vercel](https://vercel.com) and click **New Project**.

3. Import the `stanexbot` repository.

4. Vercel automatically detects Python — no build command or framework configuration needed.

5. In the **Environment Variables** section, add all of the following:

   | Variable | Description |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | The token from @BotFather (Step 1) |
   | `GROUP_CHAT_ID` | The negative group ID from `getUpdates` (Step 2) |
   | `SHEET_ID` | The ID from your sheet URL (Step 3.5) |
   | `SHEET_TAB` | The exact tab name, case-sensitive (Step 3.5) |
   | `GOOGLE_CREDENTIALS_B64` | The base64-encoded service account JSON (Step 4) |
   | `TRIGGER_DAYS` | *(Optional)* Number of days window. Default: `7` |
   | `HEADER_ROW` | *(Optional)* Row number of column headers. Default: `1` |

6. Click **Deploy**.

### 6. Verify & Test

1. In your Vercel project dashboard, go to the **Cron Jobs** tab. You should see one entry:
   - **Schedule**: `0 0 * * *` (midnight UTC = 08:00 AM MYT)
   - **Path**: `/api/index`
   - **Status**: Active

2. To test immediately, run this in your terminal:
   ```bash
   curl -H "x-vercel-cron-schedule: 0 0 * * *" \
        https://YOUR_PROJECT_NAME.vercel.app/api/index
   ```

3. Check your Telegram group — StanexBot should post its first message.

---

## How the Logic Works

### Sheet Column Requirements

StanexBot expects the following **exact** header names in row 1 of your sheet:

| Header | Content |
|---|---|
| `Due Date` | The task's deadline date |
| `Countdown (Days)` | Number of days remaining *(must be pre-computed by a sheet formula)* |
| `ACTIONS` | Task name or description |
| `PIC` | Person in charge / assignee |
| `PROGRESS` | Current status (e.g., `In Progress`, `Pending`, `COMPLETED`) |

> **Tip:** Rename columns in your sheet to match these headers exactly. The match is case-sensitive.

### Trigger Rules

A task appears in the daily message when **both** conditions are true:

1. `Countdown (Days)` is a valid number **and** falls in the range `0 <= Countdown < TRIGGER_DAYS`
2. `PROGRESS` is **not** `COMPLETED` (case-insensitive)

### Edge Cases Handled

- **Empty or blank rows**: skipped automatically.
- **Non-numeric countdown values**: logged as a warning, the row is skipped.
- **Duplicate column headers**: resolved by using the first occurrence.
- **Missing columns**: treated as empty — the row is skipped if `ACTIONS` is blank.
- **API failures**: logged with full traceback in Vercel's log stream.

---

## Configuration Options

### Custom Trigger Window

Set `TRIGGER_DAYS` in your Vercel environment variables to change how far ahead StanexBot looks. Examples:

| `TRIGGER_DAYS` | Behaviour |
|---|---|
| `3` | Alerts only when 3 or fewer days remain |
| `7` | *(Default)* Alerts for the week ahead |
| `14` | Alerts for the coming fortnight |
| `30` | Alerts for the month ahead |

### Specifying the Header Row

If your sheet has title rows, blank rows, or merged cells before the actual table (e.g., headers start at row 8), set `HEADER_ROW`:

| `HEADER_ROW` | Behaviour |
|---|---|
| `1` | *(Default)* Column headers are in row 1 |
| `8` | Column headers are in row 8 (data starts at row 9) |

### Changing the Schedule

Edit `vercel.json` and update the cron expression. All times are UTC.

| Time (MYT) | UTC | Cron Expression |
|---|---|---|
| 08:00 AM | 00:00 | `0 0 * * *` |
| 10:00 AM | 02:00 | `0 2 * * *` |
| 05:00 PM | 09:00 | `0 9 * * *` |

After editing, redeploy to apply.

### Security Notes

- The `/api/index` endpoint checks for the `x-vercel-cron-schedule` header that Vercel attaches to every cron-triggered request. External browser requests receive `403 Forbidden`.
- All credentials are stored as Vercel environment variables. Nothing sensitive is committed to the repository.
- To completely disable the bot: pause or delete the cron job in Vercel, or remove the bot from your Telegram group.

---

## Message Examples

### When tasks are approaching their deadline

```
🔔 StanexBot Daily Check-in — 20 July 2026

📋 3 task(s) approaching deadline in the next 16 days:

1️⃣ Draw up the digital floorplan
    👤 SYEDI & MIZAN
    📅 4 Aug 2026
    ⚠️ 15 days remaining
    🔄 In Progress

2️⃣ Submit quarterly report
    👤 Ahmad
    📅 25 Jul 2026
    🚨 3 days remaining
    📊 In Progress

3️⃣ Review pull requests
    👤 Siti
    📅 22 Jul 2026
    🚨 Due today!
    ⏳ Pending

---
🤖 Automated by StanexBot
```

### When everything is on track

```
🔔 StanexBot Daily Check-in — 20 July 2026

✅ All clear! No tasks are due in the next 16 days. Great job, team!

---
🤖 Automated by StanexBot
```

---

## Troubleshooting

| Symptom | Likely Cause & Fix |
|---|---|
| `Missing env vars` error | One or more environment variables are not set in Vercel. Double-check all 5 required variables. |
| `APIError: [403]` from Google | The Sheets API is not enabled for your Google Cloud project. See Step 3.2. |
| `PermissionError` | The service account email has not been granted access to the sheet. See Step 3.4. |
| `header row is not unique` | Your sheet has duplicate column headers. StanexBot handles this automatically by using the first occurrence. |
| `non-numeric countdown` warning | A cell in the `Countdown (Days)` column contains text or is empty. The bot skips that row safely. |
| Telegram message not appearing | Check: (1) Bot is an admin in the group? (2) Chat ID includes the minus sign? (3) Bot token is correct? |
| Cron job not running | In Vercel Dashboard → Cron Jobs: is the job active? Check Vercel Logs for runtime errors. |
| `403 Forbidden` on manual curl | You must include the `x-vercel-cron-schedule` header. See the test command in Step 6. |
| Module not found | Verify `requirements.txt` is committed to the repo. Vercel runs `pip install` from it during build. |
| Message is empty | Check that your sheet's header row matches exactly: `Due Date`, `Countdown (Days)`, `ACTIONS`, `PIC`, `PROGRESS`. |

---

## Architecture

```
  Google Sheets              Vercel (Hobby Tier)              Telegram
  ┌──────────────┐          ┌─────────────────────┐          ┌──────────┐
  │ Task tracker │◄─read───│ /api/index (Python)  │──POST──►│ Group    │
  │ (PrepTECH)   │  gspread │                      │  Bot API │ Chat     │
  └──────────────┘          │ Trigger: Cron 0 0 * *│          └──────────┘
                            │ (08:00 MYT daily)    │
                            │                      │
                            │ Env vars store all   │
                            │ credentials & config │
                            └─────────────────────┘
```

| Component | Technology |
|---|---|
| Runtime | Vercel Serverless Functions (Python 3.12) |
| Scheduling | Vercel Cron Jobs (free tier, once-daily) |
| Google Sheets | `gspread` + Google Service Account |
| Messaging | Telegram Bot API (`requests`) |
| Configuration | Vercel Environment Variables |
| Cost | **$0/month** (Hobby plan) |

---

## Local Development

```bash
# Clone and set up
git clone https://github.com/Rewsyaydee/stanexbot.git
cd stanexbot
python -m venv venv

# Activate virtual environment
venv\Scripts\activate     # Windows
source venv/bin/activate   # Mac / Linux

# Install dependencies
pip install -r requirements.txt

# Copy and fill in the environment file
cp .env.example .env

# Test the full pipeline
python -c "
from api.index import validate_env, fetch_due_rows, build_message, send_telegram_message
validate_env()
rows = fetch_due_rows()
msg = build_message(rows)
print(msg)
send_telegram_message(msg)
"
```
