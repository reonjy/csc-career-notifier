# CSC Career Portal Scraper

A Python scraper that extracts government job listings from the [Civil Service Commission (CSC) Career Portal](https://csc.gov.ph/career/) with configurable filters.

## Features

- **Configurable Filters**: Filter by Position, Agency, Region, and search keyword
- **Pagination Support**: Automatically scrapes all pages of results
- **Dual Output**: Exports to both CSV and JSON formats
- **CLI Arguments**: Override config defaults from the command line
- **Headless Mode**: Runs without a visible browser window (configurable)
- **Rate Limiting**: Built-in delays to be respectful to the server
- **Auto ChromeDriver**: Automatically downloads the correct ChromeDriver version

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

## Telegram notifier (new jobs)

Default filters in `config.py`:

- **Position:** administrative  
- **Region:** Region VII  
- **Keyword:** Cebu  

```powershell
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python notify.py --test
python notify.py --once
```

GitHub Actions: see [SETUP.md](SETUP.md). Workflow runs hourly and only messages **new** posts.

## Usage

### Basic Usage (uses defaults from `config.py`)

```bash
python scrape.py
```

This will scrape using the defaults from `config.py` (interactive prompts ask you to confirm/override them).

### CLI Overrides

```bash
# Search for engineer positions in NCR (skip interactive prompts)
python scrape.py --no-interactive --position "engineer" --region "NCR"

# Search with a different keyword
python scrape.py --search "cebu city"

# Run with visible browser (useful for debugging)
python scrape.py --headless false

# Export only CSV
python scrape.py --format csv

# Custom output directory
python scrape.py --output ./my_results

# Combine multiple options
python scrape.py --no-interactive --position "nurse" --region "Region VII" --search "cebu" --format both
```

### All CLI Options

| Option             | Default (from config.py) | Description                              |
|--------------------|--------------------------|------------------------------------------|
| `--position`       | `""` (any)               | Position keyword filter                  |
| `--agency`         | `All Agencies`           | Agency name filter                       |
| `--region`         | `""` (any)               | Region dropdown filter                   |
| `--search`         | `""` (none)              | DataTable search keyword                 |
| `--headless`       | `true`                   | Run without visible browser              |
| `--format`         | `both`                   | Output format: `csv`, `json`, or `both`  |
| `--output`         | `output`                 | Output directory path                    |
| `--filename`       | `csc_jobs`               | Base filename for output files           |
| `--no-interactive` | off                      | Skip prompts; use CLI/config defaults    |

## Configuration

Edit [`config.py`](config.py) to change default filters, scraping behavior, and output settings without using CLI arguments.

Key settings:
- `ENTRIES_PER_PAGE`: Set to `100` for fewer pagination clicks
- `REQUEST_DELAY`: Seconds between requests (default: `2.0` — be kind to the server)
- `MAX_PAGES`: Safety limit for pages to scrape (`0` = unlimited)
- `HEADLESS`: Run Chrome without a visible window

## Output

Results are saved in the `output/` directory with timestamped filenames:

```
output/
├── csc_jobs_20260702_094500.csv
└── csc_jobs_20260702_094500.json
```

### CSV Example

| agency                    | region | position_title         | plantilla_item_no | posting_date | closing_date | details_url |
|---------------------------|--------|------------------------|--------------------|--------------|--------------|-------------|
| MGO BUTIG, LANAO DEL SUR  | BARMM  | Internal Auditor II    | 18-01              | 08 Jun 2029  | 23 Jun 2026  | ...         |

### JSON Example

```json
[
  {
    "agency": "MGO BUTIG, LANAO DEL SUR",
    "region": "BARMM",
    "position_title": "Internal Auditor II",
    "plantilla_item_no": "18-01",
    "posting_date": "08 Jun 2029",
    "closing_date": "23 Jun 2026",
    "details_url": "https://csc.gov.ph/career/..."
  }
]
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ChromeDriver` version mismatch | Run `pip install --upgrade webdriver-manager` |
| Elements not found | The website's HTML may have changed. Run with `--headless false` to debug visually |
| Timeout errors | Increase `PAGE_LOAD_TIMEOUT` in `config.py` |
| Empty results | Try different filter combinations; the website may be temporarily down |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |

## Disclaimer

This tool is for **personal, educational purposes only**. Please:
- Respect the CSC website's terms of use
- Use reasonable delays between requests
- Do not overload the server with excessive requests
- Verify job details directly with the hiring agency
