# Reliable CSC polls (external cron)

Same approach as OnlineJobs: **cron-job.org** triggers GitHub Actions.

CSC uses **Selenium + Chrome** (often 5–15 minutes per run), so use **every 30 minutes**, not 15 — otherwise runs can overlap and queue.

## cron-job.org settings (copy from your working OnlineJobs job)

Create a **second** cron job (keep OnlineJobs as its own job).

| Field | Value |
|-------|--------|
| **Title** | `CSC poll 30m` |
| **URL** | `https://api.github.com/repos/reonjy/csc-career-notifier/actions/workflows/318717289/dispatches` |
| **Method** | **POST** (not GET — GET causes 422) |
| **Schedule** | Every **30 minutes** |
| **Body** | `{"ref":"main"}` |

Alternate URL (filename instead of numeric id):

```text
https://api.github.com/repos/reonjy/csc-career-notifier/actions/workflows/csc-notify.yml/dispatches
```

### Headers (same as OnlineJobs)

```text
Accept: application/vnd.github+json
Authorization: Bearer ghp_YOUR_TOKEN
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

You can reuse the **same classic PAT** (`repo` scope) as OnlineJobs if it already works there.

### Success

| Status | Meaning |
|--------|--------|
| **204** | OK — Actions will run |
| **422** | Method still GET or body empty/wrong |
| **401/403** | Token/header issue |

Then check: https://github.com/reonjy/csc-career-notifier/actions  
You should see **CSC Career Telegram Notify** with event `workflow_dispatch`.

---

## Side-by-side (both scrapers)

| | OnlineJobs | CSC |
|--|------------|-----|
| Repo | `onlinejobs-ph-notifier` | `csc-career-notifier` |
| Workflow id | `318610773` | `318717289` |
| Body | `{"ref":"main"}` | `{"ref":"main"}` |
| Interval | **15 min** | **30 min** (Selenium) |
| PAT | same | same |
| Telegram secrets | on that repo | on that repo |

---

## Optional: resend all current CSC matches

Because external cron has no form inputs, use a secret once:

1. Repo → Settings → Secrets → `RESEND_ALL` = `true`
2. Test run the CSC cron (or Run workflow once)
3. Delete secret or set `false`

---

## Notes

- First successful poll **seeds** seen IDs (no flood); later polls send **new** jobs only
- Defaults: position `administrative`, region `Region VII`, search `Cebu`
- Run can take several minutes (Chrome setup + scrape)
