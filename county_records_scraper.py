"""
County Tax Records Scraper - South Texas
Extracts property valuations and records from county appraisal districts
Sources: Hidalgo, Cameron, Starr County Appraisal Districts
Primary data: Assessed values, land use, ownership, tax history
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
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
        """Initialize SQLite database for county records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create county records table
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
        """Search for property in Hidalgo County records"""
        logger.info(f"Searching Hidalgo County for: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate to Hidalgo Appraisal District
                page.goto(self.county["property_search_api"], timeout=30000)

                # Wait for search box and enter address
                page.fill("input[placeholder*='address'], input[name*='address']", address)
                page.press("input[placeholder*='address'], input[name*='address']", "Enter")

                # Wait for results
                page.wait_for_selector("table, div[class*='result']", timeout=10000)

                # Extract property data from results
                properties = page.evaluate("""
                    () => {
                        const results = [];
                        const rows = document.querySelectorAll('table tr, div[class*="property-item"]');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, div[class*="property"]');
                            if (cells.length > 0) {
                                results.push({
                                    parcel_number: cells[0]?.textContent || '',
                                    property_address: cells[1]?.textContent || '',
                                    owner_name: cells[2]?.textContent || '',
                                    assessed_value: cells[3]?.textContent || ''
                                });
                            }
                        });
                        return results;
                    }
                """)

                logger.info(f"Found {len(properties)} properties")
                return properties

            except Exception as e:
                logger.error(f"Error searching Hidalgo County: {e}")
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
                # Navigate to property detail page
                detail_url = f"{self.county['appraisal_url']}/parcel/{parcel_id}"
                page.goto(detail_url, timeout=30000)

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

                return details

            except Exception as e:
                logger.error(f"Error fetching details: {e}")
                return {}

            finally:
                context.close()
                browser.close()


class CameronCountyScraper(CountyRecordsScraper):
    """Cameron County Appraisal District scraper"""

    def __init__(self):
        super().__init__("cameron")

    def search_property(self, address):
        """Search for property in Cameron County records"""
        logger.info(f"Searching Cameron County for: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate to Cameron County Appraisal District
                page.goto(self.county["property_search_api"], timeout=30000)

                # Wait for search box and enter address
                page.fill("input[placeholder*='address'], input[name*='address'], input[id*='search']", address)
                page.press("input[placeholder*='address'], input[name*='address'], input[id*='search']", "Enter")

                # Wait for results
                page.wait_for_selector("table, div[class*='result'], tr, div[class*='property']", timeout=10000)

                # Extract property data from results
                properties = page.evaluate("""
                    () => {
                        const results = [];
                        const rows = document.querySelectorAll('table tr, div[class*="property-item"], div[class*="result-row"]');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, div[class*="cell"], div[class*="property"]');
                            if (cells.length > 0) {
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

                logger.info(f"Found {len(properties)} properties in Cameron County")
                return properties

            except Exception as e:
                logger.error(f"Error searching Cameron County: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        """Get detailed property information for Cameron County"""
        logger.info(f"Fetching details for Cameron parcel: {parcel_id}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate to property detail page
                detail_url = f"{self.county['appraisal_url']}/parcel/{parcel_id}"
                page.goto(detail_url, timeout=30000)

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

                return details

            except Exception as e:
                logger.error(f"Error fetching Cameron details: {e}")
                return {}

            finally:
                context.close()
                browser.close()


class StarrCountyScraper(CountyRecordsScraper):
    """Starr County Appraisal District scraper"""

    def __init__(self):
        super().__init__("starr")

    def search_property(self, address):
        """Search for property in Starr County records"""
        logger.info(f"Searching Starr County for: {address}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate to Starr County Appraisal District
                page.goto(self.county["property_search_api"], timeout=30000)

                # Wait for search box and enter address
                page.fill("input[placeholder*='address'], input[name*='address'], input[id*='search']", address)
                page.press("input[placeholder*='address'], input[name*='address'], input[id*='search']", "Enter")

                # Wait for results
                page.wait_for_selector("table, div[class*='result'], tr, div[class*='property']", timeout=10000)

                # Extract property data from results
                properties = page.evaluate("""
                    () => {
                        const results = [];
                        const rows = document.querySelectorAll('table tr, div[class*="property-item"], div[class*="result-row"]');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, div[class*="cell"], div[class*="property"]');
                            if (cells.length > 0) {
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

                logger.info(f"Found {len(properties)} properties in Starr County")
                return properties

            except Exception as e:
                logger.error(f"Error searching Starr County: {e}")
                return []

            finally:
                context.close()
                browser.close()

    def get_property_details(self, parcel_id):
        """Get detailed property information for Starr County"""
        logger.info(f"Fetching details for Starr parcel: {parcel_id}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            try:
                # Navigate to property detail page
                detail_url = f"{self.county['appraisal_url']}/parcel/{parcel_id}"
                page.goto(detail_url, timeout=30000)

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

                return details

            except Exception as e:
                logger.error(f"Error fetching Starr details: {e}")
                return {}

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
        """Search for property across all three counties"""
        logger.info(f"\nSearching all counties for: {address}\n")

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

    parser = argparse.ArgumentParser(description="County Tax Records Scraper")
    parser.add_argument("--address", help="Property address to search")
    parser.add_argument("--county", choices=["hidalgo", "cameron", "starr"],
                        help="Search specific county")
    parser.add_argument("--parcel", help="Parcel ID to get details for")

    args = parser.parse_args()

    manager = CountyRecordsManager()

    if args.address:
        if args.county:
            # Search specific county
            results = manager.scrapers[args.county].search_property(args.address)
            logger.info(f"Found {len(results)} properties in {args.county}")
        else:
            # Search all counties
            results = manager.search_all_counties(args.address)
            total = sum(len(r) for r in results.values())
            logger.info(f"Found {total} properties total across all counties")

    elif args.parcel and args.county:
        # Get specific property details
        details = manager.get_details(args.county, args.parcel)
        logger.info(f"Property details: {json.dumps(details, indent=2)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
