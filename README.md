# CSC Career Portal Scraper

A Python scraper that extracts government job listings from the [Civil Service Commission (CSC) Career Portal](https://csc.gov.ph/career/) with configurable filters.

## Telegram notifier (new jobs)

Default filters:

- **Position:** administrative  
- **Region:** Region VII  
- **Keyword:** Cebu  

**Reliable polling:** use **external cron** (cron-job.org) → GitHub Actions every **30 minutes**.  
GitHub free-tier schedule alone often skips. See **[EXTERNAL_CRON.md](EXTERNAL_CRON.md)** and **[SETUP.md](SETUP.md)**.

```powershell
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python notify.py --test
python notify.py --once
```

## Features

- **Configurable Filters**: Filter by Position, Agency, Region, and search keyword
- **Pagination Support**: Automatically scrapes all pages of results
- **Dual Output**: Exports to both CSV and JSON formats
- **CLI Arguments**: Override config defaults from the command line
- **Headless Mode**: Runs without a visible browser window (configurable)
- **Rate Limiting**: Built-in delays to be respectful to the server
- **Auto ChromeDriver**: Automatically downloads the correct ChromeDriver version
- **Telegram + GitHub Actions**: notify on new matching jobs

## Prerequisites

- **Python 3.10+**
- **Google Chrome** browser installed on your system

## Setup

1. **Navigate to the project directory**:
   ```bash
   cd csc-career-scraper
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage (uses defaults from `config.py`)

```bash
python scrape.py
```

### CLI Overrides

```bash
python scrape.py --no-interactive --position "engineer" --region "NCR"
python scrape.py --search "cebu city"
python scrape.py --headless false
```

## Configuration

Edit [`config.py`](config.py) for default filters and scraping behavior.

## Disclaimer

This tool is for **personal, educational purposes only**. Respect the CSC website’s terms of use and verify job details with the hiring agency.
