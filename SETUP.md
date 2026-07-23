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

$env:TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
$env:TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

python notify.py --test
python notify.py --once
```

You can reuse the **same Telegram bot** as OnlineJobs.

## GitHub Actions secrets

https://github.com/reonjy/csc-career-notifier/settings/secrets/actions

| Secret | Required | Default if empty |
|--------|----------|------------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — |
| `TELEGRAM_CHAT_ID` | Yes | — |
| `CSC_POSITION` | No | `administrative` |
| `CSC_REGION` | No | `Region VII` |
| `CSC_SEARCH` | No | `Cebu` |

## Reliable timer: external cron (required)

GitHub’s built-in schedule is unreliable. Use **cron-job.org** like OnlineJobs.

**Full guide: [EXTERNAL_CRON.md](EXTERNAL_CRON.md)**

Quick settings:

| Field | Value |
|-------|--------|
| URL | `https://api.github.com/repos/reonjy/csc-career-notifier/actions/workflows/318717289/dispatches` |
| Method | **POST** |
| Body | `{"ref":"main"}` |
| Schedule | every **30 minutes** |
| Auth | `Bearer` + same PAT as OnlineJobs |

Expect **204** on test run, then a green run under [Actions](https://github.com/reonjy/csc-career-notifier/actions).

### First run vs later runs

| Situation | Telegram |
|-----------|----------|
| First run | Seeds IDs only (no spam) |
| Later runs | Only **new** jobs |
| Secret `RESEND_ALL=true` once | All current matches (up to 40) |

## Notes

- Selenium + Chrome — slower than OnlineJobs (use 30m interval)
- Seen IDs: Actions cache + `state` branch
