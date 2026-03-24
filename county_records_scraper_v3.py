"""
County Tax Records Scraper v3 - Ultra-Robust for JavaScript-Heavy Sites
Handles dynamically rendered pages with full DOM inspection
"""

import json
import sqlite3
import os
import time
import logging
from datetime import datetime
from abc import ABC, abstractmethod

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

    @abstractmethod
    def get_property_details(self, parcel_id):
        pass


class HidalgoCountyScraper(CountyRecordsScraper):
    """Hidalgo County with JavaScript support"""

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
                except PlaywrightTimeoutError as e:
                    logger.error(f"[HIDALGO] Navigation timeout/refused: {e}")
                    return []

                logger.info("[HIDALGO] Page loaded, waiting for JS to render...")

                # Wait for network idle (ensures all JS has run)
                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                    logger.info("[HIDALGO] Network idle reached")
                except:
                    logger.warning("[HIDALGO] Network idle timeout, continuing...")

                # Additional wait for rendering
                page.wait_for_timeout(3000)

                # Debug: dump page structure
                page_info = page.evaluate("""
                    () => {
                        return {
                            title: document.title,
                            inputs_count: document.querySelectorAll('input').length,
                            buttons_count: document.querySelectorAll('button').length,
                            forms_count: document.querySelectorAll('form').length,
                            all_inputs: Array.from(document.querySelectorAll('input')).map(i => ({
                                type: i.type,
                                placeholder: i.placeholder,
                                name: i.name,
                                id: i.id,
                                visible: i.offsetParent !== null
                            })).slice(0, 5)
                        };
                    }
                """)

                logger.info(f"[HIDALGO] Page info: {json.dumps(page_info, indent=2)}")

                # If no inputs on homepage, look for search/lookup link
                inputs = page.locator("input").all()
                logger.info(f"[HIDALGO] Found {len(inputs)} input fields")

                if not inputs:
                    logger.info("[HIDALGO] No inputs on homepage - looking for search link...")
                    links = page.locator("a").all()
                    logger.info(f"[HIDALGO] Found {len(links)} links")

                    # Try clicking a search/property/lookup link
                    for link in links:
                        try:
                            text = link.inner_text().lower()
                            if any(x in text for x in ['search', 'lookup', 'property', 'parcel', 'find']):
                                logger.info(f"[HIDALGO] Found search link: {text}, clicking...")
                                link.click()
                                page.wait_for_timeout(3000)
                                break
                        except:
                            pass

                    # Try buttons
                    buttons = page.locator("button").all()
                    for button in buttons:
                        try:
                            text = button.inner_text().lower()
                            if any(x in text for x in ['search', 'lookup', 'property']):
                                logger.info(f"[HIDALGO] Found search button: {text}, clicking...")
                                button.click()
                                page.wait_for_timeout(3000)
                                break
                        except:
                            pass

                    # Check inputs again after clicking
                    inputs = page.locator("input").all()
                    logger.info(f"[HIDALGO] After clicking, found {len(inputs)} input fields")

                if not inputs:
                    logger.error("[HIDALGO] Still no input fields")
                    return []

                # Type in first visible input
                for idx, inp in enumerate(inputs):
                    try:
                        if inp.is_visible():
                            logger.info(f"[HIDALGO] Using input #{idx}")
                            inp.clear()
                            inp.type(address, delay=100)
                            logger.info(f"[HIDALGO] Typed: {address}")
                            page.wait_for_timeout(500)

                            # Try to find and click search button
                            try:
                                search_btn = page.locator("button").first
                                if search_btn.is_visible():
                                    logger.info("[HIDALGO] Clicking search button")
                                    search_btn.click()
                                else:
                                    logger.info("[HIDALGO] Pressing Enter instead")
                                    inp.press("Enter")
                            except:
                                logger.info("[HIDALGO] Pressing Enter")
                                inp.press("Enter")

                            break
                    except Exception as e:
                        logger.debug(f"[HIDALGO] Input #{idx} failed: {e}")
                        continue

                # Wait for results
                logger.info("[HIDALGO] Waiting for results...")
                try:
                    page.wait_for_selector("table, tr, tbody, div[class*='result']", timeout=60000)
                    logger.info("[HIDALGO] Results found")
                except:
                    logger.warning("[HIDALGO] Results timeout")

                page.wait_for_timeout(2000)

                # Extract
                results = page.evaluate("""
                    () => {
                        const data = [];
                        const rows = document.querySelectorAll('table tr, tbody tr, div[class*="result"]');
                        rows.forEach(row => {
                            const text = row.textContent.trim();
                            if (text.length > 10) {
                                data.push({ raw: text });
                            }
                        });
                        return data;
                    }
                """)

                logger.info(f"[HIDALGO] Extracted {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"[HIDALGO] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        return {}


class CameronCountyScraper(CountyRecordsScraper):
    """Cameron County with JavaScript support"""

    def __init__(self):
        super().__init__("cameron")

    def search_property(self, address):
        logger.info(f"[CAMERON] Searching: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                url = self.county["property_search_api"]
                logger.info(f"[CAMERON] Opening: {url}")

                try:
                    page.goto(url, timeout=120000, wait_until="domcontentloaded")
                except PlaywrightTimeoutError as e:
                    logger.error(f"[CAMERON] Navigation failed: {e}")
                    return []

                logger.info("[CAMERON] Waiting for JS to render...")

                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(4000)

                # Debug
                page_info = page.evaluate("""
                    () => {
                        return {
                            title: document.title,
                            inputs: document.querySelectorAll('input').length,
                            body_text_sample: document.body.textContent.substring(0, 200)
                        };
                    }
                """)
                logger.info(f"[CAMERON] Page info: {page_info}")

                # Find and fill input
                inputs = page.locator("input").all()
                logger.info(f"[CAMERON] Found {len(inputs)} inputs")

                if not inputs:
                    logger.error("[CAMERON] No inputs found")
                    return []

                for idx, inp in enumerate(inputs):
                    try:
                        if inp.is_visible():
                            logger.info(f"[CAMERON] Using input #{idx}")
                            inp.clear()
                            inp.type(address, delay=100)
                            page.wait_for_timeout(500)
                            inp.press("Enter")
                            break
                    except:
                        continue

                logger.info("[CAMERON] Waiting for results...")
                try:
                    page.wait_for_selector("table, tr, div[class*='result']", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(2000)

                results = page.evaluate("() => { const data = []; document.querySelectorAll('table tr, div[class*=\"result\"]').forEach(r => { if(r.textContent.trim().length > 10) data.push({raw: r.textContent.trim()}); }); return data; }")

                logger.info(f"[CAMERON] Extracted {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"[CAMERON] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        return {}


class StarrCountyScraper(CountyRecordsScraper):
    """Starr County with JavaScript support"""

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
                except PlaywrightTimeoutError as e:
                    logger.error(f"[STARR] Navigation failed: {e}")
                    return []

                logger.info("[STARR] Waiting for JS to render...")

                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(4000)

                inputs = page.locator("input").all()
                logger.info(f"[STARR] Found {len(inputs)} inputs")

                if not inputs:
                    logger.error("[STARR] No inputs found")
                    return []

                for idx, inp in enumerate(inputs):
                    try:
                        if inp.is_visible():
                            logger.info(f"[STARR] Using input #{idx}")
                            inp.clear()
                            inp.type(address, delay=100)
                            page.wait_for_timeout(500)
                            inp.press("Enter")
                            break
                    except:
                        continue

                logger.info("[STARR] Waiting for results...")
                try:
                    page.wait_for_selector("table, tr, div[class*='result']", timeout=60000)
                except:
                    pass

                page.wait_for_timeout(2000)

                results = page.evaluate("() => { const data = []; document.querySelectorAll('table tr, div[class*=\"result\"]').forEach(r => { if(r.textContent.trim().length > 10) data.push({raw: r.textContent.trim()}); }); return data; }")

                logger.info(f"[STARR] Extracted {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"[STARR] Error: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        return {}


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

    parser = argparse.ArgumentParser(description="County Records Scraper v3")
    parser.add_argument("--address", help="Address to search")
    parser.add_argument("--county", choices=["hidalgo", "cameron", "starr"], help="Specific county")

    args = parser.parse_args()

    manager = CountyRecordsManager()

    if args.address:
        if args.county:
            results = manager.scrapers[args.county].search_property(args.address)
            logger.info(f"\nResults: {len(results)} found")
        else:
            results = manager.search_all_counties(args.address)
            total = sum(len(r) for r in results.values())
            logger.info(f"\n{'='*70}")
            logger.info(f"TOTAL: {total} properties")
            logger.info(f"  Hidalgo: {len(results['hidalgo'])}")
            logger.info(f"  Cameron: {len(results['cameron'])}")
            logger.info(f"  Starr: {len(results['starr'])}")
            logger.info(f"{'='*70}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
