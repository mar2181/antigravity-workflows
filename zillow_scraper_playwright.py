"""
Zillow Scraper - Playwright UI Automation Method
Uses your saved cookies to log into Zillow and scrape via UI
Same approach as Facebook automation - more reliable than API calls
"""

import json
import sqlite3
import os
import time
import logging
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
with open("zillow_config.json", "r") as f:
    CONFIG = json.load(f)

COUNTIES = CONFIG["counties"]
PROPERTY_TYPES = CONFIG["property_types"]
IMAGE_SETTINGS = CONFIG["images"]
DB_PATH = CONFIG["database"]
COOKIES_FILE = CONFIG["cookies_file"]
IMAGES_DIR = IMAGE_SETTINGS["storage_dir"]


class ZillowScraperPlaywright:
    def __init__(self):
        self.db_path = DB_PATH
        self.cookies = self._load_cookies()
        self._init_database()
        os.makedirs(IMAGES_DIR, exist_ok=True)

    def _load_cookies(self):
        """Load cookies from JSON file"""
        if not os.path.exists(COOKIES_FILE):
            raise FileNotFoundError(f"Cookies file not found: {COOKIES_FILE}")

        with open(COOKIES_FILE, "r") as f:
            cookies_dict = json.load(f)

        logger.info(f"Loaded {len(cookies_dict)} cookies")
        return cookies_dict

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                zpid TEXT PRIMARY KEY,
                county TEXT NOT NULL,
                property_type TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                price INTEGER,
                price_per_sqft REAL,
                beds INTEGER,
                baths REAL,
                sqft INTEGER,
                lot_size_sqft INTEGER,
                year_built INTEGER,
                days_on_market INTEGER,
                status TEXT,
                listing_url TEXT,
                latitude REAL,
                longitude REAL,
                image_count INTEGER,
                images_downloaded INTEGER DEFAULT 0,
                raw_json TEXT,
                scraped_at TEXT,
                duplicate_flag INTEGER DEFAULT 0,
                duplicate_source TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zpid TEXT NOT NULL,
                image_index INTEGER,
                url_original TEXT,
                local_path TEXT,
                width INTEGER,
                height INTEGER,
                downloaded_at TEXT,
                FOREIGN KEY (zpid) REFERENCES properties(zpid)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def scrape_county(self, county_key, county_fips, county_name, property_type):
        """
        Scrape properties from Zillow for a county using Playwright
        """
        logger.info(f"\n[START] {county_name} - {property_type}")

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Add cookies
            for name, value in self.cookies.items():
                try:
                    context.add_cookies([{
                        "name": name,
                        "value": value,
                        "url": "https://www.zillow.com"
                    }])
                except:
                    pass  # Some cookies might not be valid for all URLs

            page = context.new_page()

            try:
                # Navigate to Zillow search
                logger.info(f"Navigating to Zillow search...")
                page.goto("https://www.zillow.com/homes/for_sale/", wait_until="domcontentloaded", timeout=60000)

                # Build search URL with filters
                search_url = self._build_search_url(county_fips, property_type)
                logger.info(f"Loading search: {search_url}")
                page.goto(search_url, wait_until="networkidle")

                # Wait for results to load
                time.sleep(2)

                # Extract properties from page
                properties_found = self._extract_properties_from_page(page, county_key, property_type)

                logger.info(f"Found {properties_found} properties in {county_name}")

                return properties_found

            except Exception as e:
                logger.error(f"Error scraping {county_name}: {e}")
                return 0

            finally:
                context.close()
                browser.close()

    def _build_search_url(self, county_fips, property_type):
        """Build Zillow search URL with filters"""
        # This is a simplified URL - in production we'd need to add proper filter parameters
        base_url = "https://www.zillow.com/homes/for_sale/"

        # County mapping to URL parameters (would need to expand this)
        county_map = {
            "48215": "mcallen_tx",  # Hidalgo
            "48061": "brownsville_tx",  # Cameron
            "48427": "rio_grande_city_tx"  # Starr
        }

        city = county_map.get(county_fips, "mcallen_tx")
        prop_type_filter = "for_sale" if property_type == "residential" else "for_sale"

        return f"{base_url}{city}/?searchQueryState=%7B%22pagination%22:%7B%7D,%22usersSearchTerm%22:%22%22%7D"

    def _extract_properties_from_page(self, page, county_key, property_type):
        """
        Extract property listings from rendered Zillow page
        Uses JavaScript to read data from page context
        """
        count = 0

        try:
            # Zillow stores search results in window.__INITIAL_STATE__
            # Try to extract it via JavaScript
            initial_state = page.evaluate("""
                () => {
                    try {
                        return window.__INITIAL_STATE__?.searchPageState?.listResults || [];
                    } catch(e) {
                        return [];
                    }
                }
            """)

            if not initial_state:
                logger.warning("Could not extract initial state from page")
                return 0

            logger.info(f"Extracted {len(initial_state)} results from page")

            # Save each property
            for listing in initial_state:
                try:
                    prop = {
                        "zpid": str(listing.get("zpid", "")),
                        "address": listing.get("address", ""),
                        "city": listing.get("addressCity", ""),
                        "state": listing.get("addressState", ""),
                        "zip_code": listing.get("addressZipcode", ""),
                        "price": int(listing.get("price", 0)) if listing.get("price") else None,
                        "beds": listing.get("beds"),
                        "baths": listing.get("baths"),
                        "sqft": listing.get("livingArea"),
                        "lot_size_sqft": listing.get("lotSize"),
                        "year_built": listing.get("yearBuilt"),
                        "days_on_market": listing.get("daysOnZillow"),
                        "status": listing.get("statusType", ""),
                        "listing_url": f"https://www.zillow.com/homedetails/{listing.get('zpid')}_zpid",
                        "latitude": listing.get("latLong", {}).get("latitude"),
                        "longitude": listing.get("latLong", {}).get("longitude"),
                        "image_count": len(listing.get("photoThumbs", [])),
                        "raw_json": json.dumps(listing)
                    }

                    # Calculate price per sqft
                    if prop["price"] and prop["sqft"]:
                        prop["price_per_sqft"] = prop["price"] / prop["sqft"]

                    # Save to database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO properties (
                            zpid, county, property_type, address, city, state, zip_code,
                            price, price_per_sqft, beds, baths, sqft, lot_size_sqft,
                            year_built, days_on_market, status, listing_url,
                            latitude, longitude, image_count, raw_json, scraped_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        prop["zpid"], county_key, property_type, prop["address"],
                        prop["city"], prop["state"], prop["zip_code"],
                        prop["price"], prop.get("price_per_sqft"), prop["beds"],
                        prop["baths"], prop["sqft"], prop["lot_size_sqft"],
                        prop["year_built"], prop["days_on_market"], prop["status"],
                        prop["listing_url"], prop["latitude"], prop["longitude"],
                        prop["image_count"], prop["raw_json"],
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    conn.close()

                    count += 1

                except Exception as e:
                    logger.debug(f"Error processing listing: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting properties: {e}")

        return count

    def run_test(self):
        """Run a test scrape for Hidalgo County, residential"""
        county = COUNTIES["hidalgo"]
        properties = self.scrape_county(
            "hidalgo",
            county["fips"],
            county["name"],
            "residential"
        )

        logger.info(f"\n✅ Test complete: {properties} properties saved")
        return properties


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Zillow Playwright Scraper")
    parser.add_argument("--test", action="store_true", help="Run test scrape (1 county)")
    parser.add_argument("--full", action="store_true", help="Run full scrape (all counties)")

    args = parser.parse_args()

    scraper = ZillowScraperPlaywright()

    if args.test:
        scraper.run_test()
    elif args.full:
        logger.info("=" * 70)
        logger.info("ZILLOW PLAYWRIGHT SCRAPER - FULL RUN".center(70))
        logger.info("=" * 70)

        total = 0
        for county_key, county_info in COUNTIES.items():
            for prop_type in PROPERTY_TYPES:
                count = scraper.scrape_county(
                    county_key,
                    county_info["fips"],
                    county_info["name"],
                    prop_type
                )
                total += count

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ SCRAPING COMPLETE - {total} properties saved")
        logger.info(f"{'='*70}\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
