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

### Schedule (best-effort)

GitHub free-tier `schedule` is **not** a guaranteed timer — runs can be delayed or skipped.
This workflow polls about **every 30 minutes** at UTC minutes **:12** and **:42** (offset from the hour
to reduce drops; Selenium runs are slower than OnlineJobs so 15m would often overlap).

- Check history: https://github.com/reonjy/csc-career-notifier/actions  
- Use **Run workflow** anytime for an immediate poll  
- Seen IDs are stored in Actions cache **and** a durable `state` git branch  

### First run vs later runs

| Situation | What Telegram gets |
|-----------|--------------------|
| First run (default) | Jobs are **seeded**, not sent (no spam). ✅ connection only with `python notify.py --test` |
| Later runs | Only **new** jobs |
| Manual run with **resend_all = true** | All current matches (up to 40) |

**Why `SEND_ON_FIRST_RUN=true` as a secret often does nothing after run #1:**  
the first successful run already saved every job into seen state.  
`SEND_ON_FIRST_RUN` only applies when the seen list is **empty**.  
To dump current jobs after that, use **resend_all = true** (see below).

### Send all current matches now

1. Actions → **CSC Career Telegram Notify** → **Run workflow**
2. Set **resend_all** → **true**
3. Run  

Or set secret `RESEND_ALL=true` once, run, then set it back to `false` / delete it.

## Notes

- Uses Selenium + Chrome (heavier than OnlineJobs scraper).
- First GitHub run can take several minutes while Chrome/chromedriver set up.
- Seen job IDs: `state/seen_jobs.json` (cache + `state` branch on the repo).
