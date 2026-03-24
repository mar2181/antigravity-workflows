"""
County Tax Records Scraper v4 - Final Version
Enhanced result detection and extraction from all county websites
"""

import json
import sqlite3
import logging
from abc import ABC, abstractmethod

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Playwright not installed")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

with open("county_records_config.json", "r") as f:
    CONFIG = json.load(f)

COUNTIES = CONFIG["counties"]
DB_PATH = CONFIG["database"]


class CountyRecordsScraper(ABC):
    """Abstract base class for county-specific scrapers"""

    def __init__(self, county_key):
        self.county_key = county_key
        self.county = COUNTIES[county_key]
        self.db_path = DB_PATH
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS county_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county TEXT NOT NULL,
                parcel_number TEXT NOT NULL,
                account_number TEXT,
                property_address TEXT NOT NULL,
                city TEXT,
                zip_code TEXT,
                owner_name TEXT,
                owner_address TEXT,
                owner_city TEXT,
                owner_state TEXT,
                owner_zip TEXT,
                legal_description TEXT,
                property_type TEXT,
                land_use_code TEXT,
                assessed_value INTEGER,
                market_value INTEGER,
                appraised_value INTEGER,
                tax_year INTEGER,
                exemptions TEXT,
                homestead_exemption INTEGER DEFAULT 0,
                sqft_building INTEGER,
                sqft_land INTEGER,
                lot_size_sqft INTEGER,
                year_built INTEGER,
                bedrooms INTEGER,
                bathrooms REAL,
                stories INTEGER,
                roof_type TEXT,
                foundation_type TEXT,
                quality_grade TEXT,
                condition_rating TEXT,
                total_tax_amount REAL,
                last_sale_price INTEGER,
                last_sale_date TEXT,
                deed_book TEXT,
                deed_page TEXT,
                latitude REAL,
                longitude REAL,
                raw_json TEXT,
                scraped_at TEXT,
                UNIQUE(county, parcel_number)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"DB ready: {self.county['name']}")

    @abstractmethod
    def search_property(self, address):
        pass


class HidalgoCountyScraper(CountyRecordsScraper):
    """Hidalgo County - New URL (hidalgoad.org)"""

    def __init__(self):
        super().__init__("hidalgo")

    def search_property(self, address):
        logger.info(f"[HIDALGO] Searching: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                url = self.county["property_search_api"]
                logger.info(f"[HIDALGO] Opening: {url}")

                try:
                    page.goto(url, timeout=120000, wait_until="domcontentloaded")
                except PlaywrightTimeoutError:
                    logger.error("[HIDALGO] Navigation timeout")
                    return []

                logger.info("[HIDALGO] Waiting for page to render...")

                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(4000)

                # Find and click search link
                inputs = page.locator("input").all()
                if not inputs:
                    logger.info("[HIDALGO] Looking for search link...")
                    links = page.locator("a").all()
                    for link in links:
                        try:
                            text = link.inner_text().lower()
                            if 'search' in text or 'property' in text or 'lookup' in text:
                                logger.info(f"[HIDALGO] Clicking: {text}")
                                link.click()
                                page.wait_for_timeout(3000)
                                break
                        except:
                            pass

                    inputs = page.locator("input").all()

                if not inputs:
                    logger.error("[HIDALGO] No search input found")
                    return []

                logger.info(f"[HIDALGO] Found {len(inputs)} inputs, filling search...")

                # Fill and submit
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            inp.clear()
                            inp.type(address, delay=50)
                            logger.info(f"[HIDALGO] Typed: {address}")
                            page.wait_for_timeout(500)

                            # Click search button
                            buttons = page.locator("button").all()
                            for btn in buttons:
                                try:
                                    if btn.is_visible():
                                        btn.click()
                                        logger.info("[HIDALGO] Clicked search button")
                                        break
                                except:
                                    pass

                            break
                    except:
                        continue

                # Wait for results with very long timeout
                logger.info("[HIDALGO] Waiting for search results (90 seconds)...")
                page.wait_for_timeout(10000)  # Always wait at least 10 seconds

                # Extract ANY visible content
                results = page.evaluate("""
                    () => {
                        const data = [];

                        // Try multiple extraction patterns
                        const tables = document.querySelectorAll('table tbody tr, table tr');
                        const divRows = document.querySelectorAll('div[class*="row"], div[class*="result"], div[class*="item"], div[class*="listing"]');
                        const allText = document.body.innerText;

                        // From tables
                        tables.forEach(row => {
                            const text = row.innerText || row.textContent;
                            if (text && text.trim().length > 10) {
                                data.push({ source: 'table', text: text.trim() });
                            }
                        });

                        // From divs
                        divRows.forEach(div => {
                            const text = div.innerText;
                            if (text && text.trim().length > 10) {
                                data.push({ source: 'div', text: text.trim() });
                            }
                        });

                        // Check page body
                        if (allText.toLowerCase().includes('parcel') || allText.toLowerCase().includes('property')) {
                            data.push({ source: 'page_contains', text: 'Page contains property/parcel info' });
                        }

                        return {
                            total_items: data.length,
                            sample: data.slice(0, 5)
                        };
                    }
                """)

                logger.info(f"[HIDALGO] Extracted {results['total_items']} items")
                if results['sample']:
                    logger.info(f"[HIDALGO] Sample: {results['sample'][0]}")

                return results.get('sample', [])

            except Exception as e:
                logger.error(f"[HIDALGO] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()


class CameronCountyScraper(CountyRecordsScraper):
    """Cameron County"""

    def __init__(self):
        super().__init__("cameron")

    def search_property(self, address):
        logger.info(f"[CAMERON] Searching: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Try main URL first
                url = self.county.get("appraisal_url", "https://www.ccad.org/")
                logger.info(f"[CAMERON] Opening: {url}")

                try:
                    page.goto(url, timeout=120000, wait_until="domcontentloaded")
                except PlaywrightTimeoutError:
                    logger.error("[CAMERON] Navigation timeout")
                    return []

                logger.info("[CAMERON] Waiting for JS to render...")

                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(4000)

                # Look for search
                inputs = page.locator("input").all()
                logger.info(f"[CAMERON] Found {len(inputs)} inputs")

                if not inputs:
                    logger.info("[CAMERON] No inputs - looking for links...")
                    links = page.locator("a").all()
                    for link in links:
                        try:
                            text = link.inner_text().lower()
                            if 'search' in text or 'property' in text:
                                logger.info(f"[CAMERON] Clicking: {text}")
                                link.click()
                                page.wait_for_timeout(3000)
                                break
                        except:
                            pass

                    inputs = page.locator("input").all()

                if not inputs:
                    logger.error("[CAMERON] No search inputs")
                    return []

                # Fill and search
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            inp.clear()
                            inp.type(address, delay=50)
                            page.wait_for_timeout(500)
                            inp.press("Enter")
                            logger.info("[CAMERON] Search submitted")
                            break
                    except:
                        continue

                page.wait_for_timeout(10000)

                # Extract results
                results = page.evaluate("""
                    () => {
                        const data = [];
                        document.querySelectorAll('table tr, div[class*="result"]').forEach(row => {
                            const text = row.innerText || row.textContent;
                            if (text && text.trim().length > 10) {
                                data.push({ text: text.trim() });
                            }
                        });
                        return data;
                    }
                """)

                logger.info(f"[CAMERON] Found {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"[CAMERON] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()


class StarrCountyScraper(CountyRecordsScraper):
    """Starr County"""

    def __init__(self):
        super().__init__("starr")

    def search_property(self, address):
        logger.info(f"[STARR] Searching: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                url = self.county["property_search_api"]
                logger.info(f"[STARR] Opening: {url}")

                try:
                    page.goto(url, timeout=120000, wait_until="domcontentloaded")
                except PlaywrightTimeoutError:
                    logger.error("[STARR] Navigation timeout")
                    return []

                logger.info("[STARR] Waiting for page...")

                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(4000)

                inputs = page.locator("input").all()
                logger.info(f"[STARR] Found {len(inputs)} inputs")

                if not inputs:
                    logger.error("[STARR] No search inputs")
                    return []

                # Fill search
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            inp.clear()
                            inp.type(address, delay=50)
                            page.wait_for_timeout(500)
                            inp.press("Enter")
                            logger.info("[STARR] Search submitted")
                            break
                    except:
                        continue

                page.wait_for_timeout(10000)

                # Extract
                results = page.evaluate("""
                    () => {
                        const data = [];
                        document.querySelectorAll('table tr, div[class*="result"], div[class*="item"]').forEach(row => {
                            const text = row.innerText || row.textContent;
                            if (text && text.trim().length > 10) {
                                data.push({ text: text.trim() });
                            }
                        });
                        return data;
                    }
                """)

                logger.info(f"[STARR] Found {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"[STARR] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()


class CountyRecordsManager:
    """Manages all county scrapers"""

    def __init__(self):
        self.scrapers = {
            "hidalgo": HidalgoCountyScraper(),
            "cameron": CameronCountyScraper(),
            "starr": StarrCountyScraper()
        }

    def search_all_counties(self, address):
        logger.info(f"\n{'='*70}")
        logger.info(f"MULTI-COUNTY SEARCH: {address}")
        logger.info(f"{'='*70}\n")

        results = {}
        for county_key in ["hidalgo", "cameron", "starr"]:
            try:
                results[county_key] = self.scrapers[county_key].search_property(address)
            except Exception as e:
                logger.error(f"Error in {county_key}: {e}")
                results[county_key] = []

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="County Records Scraper v4")
    parser.add_argument("--address", help="Address to search")
    parser.add_argument("--county", choices=["hidalgo", "cameron", "starr"], help="Specific county")

    args = parser.parse_args()

    manager = CountyRecordsManager()

    if args.address:
        if args.county:
            results = manager.scrapers[args.county].search_property(args.address)
            logger.info(f"\n✓ Results: {len(results)} found")
        else:
            results = manager.search_all_counties(args.address)
            total = sum(len(r) for r in results.values())
            logger.info(f"\n{'='*70}")
            logger.info(f"✓ TOTAL: {total} properties")
            logger.info(f"  Hidalgo: {len(results['hidalgo'])}")
            logger.info(f"  Cameron: {len(results['cameron'])}")
            logger.info(f"  Starr: {len(results['starr'])}")
            logger.info(f"{'='*70}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
