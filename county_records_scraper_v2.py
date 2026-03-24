"""
County Tax Records Scraper v2 - Enhanced with Better Timeouts & Debugging
Extracts property valuations from Hidalgo, Cameron, Starr County Appraisal Districts
With retry logic, flexible selectors, and aggressive timeouts
"""

import json
import sqlite3
import os
import time
import logging
from datetime import datetime
from abc import ABC, abstractmethod

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    exit(1)

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
with open("county_records_config.json", "r") as f:
    CONFIG = json.load(f)

COUNTIES = CONFIG["counties"]
DB_PATH = CONFIG["database"]
SCRAPE_CONFIG = CONFIG["scraping"]


class CountyRecordsScraper(ABC):
    """Abstract base class for county-specific scrapers"""

    def __init__(self, county_key):
        self.county_key = county_key
        self.county = COUNTIES[county_key]
        self.db_path = DB_PATH
        self.timeout_ms = SCRAPE_CONFIG["element_wait_timeout_seconds"] * 1000
        self.page_timeout_ms = SCRAPE_CONFIG["page_load_timeout_seconds"] * 1000
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for county records"""
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
        logger.info(f"Database initialized for {self.county['name']}")

    @abstractmethod
    def search_property(self, address):
        """Search for property by address - implemented by subclasses"""
        pass

    @abstractmethod
    def get_property_details(self, parcel_id):
        """Get detailed property information - implemented by subclasses"""
        pass

    def save_record(self, record):
        """Save county record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO county_records (
                    county, parcel_number, account_number, property_address,
                    city, zip_code, owner_name, owner_address, owner_city,
                    owner_state, owner_zip, legal_description, property_type,
                    land_use_code, assessed_value, market_value, appraised_value,
                    tax_year, exemptions, homestead_exemption,
                    sqft_building, sqft_land, lot_size_sqft, year_built,
                    bedrooms, bathrooms, stories, roof_type, foundation_type,
                    quality_grade, condition_rating, total_tax_amount,
                    last_sale_price, last_sale_date, deed_book, deed_page,
                    latitude, longitude, raw_json, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.county_key,
                record.get("parcel_number"),
                record.get("account_number"),
                record.get("property_address"),
                record.get("city"),
                record.get("zip_code"),
                record.get("owner_name"),
                record.get("owner_address"),
                record.get("owner_city"),
                record.get("owner_state"),
                record.get("owner_zip"),
                record.get("legal_description"),
                record.get("property_type"),
                record.get("land_use_code"),
                record.get("assessed_value"),
                record.get("market_value"),
                record.get("appraised_value"),
                record.get("tax_year"),
                record.get("exemptions"),
                record.get("homestead_exemption"),
                record.get("sqft_building"),
                record.get("sqft_land"),
                record.get("lot_size_sqft"),
                record.get("year_built"),
                record.get("bedrooms"),
                record.get("bathrooms"),
                record.get("stories"),
                record.get("roof_type"),
                record.get("foundation_type"),
                record.get("quality_grade"),
                record.get("condition_rating"),
                record.get("total_tax_amount"),
                record.get("last_sale_price"),
                record.get("last_sale_date"),
                record.get("deed_book"),
                record.get("deed_page"),
                record.get("latitude"),
                record.get("longitude"),
                json.dumps(record),
                datetime.now().isoformat()
            ))

            conn.commit()
            logger.debug(f"Saved record for {record.get('parcel_number')}")

        except sqlite3.IntegrityError:
            logger.debug(f"Record already exists: {record.get('parcel_number')}")
        finally:
            conn.close()


class HidalgoCountyScraper(CountyRecordsScraper):
    """Hidalgo County Appraisal District scraper"""

    def __init__(self):
        super().__init__("hidalgo")

    def search_property(self, address):
        """Search for property in Hidalgo County records with enhanced timeout handling"""
        logger.info(f"=== HIDALGO COUNTY SEARCH: {address} ===")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate with aggressive timeouts
                url = self.county["property_search_api"]
                logger.info(f"Navigating to: {url}")
                logger.info(f"Timeout: {self.page_timeout_ms}ms")

                page.goto(url, timeout=self.page_timeout_ms, wait_until="domcontentloaded")
                logger.info("Page loaded successfully")

                # Wait for page to fully stabilize
                page.wait_for_timeout(3000)
                logger.debug("Page stabilization complete")

                # Try multiple selector patterns for search input
                search_selectors = [
                    "input[placeholder*='address']",
                    "input[name*='address']",
                    "input[id*='search']",
                    "input[id*='address']",
                    "input[type='text']",
                    "input[placeholder*='Property']",
                    "input[placeholder*='Address']"
                ]

                search_input_selector = None
                for selector in search_selectors:
                    try:
                        logger.debug(f"Trying selector: {selector}")
                        element = page.locator(selector).first
                        if element.is_visible(timeout=5000):
                            search_input_selector = selector
                            logger.info(f"✓ Found search input: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"✗ Selector failed: {selector} - {e}")
                        continue

                if not search_input_selector:
                    logger.error("❌ Could not find any search input field")
                    logger.info("Dumping page source for debugging...")
                    html = page.content()[:500]
                    logger.info(f"Page HTML: {html}")
                    return []

                # Fill search field
                logger.info(f"Filling search field with: {address}")
                page.fill(search_input_selector, address)
                page.wait_for_timeout(1000)

                # Submit search
                logger.info("Submitting search...")
                page.press(search_input_selector, "Enter")

                # Wait for results with very long timeout
                logger.info(f"Waiting for results (timeout: {self.timeout_ms}ms)...")
                try:
                    page.wait_for_selector(
                        "table, tbody, tr, div[class*='result'], div[class*='property'], div[class*='listing']",
                        timeout=self.timeout_ms
                    )
                    logger.info("✓ Results found")
                except Exception as e:
                    logger.warning(f"Results selector timeout: {e}")
                    logger.info("Continuing anyway - page may have results...")

                # Wait a bit more for content to render
                page.wait_for_timeout(2000)

                # Extract property data
                logger.info("Extracting property data...")
                properties = page.evaluate("""
                    () => {
                        const results = [];

                        // Get all potential result rows
                        const rows = document.querySelectorAll(
                            'table tr, tbody tr, div[class*="result"], div[class*="property"], div[class*="listing"], div[class*="item"]'
                        );

                        console.log('Found ' + rows.length + ' potential rows');

                        rows.forEach((row, idx) => {
                            const text = row.textContent.trim();

                            // Skip empty and header rows
                            if (text.length < 10 || text.toLowerCase().includes('parcel')) {
                                return;
                            }

                            // Try to extract data from different structures
                            const cells = row.querySelectorAll('td, div[class*="cell"], span, a');
                            const data = {
                                raw_text: text,
                                parcel_number: cells[0]?.textContent?.trim() || '',
                                property_address: cells[1]?.textContent?.trim() || '',
                                owner_name: cells[2]?.textContent?.trim() || '',
                                assessed_value: cells[3]?.textContent?.trim() || '',
                                html_class: row.className || 'unknown'
                            };

                            results.push(data);
                        });

                        return {
                            count: results.length,
                            properties: results
                        };
                    }
                """)

                logger.info(f"✓ Extracted {properties['count']} rows from page")

                # Clean up results
                cleaned_results = []
                for prop in properties.get('properties', [])[:20]:  # Limit to first 20
                    if prop['property_address'] or prop['parcel_number']:
                        cleaned_results.append({
                            'parcel_number': prop['parcel_number'],
                            'property_address': prop['property_address'],
                            'owner_name': prop['owner_name'],
                            'assessed_value': prop['assessed_value']
                        })

                logger.info(f"✓ Found {len(cleaned_results)} valid properties")
                return cleaned_results

            except Exception as e:
                logger.error(f"❌ Error searching Hidalgo County: {e}", exc_info=True)
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        """Get detailed property information for Hidalgo County"""
        logger.info(f"Fetching details for Hidalgo parcel: {parcel_id}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                detail_url = f"{self.county['appraisal_url']}/parcel/{parcel_id}"
                logger.info(f"Navigating to: {detail_url}")
                page.goto(detail_url, timeout=self.page_timeout_ms)

                # Extract property details
                details = page.evaluate("""
                    () => {
                        return {
                            parcel_number: document.querySelector('[data-parcel]')?.textContent || '',
                            assessed_value: document.querySelector('[data-assessed]')?.textContent || '',
                            market_value: document.querySelector('[data-market]')?.textContent || '',
                            year_built: document.querySelector('[data-year]')?.textContent || '',
                            sqft_building: document.querySelector('[data-sqft]')?.textContent || '',
                            property_type: document.querySelector('[data-type]')?.textContent || ''
                        };
                    }
                """)

                logger.info(f"✓ Retrieved details for parcel {parcel_id}")
                return details

            except Exception as e:
                logger.error(f"Error fetching Hidalgo details: {e}")
                return {}

            finally:
                context.close()
                browser.close()


class CameronCountyScraper(CountyRecordsScraper):
    """Cameron County Appraisal District scraper"""

    def __init__(self):
        super().__init__("cameron")

    def search_property(self, address):
        """Search for property in Cameron County"""
        logger.info(f"=== CAMERON COUNTY SEARCH: {address} ===")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                url = self.county["property_search_api"]
                logger.info(f"Navigating to: {url}")
                page.goto(url, timeout=self.page_timeout_ms, wait_until="domcontentloaded")
                logger.info("Page loaded")

                page.wait_for_timeout(3000)

                # Try multiple selectors
                search_selectors = [
                    "input[placeholder*='address']",
                    "input[id*='address']",
                    "input[name*='address']",
                    "input[type='text']",
                    "input[placeholder*='Address']"
                ]

                search_input_selector = None
                for selector in search_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible(timeout=5000):
                            search_input_selector = selector
                            logger.info(f"✓ Found search input: {selector}")
                            break
                    except:
                        pass

                if not search_input_selector:
                    logger.error("❌ No search input found")
                    return []

                logger.info(f"Searching for: {address}")
                page.fill(search_input_selector, address)
                page.wait_for_timeout(1000)
                page.press(search_input_selector, "Enter")

                logger.info(f"Waiting for results...")
                try:
                    page.wait_for_selector(
                        "table, tr, div[class*='result'], div[class*='property']",
                        timeout=self.timeout_ms
                    )
                except:
                    logger.warning("Results timeout - continuing...")

                page.wait_for_timeout(2000)

                properties = page.evaluate("""
                    () => {
                        const results = [];
                        const rows = document.querySelectorAll('table tr, div[class*="result"], div[class*="property"], tr');
                        rows.forEach(row => {
                            const text = row.textContent.trim();
                            if (text.length > 10) {
                                const cells = row.querySelectorAll('td, div, span');
                                results.push({
                                    parcel_number: cells[0]?.textContent?.trim() || '',
                                    property_address: cells[1]?.textContent?.trim() || '',
                                    owner_name: cells[2]?.textContent?.trim() || '',
                                    assessed_value: cells[3]?.textContent?.trim() || ''
                                });
                            }
                        });
                        return results;
                    }
                """)

                logger.info(f"✓ Found {len(properties)} properties")
                return properties

            except Exception as e:
                logger.error(f"❌ Error searching Cameron County: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        """Get property details from Cameron County"""
        return {}


class StarrCountyScraper(CountyRecordsScraper):
    """Starr County Appraisal District scraper"""

    def __init__(self):
        super().__init__("starr")

    def search_property(self, address):
        """Search for property in Starr County"""
        logger.info(f"=== STARR COUNTY SEARCH: {address} ===")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                url = self.county["property_search_api"]
                logger.info(f"Navigating to: {url}")
                page.goto(url, timeout=self.page_timeout_ms, wait_until="domcontentloaded")
                logger.info("Page loaded")

                page.wait_for_timeout(3000)

                search_selectors = [
                    "input[placeholder*='address']",
                    "input[id*='address']",
                    "input[name*='address']",
                    "input[type='text']"
                ]

                search_input_selector = None
                for selector in search_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible(timeout=5000):
                            search_input_selector = selector
                            logger.info(f"✓ Found search input: {selector}")
                            break
                    except:
                        pass

                if not search_input_selector:
                    logger.error("❌ No search input found")
                    return []

                logger.info(f"Searching for: {address}")
                page.fill(search_input_selector, address)
                page.wait_for_timeout(1000)
                page.press(search_input_selector, "Enter")

                logger.info("Waiting for results...")
                try:
                    page.wait_for_selector(
                        "table, tr, div[class*='result'], div[class*='property']",
                        timeout=self.timeout_ms
                    )
                except:
                    logger.warning("Results timeout - continuing...")

                page.wait_for_timeout(2000)

                properties = page.evaluate("""
                    () => {
                        const results = [];
                        const rows = document.querySelectorAll('table tr, div[class*="result"], tr');
                        rows.forEach(row => {
                            const text = row.textContent.trim();
                            if (text.length > 10) {
                                const cells = row.querySelectorAll('td, div, span');
                                results.push({
                                    parcel_number: cells[0]?.textContent?.trim() || '',
                                    property_address: cells[1]?.textContent?.trim() || '',
                                    owner_name: cells[2]?.textContent?.trim() || '',
                                    assessed_value: cells[3]?.textContent?.trim() || ''
                                });
                            }
                        });
                        return results;
                    }
                """)

                logger.info(f"✓ Found {len(properties)} properties")
                return properties

            except Exception as e:
                logger.error(f"❌ Error searching Starr County: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        """Get property details from Starr County"""
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
        """Search for property across all three counties"""
        logger.info(f"\n{'='*60}")
        logger.info(f"SEARCHING ALL COUNTIES FOR: {address}")
        logger.info(f"{'='*60}\n")

        results = {}
        for county_key, scraper in self.scrapers.items():
            try:
                results[county_key] = scraper.search_property(address)
            except Exception as e:
                logger.error(f"Error searching {county_key}: {e}")
                results[county_key] = []

        return results

    def get_details(self, county_key, parcel_id):
        """Get property details from specific county"""
        if county_key not in self.scrapers:
            logger.error(f"Unknown county: {county_key}")
            return {}

        return self.scrapers[county_key].get_property_details(parcel_id)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="County Tax Records Scraper v2")
    parser.add_argument("--address", help="Property address to search")
    parser.add_argument("--county", choices=["hidalgo", "cameron", "starr"],
                        help="Search specific county")
    parser.add_argument("--parcel", help="Parcel ID to get details for")

    args = parser.parse_args()

    manager = CountyRecordsManager()

    if args.address:
        if args.county:
            logger.info(f"Searching {args.county.upper()} only...")
            results = manager.scrapers[args.county].search_property(args.address)
            logger.info(f"Found {len(results)} properties")
        else:
            logger.info("Searching ALL counties...")
            results = manager.search_all_counties(args.address)
            total = sum(len(r) for r in results.values())
            logger.info(f"\n{'='*60}")
            logger.info(f"TOTAL RESULTS: {total} properties")
            logger.info(f"  Hidalgo: {len(results.get('hidalgo', []))} properties")
            logger.info(f"  Cameron: {len(results.get('cameron', []))} properties")
            logger.info(f"  Starr: {len(results.get('starr', []))} properties")
            logger.info(f"{'='*60}\n")

    elif args.parcel and args.county:
        details = manager.get_details(args.county, args.parcel)
        logger.info(f"Property details: {json.dumps(details, indent=2)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
