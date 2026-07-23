"""
CSC Career Page Scraper - Configuration
========================================
Centralized filter settings for the scraper.
Modify these values to customize your job search criteria.
"""

# ──────────────────────────────────────────────
# Target URL
# ──────────────────────────────────────────────
BASE_URL = "https://csc.gov.ph/career/"

# ──────────────────────────────────────────────
# Filter Settings (matches the "Filter Publications by:" form)
# ──────────────────────────────────────────────

# Position title keyword (typed into the Position text field)
# Examples: "administrative", "engineer", "accountant", "nurse"
# Set to "" (empty string) to skip this filter.
POSITION_FILTER = "administrative"

# Agency name to filter by.
# Set to "All Agencies" or "" to include all agencies.
AGENCY_FILTER = "All Agencies"

# Region to filter by (must match the dropdown options exactly).
# Examples: "Region VII", "NCR", "Region I", "CAR", "BARMM"
# Set to "" to include all regions.
REGION_FILTER = "Region VII"

# ──────────────────────────────────────────────
# Search Box (the DataTable's built-in search)
# ──────────────────────────────────────────────

# Additional search keyword typed into the DataTable search box.
# This filters across all visible columns (agency, position, etc.)
# Set to "" to skip.
SEARCH_KEYWORD = "Cebu"

# ──────────────────────────────────────────────
# Telegram notifier defaults (notify.py / GitHub Actions)
# ──────────────────────────────────────────────

# How often notify.py sleeps between polls when run as a long process.
NOTIFY_POLL_INTERVAL_MINUTES = 60

# First notify run only seeds seen IDs (no flood) unless True.
NOTIFY_SEND_ON_FIRST_RUN = False

# ──────────────────────────────────────────────
# Scraping Behavior
# ──────────────────────────────────────────────

# Run Chrome in headless mode (no visible browser window).
HEADLESS = True

# Number of entries per page to request from the DataTable.
# Options typically: 10, 25, 50, 100
ENTRIES_PER_PAGE = 100

# Maximum number of pages to scrape (safety limit).
# Set to 0 for unlimited.
MAX_PAGES = 0

# Exclude jobs whose closing date has already passed.
# Set to True to only keep jobs that are still open.
FILTER_EXPIRED = True

# Date formats the closing date column might use (tried in order).
# The CSC portal typically uses "dd Mon yyyy" (e.g., "23 Jun 2026").
CLOSING_DATE_FORMATS = [
    "%d %b %Y",    # 23 Jun 2026
    "%d %B %Y",    # 23 June 2026
    "%Y-%m-%d",    # 2026-06-23
    "%m/%d/%Y",    # 06/23/2026
    "%d/%m/%Y",    # 23/06/2026
]

# Delay between page navigations (seconds) — be respectful to the server.
REQUEST_DELAY = 2.0

# Timeout for waiting for page elements to load (seconds).
PAGE_LOAD_TIMEOUT = 30

# ──────────────────────────────────────────────
# Output Settings
# ──────────────────────────────────────────────

# Output file name (without extension). Timestamp is appended automatically.
OUTPUT_FILENAME = "csc_jobs"

# Output formats to generate. Options: "csv", "json", "both"
OUTPUT_FORMAT = "both"

# Output directory (relative to script location).
OUTPUT_DIR = "output"
