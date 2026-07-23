"""
CSC Career Page Scraper (Selenium)
===================================
Scrapes government job listings from https://csc.gov.ph/career/
with configurable filters for Position, Agency, Region, and keyword search.

Usage:
    python scrape.py
    python scrape.py --no-interactive --position "engineer" --region "NCR"
    python scrape.py --headless false
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("=" * 60)
    print("ERROR: Missing dependencies.")
    print("Run:  pip install -r requirements.txt")
    print("=" * 60)
    sys.exit(1)

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

import config


# ──────────────────────────────────────────────
# Logging helpers
# ──────────────────────────────────────────────

def _try_enable_ansi():
    """Try to enable ANSI escape codes on Windows 10+."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_ANSI_OK = _try_enable_ansi()


class Logger:
    """Simple console logger. Uses ANSI colors only if the terminal supports them."""

    COLORS = {
        "info":  "\033[94m"  if _ANSI_OK else "",
        "ok":    "\033[92m"  if _ANSI_OK else "",
        "warn":  "\033[93m"  if _ANSI_OK else "",
        "error": "\033[91m"  if _ANSI_OK else "",
        "reset": "\033[0m"   if _ANSI_OK else "",
        "bold":  "\033[1m"   if _ANSI_OK else "",
        "dim":   "\033[2m"   if _ANSI_OK else "",
    }

    @staticmethod
    def _ts():
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def info(cls, msg):
        print(f"[{cls._ts()}]  i  {msg}")

    @classmethod
    def ok(cls, msg):
        print(f"[{cls._ts()}]  +  {msg}")

    @classmethod
    def warn(cls, msg):
        print(f"[{cls._ts()}]  !  {msg}")

    @classmethod
    def error(cls, msg):
        print(f"[{cls._ts()}]  X  {msg}")

    @classmethod
    def header(cls, msg):
        width = 60
        print()
        print("=" * width)
        print(f"  {msg}")
        print("=" * width)
        print()


log = Logger()


# ──────────────────────────────────────────────
# Browser setup
# ──────────────────────────────────────────────

def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # Common stability options (CI / GitHub Actions friendly)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    chrome_bin = os.environ.get("CHROME_BIN") or os.environ.get("CHROME_PATH")
    if chrome_bin and os.path.isfile(chrome_bin):
        options.binary_location = chrome_bin

    # Mimic a real browser
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # Suppress automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Suppress verbose logging
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # Fallback: try system Chrome/chromedriver
        log.warn("webdriver-manager failed, trying system chromedriver...")
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
    return driver


# ──────────────────────────────────────────────
# Scraper core
# ──────────────────────────────────────────────

class CSCScraper:
    """Scrapes job listings from the CSC Career portal."""

    def __init__(self, driver: webdriver.Chrome, filters: dict):
        self.driver = driver
        self.filters = filters
        self.wait = WebDriverWait(driver, config.PAGE_LOAD_TIMEOUT)
        self.jobs = []

    # ── Navigation ────────────────────────────

    def navigate_to_career_page(self):
        """Load the CSC career page."""
        log.info(f"Navigating to {config.BASE_URL}")
        self.driver.get(config.BASE_URL)
        time.sleep(3)  # Let the page fully initialize

        # Wait for the filter form to be present
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input, select, button"))
            )
            log.ok("Career page loaded successfully")
        except Exception:
            log.warn("Page loaded but filter elements may not be ready yet")

    # ── Filter application ────────────────────

    def apply_filters(self):
        """Apply the position, agency, and region filters, then click Filter."""
        log.info("Applying filters...")

        # --- Position filter ---
        position = self.filters.get("position", "")
        if position:
            try:
                # Try common selectors for the position input
                pos_input = self._find_element_flexible(
                    selectors=[
                        (By.CSS_SELECTOR, "input[name*='position' i]"),
                        (By.CSS_SELECTOR, "input[name*='pos' i]"),
                        (By.CSS_SELECTOR, "input[placeholder*='position' i]"),
                        (By.XPATH, "//label[contains(text(),'Position')]/following::input[1]"),
                        (By.XPATH, "//b[contains(text(),'Position')]/following::input[1]"),
                        (By.XPATH, "//*[contains(text(),'Position')]/ancestor::div[1]//input"),
                    ],
                    description="Position input"
                )
                if pos_input:
                    pos_input.clear()
                    pos_input.send_keys(position)
                    log.ok(f"Position filter set to: '{position}'")
                    time.sleep(0.5)
            except Exception as e:
                log.warn(f"Could not set position filter: {e}")

        # --- Agency filter ---
        agency = self.filters.get("agency", "")
        if agency and agency != "All Agencies":
            try:
                agency_select = self._find_element_flexible(
                    selectors=[
                        (By.CSS_SELECTOR, "select[name*='agency' i]"),
                        (By.CSS_SELECTOR, "select[name*='agcy' i]"),
                        (By.XPATH, "//label[contains(text(),'Agency')]/following::select[1]"),
                        (By.XPATH, "//*[contains(text(),'Agency')]/ancestor::div[1]//select"),
                    ],
                    description="Agency dropdown"
                )
                if agency_select:
                    select = Select(agency_select)
                    try:
                        select.select_by_visible_text(agency)
                    except Exception:
                        # Try partial match
                        for option in select.options:
                            if agency.lower() in option.text.lower():
                                select.select_by_visible_text(option.text)
                                break
                    log.ok(f"Agency filter set to: '{agency}'")
                    time.sleep(0.5)
            except Exception as e:
                log.warn(f"Could not set agency filter: {e}")

        # --- Region filter ---
        region = self.filters.get("region", "")
        if region:
            try:
                region_select = self._find_element_flexible(
                    selectors=[
                        (By.CSS_SELECTOR, "select[name*='region' i]"),
                        (By.CSS_SELECTOR, "select[name*='rgn' i]"),
                        (By.XPATH, "//label[contains(text(),'Region')]/following::select[1]"),
                        (By.XPATH, "//*[contains(text(),'Region')]/ancestor::div[1]//select"),
                    ],
                    description="Region dropdown"
                )
                if region_select:
                    select = Select(region_select)
                    try:
                        select.select_by_visible_text(region)
                    except Exception:
                        # Try partial match
                        for option in select.options:
                            if region.lower() in option.text.lower():
                                select.select_by_visible_text(option.text)
                                break
                    log.ok(f"Region filter set to: '{region}'")
                    time.sleep(0.5)
            except Exception as e:
                log.warn(f"Could not set region filter: {e}")

        # --- Click Filter button ---
        try:
            filter_btn = self._find_element_flexible(
                selectors=[
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(text(),'Filter')]"),
                    (By.XPATH, "//input[@value='Filter']"),
                    (By.CSS_SELECTOR, ".btn-primary"),
                    (By.CSS_SELECTOR, "button.btn"),
                    (By.XPATH, "//a[contains(text(),'Filter')]"),
                ],
                description="Filter button"
            )
            if filter_btn:
                filter_btn.click()
                log.ok("Filter button clicked")
                time.sleep(config.REQUEST_DELAY)
                self._wait_for_table_load()
        except Exception as e:
            log.warn(f"Could not click Filter button: {e}")

    def apply_search(self):
        """Type the search keyword into the DataTable search box."""
        keyword = self.filters.get("search", "")
        if not keyword:
            return

        log.info(f"Applying search keyword: '{keyword}'")
        try:
            search_input = self._find_element_flexible(
                selectors=[
                    (By.CSS_SELECTOR, "input[type='search']"),
                    (By.CSS_SELECTOR, ".dataTables_filter input"),
                    (By.CSS_SELECTOR, "#DataTables_Table_0_filter input"),
                    (By.XPATH, "//label[contains(text(),'Search')]/input"),
                    (By.XPATH, "//input[@aria-controls]"),
                ],
                description="DataTable search box"
            )
            if search_input:
                search_input.clear()
                search_input.send_keys(keyword)
                log.ok(f"Typed search keyword: '{keyword}'")
                log.info("Pressing Enter to submit search...")
                search_input.send_keys(Keys.ENTER)
                log.ok("Enter button clicked")
                log.info("Waiting for search filter to finish processing...")
                time.sleep(config.REQUEST_DELAY)
                self._wait_for_table_load()
                time.sleep(2)
                log.ok(f"Search filter for '{keyword}' completed — results loaded")
        except Exception as e:
            log.warn(f"Could not apply search keyword: {e}")

    def set_entries_per_page(self):
        """Set the number of entries per page in the DataTable."""
        try:
            entries_select = self._find_element_flexible(
                selectors=[
                    (By.CSS_SELECTOR, ".dataTables_length select"),
                    (By.CSS_SELECTOR, "select[name*='_length']"),
                    (By.XPATH, "//label[contains(text(),'entries')]/select"),
                    (By.XPATH, "//select[contains(@name,'length')]"),
                ],
                description="Entries per page dropdown"
            )
            if entries_select:
                select = Select(entries_select)
                try:
                    select.select_by_value(str(config.ENTRIES_PER_PAGE))
                except Exception:
                    options = [int(o.get_attribute("value")) for o in select.options
                               if o.get_attribute("value").isdigit()]
                    if options:
                        select.select_by_value(str(max(options)))
                log.ok(f"Entries per page set to: {config.ENTRIES_PER_PAGE}")
                time.sleep(config.REQUEST_DELAY)
                self._wait_for_table_load()
        except Exception as e:
            log.warn(f"Could not set entries per page: {e}")

    def scrape_current_page(self) -> list[dict]:
        """Extract job listings from the currently visible DataTable page."""
        rows = []
        try:
            table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if not table_rows:
                table_rows = self.driver.find_elements(
                    By.CSS_SELECTOR, ".dataTable tbody tr, #DataTables_Table_0 tbody tr"
                )
            for row in table_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells or len(cells) < 4:
                    continue
                first_cell_text = cells[0].text.strip()
                if "no data" in first_cell_text.lower() or "no matching" in first_cell_text.lower():
                    continue
                job = {}
                try:
                    job["agency"] = cells[0].text.strip() if len(cells) > 0 else ""
                    job["region"] = cells[1].text.strip() if len(cells) > 1 else ""
                    job["position_title"] = cells[2].text.strip() if len(cells) > 2 else ""
                    job["plantilla_item_no"] = cells[3].text.strip() if len(cells) > 3 else ""
                    job["posting_date"] = cells[4].text.strip() if len(cells) > 4 else ""
                    job["closing_date"] = cells[5].text.strip() if len(cells) > 5 else ""
                    import re
                    job["details_url"] = ""
                    if len(cells) > 6:
                        action_cell = cells[6]
                        if not rows:
                            try:
                                raw_html = action_cell.get_attribute("innerHTML")
                                log.info(f"Action cell HTML (first row): {raw_html[:300]}")
                            except Exception:
                                pass
                        try:
                            btn = action_cell.find_element(By.CSS_SELECTOR, "button[id^='info_']")
                            btn_id = btn.get_attribute("id") or ""
                            job_id = btn_id.replace("info_", "")
                            if job_id.isdigit():
                                job["details_url"] = f"https://csc.gov.ph/career/job/{job_id}"
                        except Exception:
                            pass
                        if not job["details_url"]:
                            try:
                                links = action_cell.find_elements(By.TAG_NAME, "a")
                                for link in links:
                                    href = link.get_attribute("href") or ""
                                    if href and href != "#" and "javascript" not in href.lower():
                                        job["details_url"] = href
                                        break
                            except Exception:
                                pass
                        if not job["details_url"]:
                            try:
                                elements = action_cell.find_elements(By.CSS_SELECTOR, "a, button, input, [role='button']")
                                for el in elements:
                                    for attr in ["data-href", "data-url", "data-link", "data-id", "value"]:
                                        val = el.get_attribute(attr) or ""
                                        if val:
                                            if val.startswith("http"):
                                                job["details_url"] = val
                                                break
                                            elif val.isdigit() and len(val) >= 5:
                                                job["details_url"] = f"https://csc.gov.ph/career/job/{val}"
                                                break
                                    if job["details_url"]:
                                        break
                            except Exception:
                                pass
                        if not job["details_url"]:
                            try:
                                clickable = action_cell.find_elements(By.CSS_SELECTOR, "[onclick]")
                                for el in clickable:
                                    onclick = el.get_attribute("onclick") or ""
                                    url_match = re.search(r"(https?://[^\s'\"]+)", onclick)
                                    if url_match:
                                        job["details_url"] = url_match.group(1)
                                        break
                                    id_match = re.search(r"(\d{5,})", onclick)
                                    if id_match:
                                        job["details_url"] = f"https://csc.gov.ph/career/job/{id_match.group(1)}"
                                        break
                            except Exception:
                                pass
                        if not job["details_url"]:
                            try:
                                html = action_cell.get_attribute("innerHTML") or ""
                                href_match = re.search(r'href=["\']([^"\']+)["\']', html)
                                if href_match:
                                    href_val = href_match.group(1)
                                    if href_val.startswith("http"):
                                        job["details_url"] = href_val
                                    elif href_val.startswith("/"):
                                        job["details_url"] = f"https://csc.gov.ph{href_val}"
                                if not job["details_url"]:
                                    id_match = re.search(r"job/(\d+)", html)
                                    if id_match:
                                        job["details_url"] = f"https://csc.gov.ph/career/job/{id_match.group(1)}"
                                    else:
                                        id_match = re.search(r"career/(\d+)", html)
                                        if id_match:
                                            job["details_url"] = f"https://csc.gov.ph/career/{id_match.group(1)}"
                            except Exception:
                                pass
                        if not job["details_url"]:
                            try:
                                row_html = row.get_attribute("innerHTML") or ""
                                href_matches = re.findall(r'href=["\']([^"\']+)["\']', row_html)
                                for href in href_matches:
                                    if "job" in href or "career" in href:
                                        if href.startswith("http"):
                                            job["details_url"] = href
                                        elif href.startswith("/"):
                                            job["details_url"] = f"https://csc.gov.ph{href}"
                                        break
                            except Exception:
                                pass
                except (IndexError, Exception) as e:
                    log.warn(f"Error extracting row data: {e}")
                    continue
                if job.get("agency") or job.get("position_title"):
                    rows.append(job)
        except Exception as e:
            log.error(f"Error scraping table: {e}")
        return rows

    def scrape_all_pages(self) -> list[dict]:
        """Scrape job listings from all DataTable pages."""
        all_jobs = []
        page_num = 1
        while True:
            log.info(f"Scraping page {page_num}...")
            page_jobs = self.scrape_current_page()
            if not page_jobs:
                log.info(f"No jobs found on page {page_num}, stopping.")
                break
            all_jobs.extend(page_jobs)
            log.ok(f"Page {page_num}: scraped {len(page_jobs)} job(s) "
                   f"(total: {len(all_jobs)})")
            if config.MAX_PAGES > 0 and page_num >= config.MAX_PAGES:
                log.info(f"Reached max page limit ({config.MAX_PAGES})")
                break
            if not self._go_to_next_page():
                log.info("No more pages available.")
                break
            page_num += 1
            time.sleep(config.REQUEST_DELAY)
        return all_jobs

    def _go_to_next_page(self) -> bool:
        """Click the 'Next' button in the DataTable pagination. Returns False if no next page."""
        try:
            next_btn = self._find_element_flexible(
                selectors=[
                    (By.CSS_SELECTOR, ".dataTables_paginate .next:not(.disabled)"),
                    (By.CSS_SELECTOR, ".paginate_button.next:not(.disabled)"),
                    (By.XPATH, "//a[contains(@class,'next') and not(contains(@class,'disabled'))]"),
                    (By.XPATH, "//li[contains(@class,'next') and not(contains(@class,'disabled'))]/a"),
                ],
                description="Next page button",
                quiet=True
            )
            if next_btn:
                classes = next_btn.get_attribute("class") or ""
                if "disabled" in classes:
                    return False
                next_btn.click()
                time.sleep(1)
                self._wait_for_table_load()
                return True
        except Exception:
            pass
        return False

    def _find_element_flexible(self, selectors: list, description: str, quiet: bool = False):
        """Try multiple selectors to find an element. Returns the first match or None."""
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element and element.is_displayed():
                    return element
            except Exception:
                continue
        if not quiet:
            log.warn(f"Could not find element: {description}")
        return None

    def _wait_for_table_load(self):
        """Wait for the DataTable to finish loading/processing."""
        try:
            processing = self.driver.find_elements(By.CSS_SELECTOR, ".dataTables_processing")
            if processing:
                self.wait.until(
                    lambda d: not any(
                        p.is_displayed()
                        for p in d.find_elements(By.CSS_SELECTOR, ".dataTables_processing")
                    )
                )
        except Exception:
            time.sleep(2)

    def get_table_info(self) -> str:
        """Get the DataTable info text (e.g., 'Showing 1 to 10 of 50 entries')."""
        try:
            info = self._find_element_flexible(
                selectors=[
                    (By.CSS_SELECTOR, ".dataTables_info"),
                    (By.CSS_SELECTOR, "[id*='_info']"),
                ],
                description="Table info",
                quiet=True
            )
            return info.text.strip() if info else ""
        except Exception:
            return ""


def _parse_date(date_str: str):
    """Try to parse a date string using the formats defined in config."""
    date_str = date_str.strip()
    if not date_str:
        return None
    for fmt in config.CLOSING_DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def filter_expired_jobs(jobs: list[dict]) -> list[dict]:
    """Remove jobs whose closing date is before today."""
    today = datetime.now().date()
    active = []
    skipped = 0
    for job in jobs:
        closing_str = job.get("closing_date", "")
        closing_date = _parse_date(closing_str)
        if closing_date is None:
            active.append(job)
        elif closing_date >= today:
            active.append(job)
        else:
            skipped += 1
    if skipped:
        log.info(f"Filtered out {skipped} expired job(s) (closing date before {today})")
    log.ok(f"{len(active)} active (non-expired) job(s) remaining")
    return active


def save_results(jobs: list[dict], output_format: str, output_dir: str, filename: str):
    """Save scraped jobs to CSV and/or JSON files."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = os.path.join(output_dir, f"{filename}_{timestamp}")
    def _sort_key(job):
        parsed = _parse_date(job.get("closing_date", ""))
        return parsed if parsed else datetime.max.date()
    jobs = sorted(jobs, key=_sort_key)
    log.ok("Sorted results by closing date (earliest → latest)")
    saved_files = []
    if output_format in ("csv", "both"):
        csv_path = f"{base_path}.csv"
        if HAS_PANDAS:
            df = pd.DataFrame(jobs)
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        else:
            if jobs:
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
                    writer.writeheader()
                    writer.writerows(jobs)
        saved_files.append(csv_path)
        log.ok(f"CSV saved: {csv_path}")
    if output_format in ("json", "both"):
        json_path = f"{base_path}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        saved_files.append(json_path)
        log.ok(f"JSON saved: {json_path}")
    return saved_files


def print_summary(jobs: list[dict]):
    """Print a formatted summary of scraped jobs to the console."""
    if not jobs:
        log.warn("No jobs found matching your criteria.")
        return
    log.header(f"RESULTS: {len(jobs)} Job(s) Found")
    print(f"{'#':<4} {'Agency':<35} {'Position':<40} {'Closing Date':<15}")
    print("─" * 94)
    for i, job in enumerate(jobs, 1):
        agency = (job.get("agency", "")[:33] + "..") if len(job.get("agency", "")) > 35 else job.get("agency", "")
        position = (job.get("position_title", "")[:38] + "..") if len(job.get("position_title", "")) > 40 else job.get("position_title", "")
        closing = job.get("closing_date", "")
        print(f"{i:<4} {agency:<35} {position:<40} {closing:<15}")
    print("─" * 94)
    print()


def parse_args():
    """Parse command-line arguments, falling back to config.py defaults."""
    parser = argparse.ArgumentParser(
        description="Scrape CSC Career Portal job listings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape.py
  python scrape.py --no-interactive --position "engineer" --region "NCR"
  python scrape.py --search "cebu" --headless false
  python scrape.py --format csv --output ./results
        """
    )
    parser.add_argument("--position", default=config.POSITION_FILTER,
                        help=f"Position keyword (default: '{config.POSITION_FILTER}')")
    parser.add_argument("--agency", default=config.AGENCY_FILTER,
                        help=f"Agency name (default: '{config.AGENCY_FILTER}')")
    parser.add_argument("--region", default=config.REGION_FILTER,
                        help=f"Region (default: '{config.REGION_FILTER}')")
    parser.add_argument("--search", default=config.SEARCH_KEYWORD,
                        help=f"Search keyword (default: '{config.SEARCH_KEYWORD}')")
    parser.add_argument("--headless", default=str(config.HEADLESS).lower(),
                        choices=["true", "false"],
                        help=f"Run headless (default: {config.HEADLESS})")
    parser.add_argument("--format", default=config.OUTPUT_FORMAT,
                        choices=["csv", "json", "both"],
                        help=f"Output format (default: '{config.OUTPUT_FORMAT}')")
    parser.add_argument("--output", default=config.OUTPUT_DIR,
                        help=f"Output directory (default: '{config.OUTPUT_DIR}')")
    parser.add_argument("--filename", default=config.OUTPUT_FILENAME,
                        help=f"Output filename base (default: '{config.OUTPUT_FILENAME}')")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Skip interactive prompts and use defaults/CLI args directly")
    return parser.parse_args()


REGIONS = [
    "All Regions", "NCR", "CAR", "Region I", "Region II", "Region III",
    "Region IV-A", "Region IV-B", "Region V", "Region VI", "Region VII",
    "Region VIII", "Region IX", "Region X", "Region XI", "Region XII",
    "Region XIII", "BARMM",
]


def interactive_prompt(defaults: dict) -> dict:
    """Prompt the user for filter values interactively."""
    print()
    print("-" * 50)
    print("  Configure Search Filters")
    print("  (Press Enter to keep the default value)")
    print("-" * 50)
    print()
    default_pos = defaults.get("position", "")
    pos_input = input(f"  Position [{default_pos or 'any'}]: ").strip()
    position = pos_input if pos_input else default_pos
    print()
    print("  Region -- pick a number:")
    print()
    for i, region in enumerate(REGIONS):
        marker = ""
        if region == defaults.get("region", ""):
            marker = "  <-- default"
        print(f"    {i:>2}  {region}{marker}")
    print()
    default_region = defaults.get("region", "")
    region_input = input(f"  Enter number [{default_region or 'All Regions'}]: ").strip()
    if region_input.isdigit() and 0 <= int(region_input) < len(REGIONS):
        region = REGIONS[int(region_input)]
        if region == "All Regions":
            region = ""
    elif region_input == "":
        region = default_region
    else:
        region = default_region
    print()
    default_search = defaults.get("search", "")
    search_input = input(f"  Search keyword [{default_search or 'none'}]: ").strip()
    search = search_input if search_input else default_search
    print()
    print("-" * 50)
    print()
    return {
        "position": position,
        "agency": defaults.get("agency", ""),
        "region": region,
        "search": search,
    }


def run_scrape(filters: dict, headless: bool = True) -> list[dict]:
    """
    Run a full scrape with the given filters and return job dicts.
    Always closes the browser. Does not write files or prompt.
    """
    driver = None
    try:
        log.info("Launching Chrome browser...")
        driver = create_driver(headless=headless)
        log.ok("Browser launched")
        scraper = CSCScraper(driver, filters)
        scraper.navigate_to_career_page()
        scraper.apply_filters()
        scraper.set_entries_per_page()
        scraper.apply_search()
        info = scraper.get_table_info()
        if info:
            log.info(f"Table info: {info}")
        jobs = scraper.scrape_all_pages()
        if config.FILTER_EXPIRED:
            total_before = len(jobs)
            jobs = filter_expired_jobs(jobs)
            log.info(f"Kept {len(jobs)} of {total_before} job(s) after expiry filter")
        return jobs
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            log.info("Browser closed.")
            if sys.platform == "win32":
                try:
                    import subprocess
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "chromedriver.exe"],
                        capture_output=True,
                        check=False,
                    )
                except Exception:
                    pass


def main():
    args = parse_args()
    log.header("CSC Career Portal Scraper")
    defaults = {
        "position": args.position,
        "agency": args.agency,
        "region": args.region,
        "search": args.search,
    }
    if not args.no_interactive:
        filters = interactive_prompt(defaults)
    else:
        filters = defaults
    headless = args.headless.lower() == "true"
    log.info("Filters:")
    log.info(f"  Position : {filters['position'] or '(any)'}")
    log.info(f"  Agency   : {filters['agency'] or '(any)'}")
    log.info(f"  Region   : {filters['region'] or '(any)'}")
    log.info(f"  Search   : {filters['search'] or '(none)'}")
    log.info(f"  Headless : {headless}")
    print()
    try:
        jobs = run_scrape(filters, headless=headless)
        print_summary(jobs)
        if jobs:
            saved = save_results(jobs, args.format, args.output, args.filename)
            print()
            log.header("EXPORT COMPLETE")
            for f in saved:
                log.ok(f"  → {os.path.abspath(f)}")
        else:
            log.warn("No data to export.")
        print()
        log.ok(f"Done! Scraped {len(jobs)} job listing(s).")
    except KeyboardInterrupt:
        log.warn("Interrupted by user.")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
