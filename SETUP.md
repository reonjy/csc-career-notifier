# CSC Career → Telegram setup

Default filters:

| Filter | Value |
|--------|--------|
| Position | `administrative` |
| Region | `Region VII` |
| Search keyword | `Cebu` |

## Local

```powershell
cd C:\Users\Peppa\Documents\Programs\csc-career-scraper
pip install -r requirements.txt

# Set env (PowerShell)
$env:TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
$env:TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

python notify.py --test
python notify.py --once
```

You can reuse the **same Telegram bot** as OnlineJobs.

## GitHub Actions (always-on)

1. Create/push this project to a GitHub repo (e.g. `csc-career-notifier`).
2. **Settings → Secrets and variables → Actions**:

| Secret | Required | Default if empty |
|--------|----------|------------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — |
| `TELEGRAM_CHAT_ID` | Yes | — |
| `CSC_POSITION` | No | `administrative` |
| `CSC_REGION` | No | `Region VII` |
| `CSC_SEARCH` | No | `Cebu` |

3. **Actions → CSC Career Telegram Notify → Run workflow**

- First run seeds existing jobs (no spam) + sends ✅ connection message  
- Hourly after that: only **new** matching CSC posts  

## Notes

- Uses Selenium + Chrome (heavier than OnlineJobs scraper).
- First GitHub run can take several minutes while Chrome/chromedriver set up.
- Seen job IDs are cached under `state/seen_jobs.json`.
