"""
CSC Career Portal → Telegram Notifier
=====================================
Scrapes CSC career listings with your filters and sends NEW jobs to Telegram.

Default filters (config.py / env overrides):
  Position : administrative
  Region   : Region VII
  Search   : Cebu

Usage:
    python notify.py --once
    python notify.py --test
    python notify.py

Env / GitHub Actions secrets:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  CSC_POSITION, CSC_REGION, CSC_SEARCH, CSC_AGENCY (optional overrides)
  POLL_INTERVAL_MINUTES, SEND_ON_FIRST_RUN, STATE_FILE, HEADLESS
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

import config
from scrape import log, run_scrape

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state" / "seen_jobs.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val is None or str(val).strip() == "":
        return default
    return str(val).strip()


def load_settings() -> dict:
    token = (_env("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = str(_env("TELEGRAM_CHAT_ID") or "").strip()
    if not token:
        print("ERROR: Set TELEGRAM_BOT_TOKEN env (or GitHub secret).")
        sys.exit(1)
    if not chat_id:
        print("ERROR: Set TELEGRAM_CHAT_ID env (or GitHub secret).")
        sys.exit(1)

    chat_id = chat_id.strip().strip('"').strip("'")
    if chat_id.lower().startswith("chat_id="):
        chat_id = chat_id.split("=", 1)[1].strip()

    position = _env("CSC_POSITION", config.POSITION_FILTER) or ""
    agency = _env("CSC_AGENCY", config.AGENCY_FILTER) or "All Agencies"
    region = _env("CSC_REGION", config.REGION_FILTER) or ""
    search = _env("CSC_SEARCH", config.SEARCH_KEYWORD) or ""

    interval = float(
        _env(
            "POLL_INTERVAL_MINUTES",
            str(getattr(config, "NOTIFY_POLL_INTERVAL_MINUTES", 60)),
        )
    )
    def _truthy(name: str, default: str = "false") -> bool:
        return (_env(name, default) or default).lower() in ("1", "true", "yes", "y")

    send_first = _truthy("SEND_ON_FIRST_RUN", "false")
    # Force-send every current match (ignores seen state for this run)
    resend_all = _truthy("RESEND_ALL", "false")
    headless = _truthy("HEADLESS", "true")

    state = _env("STATE_FILE")
    if state:
        state_path = Path(state)
    else:
        data_dir = Path("/data")
        if data_dir.is_dir() and os.access(data_dir, os.W_OK):
            state_path = data_dir / "csc_seen_jobs.json"
        else:
            state_path = STATE_FILE

    return {
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
        "filters": {
            "position": position,
            "agency": agency,
            "region": region,
            "search": search,
        },
        "poll_interval_minutes": interval,
        "send_on_first_run": send_first,
        "resend_all": resend_all,
        "headless": headless,
        "state_file": state_path,
    }


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = sorted(seen)[-8000:]
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(ids),
        "seen_ids": ids,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def job_id(job: dict) -> str:
    """Stable id for a CSC listing."""
    url = (job.get("details_url") or "").strip()
    m = re.search(r"/(\d{5,})/?$", url)
    if m:
        return f"csc-{m.group(1)}"
    raw = "|".join(
        [
            job.get("agency", ""),
            job.get("region", ""),
            job.get("position_title", ""),
            job.get("plantilla_item_no", ""),
            job.get("posting_date", ""),
            job.get("closing_date", ""),
        ]
    )
    return "csc-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def telegram_call(token: str, method: str, payload: dict) -> dict:
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, json=payload, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        desc = data.get("description") or data
        hint = ""
        if "chat not found" in str(desc).lower():
            hint = (
                "\n\nCHAT NOT FOUND — fix TELEGRAM_CHAT_ID:\n"
                "  1. Open your bot and press Start / send a message\n"
                "  2. Open getUpdates and copy chat.id (number only)\n"
            )
        raise RuntimeError(f"Telegram API error: {data}{hint}")
    return data


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    telegram_call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
    )


def format_job_message(job: dict, filters: dict) -> str:
    title = html.escape(job.get("position_title") or "Untitled position")
    agency = html.escape(job.get("agency") or "—")
    region = html.escape(job.get("region") or "—")
    plantilla = html.escape(job.get("plantilla_item_no") or "—")
    posted = html.escape(job.get("posting_date") or "—")
    closing = html.escape(job.get("closing_date") or "—")
    link = (job.get("details_url") or "").strip()
    filt = html.escape(
        f"{filters.get('position') or 'any'} | {filters.get('region') or 'any'} | "
        f"{filters.get('search') or '—'}"
    )

    lines = [
        f"🏛️ <b>CSC Job: {title}</b>",
        f"🏢 <b>Agency:</b> {agency}",
        f"📍 <b>Region:</b> {region}",
        f"🔢 <b>Plantilla:</b> {plantilla}",
        f"📅 <b>Posted:</b> {posted}",
        f"⏰ <b>Closing:</b> {closing}",
        f"🏷 <b>Filter:</b> {filt}",
    ]
    if link:
        lines.append(f'🔗 <a href="{html.escape(link)}">View details</a>')
    return "\n".join(lines)


def test_telegram(token: str, chat_id: str) -> None:
    send_telegram_message(
        token,
        chat_id,
        "✅ CSC Career notifier is connected.\n"
        "You will get messages when new matching CSC jobs appear.",
    )


def run_once(settings: dict, seen: set[str]) -> set[str]:
    filters = settings["filters"]
    state_path = Path(settings["state_file"])
    resend_all = bool(settings.get("resend_all"))
    send_on_first = bool(settings.get("send_on_first_run"))

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling CSC Career…")
    print(
        f"  Filters: position={filters['position']!r} "
        f"region={filters['region']!r} search={filters['search']!r}"
    )
    print(
        f"  Options: send_on_first_run={send_on_first} resend_all={resend_all} "
        f"already_seen={len(seen)}"
    )

    jobs = run_scrape(filters, headless=settings["headless"])
    print(f"  Found {len(jobs)} active job(s) matching filters")

    if not jobs:
        print(
            "  No jobs matched filters — nothing to send. "
            "Check CSC_POSITION / CSC_REGION / CSC_SEARCH."
        )
        save_seen(state_path, seen)
        return seen

    for j in jobs:
        j["_id"] = job_id(j)

    # Prefer newest posting dates first when notifying
    def _post_key(j):
        from scrape import _parse_date

        d = _parse_date(j.get("posting_date", "") or "")
        return d or datetime.min.date()

    # What to send this run
    if resend_all:
        # Ignore seen cache for this run (user requested a full dump)
        to_send = sorted(jobs, key=_post_key, reverse=True)
        print(f"  RESEND_ALL: will send all {len(to_send)} current match(es)")
    else:
        to_send = [j for j in jobs if j["_id"] not in seen]
        to_send = sorted(to_send, key=_post_key, reverse=True)

    first_run = len(seen) == 0
    if first_run and not send_on_first and not resend_all:
        print(
            f"  First run: seeding {len(jobs)} job IDs (no Telegram spam). "
            "Set SEND_ON_FIRST_RUN=true or RESEND_ALL=true to send listings, "
            "or wait for new posts on later runs."
        )
        for j in jobs:
            seen.add(j["_id"])
        save_seen(state_path, seen)
        return seen

    if not to_send:
        print(
            f"  No new jobs to send ({len(jobs)} match filter, "
            f"all already in seen list). "
            "Use RESEND_ALL=true once to re-send current matches."
        )
        for j in jobs:
            seen.add(j["_id"])
        save_seen(state_path, seen)
        return seen

    # Safety cap so we don't spam hundreds of messages by accident
    max_send = int(_env("MAX_SEND_PER_RUN", "40") or "40")
    if len(to_send) > max_send:
        print(
            f"  Capping send list from {len(to_send)} to {max_send} "
            f"(set MAX_SEND_PER_RUN to raise)"
        )
        to_send = to_send[:max_send]

    print(f"  Sending {len(to_send)} job(s) to Telegram…")
    token = settings["telegram_bot_token"]
    chat_id = settings["telegram_chat_id"]
    sent = 0
    for job in to_send:
        try:
            send_telegram_message(token, chat_id, format_job_message(job, filters))
            sent += 1
            seen.add(job["_id"])
            time.sleep(0.4)
        except Exception as exc:
            print(f"  [warn] failed to send {job['_id']}: {exc}")

    for j in jobs:
        seen.add(j["_id"])
    save_seen(state_path, seen)
    print(f"  Sent {sent} Telegram message(s). Seen IDs: {len(seen)}")
    return seen


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Notify Telegram of new CSC career jobs.")
    p.add_argument("--once", action="store_true", help="Single poll then exit")
    p.add_argument("--test", action="store_true", help="Send a test Telegram message")
    p.add_argument(
        "--send-existing",
        action="store_true",
        help="On first run, send current matches instead of only seeding",
    )
    p.add_argument(
        "--resend-all",
        action="store_true",
        help="Send all current matches this run (ignore seen cache)",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Minutes between polls (long-running mode)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    if args.send_existing:
        settings["send_on_first_run"] = True
    if args.resend_all:
        settings["resend_all"] = True
    if args.interval is not None:
        settings["poll_interval_minutes"] = args.interval

    token = settings["telegram_bot_token"]
    chat_id = settings["telegram_chat_id"]
    filters = settings["filters"]

    if args.test:
        print("Sending test message…")
        test_telegram(token, chat_id)
        print("OK — check Telegram.")
        return 0

    state_path = Path(settings["state_file"])
    seen = load_seen(state_path)
    interval = float(settings["poll_interval_minutes"])

    print("CSC Career → Telegram notifier")
    print(f"  Position : {filters['position'] or '(any)'}")
    print(f"  Region   : {filters['region'] or '(any)'}")
    print(f"  Search   : {filters['search'] or '(none)'}")
    print(f"  Agency   : {filters['agency'] or '(any)'}")
    print(f"  Interval : {interval} min" + (" (single run)" if args.once else ""))
    print(f"  State    : {state_path}")
    print(f"  Seen IDs : {len(seen)}")
    print("  Press Ctrl+C to stop.\n")

    try:
        test_telegram(token, chat_id)
        print("Telegram connection OK.\n")
    except Exception as exc:
        print(f"ERROR: Could not message Telegram: {exc}")
        return 1

    try:
        while True:
            try:
                seen = run_once(settings, seen)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"  [error] poll failed: {exc}")
                import traceback

                traceback.print_exc()

            if args.once:
                break

            print(f"  Sleeping {interval} minute(s)…")
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
