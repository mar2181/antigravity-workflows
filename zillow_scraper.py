"""
Zillow South Texas Property Data Extraction System
Scrapes residential and commercial properties from Zillow for Cameron, Hidalgo, and Starr Counties
Stores data in SQLite with local image downloads
"""

import json
import sqlite3
import requests
import os
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from difflib import SequenceMatcher
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
with open("zillow_config.json", "r") as f:
    CONFIG = json.load(f)

COUNTIES = CONFIG["counties"]
PROPERTY_TYPES = CONFIG["property_types"]
IMAGE_SETTINGS = CONFIG["images"]
DB_PATH = CONFIG["database"]
COOKIES_FILE = CONFIG["cookies_file"]
REQUEST_DELAY = CONFIG["request_delay_seconds"]
USER_AGENT = CONFIG["user_agent"]
IMAGES_DIR = IMAGE_SETTINGS["storage_dir"]


class ZillowScraper:
    def __init__(self):
        self.db_path = DB_PATH
        self.cookies = self._load_cookies()
        self.session = self._create_session()
        self._init_database()
        os.makedirs(IMAGES_DIR, exist_ok=True)

    def _load_cookies(self):
        """Load cookies from zillow_cookies.json"""
        if not os.path.exists(COOKIES_FILE):
            raise FileNotFoundError(
                f"Cookies file not found: {COOKIES_FILE}\n"
                "Run 'python save_zillow_auth.py' first to save your session."
            )

        with open(COOKIES_FILE, "r") as f:
            cookies_dict = json.load(f)

        logger.info(f"Loaded {len(cookies_dict)} cookies from {COOKIES_FILE}")
        return cookies_dict

    def _create_session(self):
        """Create requests session with cookies and headers"""
        session = requests.Session()

        # Add cookies
        for name, value in self.cookies.items():
            session.cookies.set(name, value)

        # Add headers
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.zillow.com/",
            "X-Requested-With": "XMLHttpRequest"
        })

        return session

    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create properties table
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

        # Create images table
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

    def search_county(self, county_fips, property_type, page=1):
        """
        Execute search on Zillow API for a county and property type
        Returns raw JSON response
        """
        url = "https://www.zillow.com/async-create-search-page-state"

        payload = {
            "searchQueryState": {
                "pagination": {"currentPage": page},
                "usersSearchTerm": "",
                "mapBounds": {},
                "regionSelection": [
                    {
                        "regionId": int(county_fips),
                        "regionType": 3  # County
                    }
                ],
                "filterState": {
                    "isAllHomes": {"value": True},
                    "propertyTypes": {
                        "value": [property_type.capitalize()]
                    },
                    "isListingVisible": {"value": True}
                },
                "isListVisible": True,
                "shouldHighlight": True,
                "isMap": False
            }
        }

        try:
            logger.info(
                f"Searching {county_fips} for {property_type} - Page {page}"
            )
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            time.sleep(REQUEST_DELAY)
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None

    def paginate_county(self, county_fips, property_type, max_pages=None):
        """
        Paginate through all results for a county/property type combination
        Yields raw property data from each page
        """
        page = 1
        total_count = 0
        properties_count = 0

        while True:
            if max_pages and page > max_pages:
                break

            data = self.search_county(county_fips, property_type, page)

            if not data or "searchResults" not in data:
                logger.warning(f"No search results for page {page}")
                break

            listings = data.get("searchResults", {}).get("listResults", [])

            if not listings:
                logger.info(f"No more listings on page {page}")
                break

            for listing in listings:
                yield listing
                properties_count += 1

            page += 1
            total_count = data.get("searchResults", {}).get("totalResultCount", 0)

            if properties_count >= total_count and total_count > 0:
                break

        logger.info(f"Paginated {properties_count} properties (Total: {total_count})")

    def extract_property(self, raw_data):
        """
        Parse a single property from raw Zillow JSON
        Returns dict with normalized fields
        """
        try:
            prop = {
                "zpid": str(raw_data.get("zpid", "")),
                "address": raw_data.get("address", ""),
                "city": raw_data.get("addressCity", ""),
                "state": raw_data.get("addressState", ""),
                "zip_code": raw_data.get("addressZipcode", ""),
                "price": int(raw_data.get("price", 0)) if raw_data.get("price") else None,
                "beds": raw_data.get("beds"),
                "baths": raw_data.get("baths"),
                "sqft": raw_data.get("livingArea"),
                "lot_size_sqft": raw_data.get("lotSize"),
                "year_built": raw_data.get("yearBuilt"),
                "days_on_market": raw_data.get("daysOnZillow"),
                "status": raw_data.get("statusType", ""),
                "listing_url": f"https://www.zillow.com/homedetails/{raw_data.get('zpid')}_zpid",
                "latitude": raw_data.get("latLong", {}).get("latitude"),
                "longitude": raw_data.get("latLong", {}).get("longitude"),
                "image_urls": raw_data.get("imgSrc", ""),
                "image_count": len(raw_data.get("photoThumbs", [])),
                "raw_json": json.dumps(raw_data)
            }

            # Calculate price per sqft if both available
            if prop["price"] and prop["sqft"]:
                prop["price_per_sqft"] = prop["price"] / prop["sqft"]

            return prop

        except Exception as e:
            logger.error(f"Error extracting property: {e}")
            return None

    def save_property(self, prop, county, property_type):
        """
        Insert or update property in SQLite database
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO properties (
                    zpid, county, property_type, address, city, state, zip_code,
                    price, price_per_sqft, beds, baths, sqft, lot_size_sqft,
                    year_built, days_on_market, status, listing_url,
                    latitude, longitude, image_count, raw_json, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prop["zpid"], county, property_type, prop["address"],
                prop["city"], prop["state"], prop["zip_code"],
                prop["price"], prop.get("price_per_sqft"), prop["beds"],
                prop["baths"], prop["sqft"], prop["lot_size_sqft"],
                prop["year_built"], prop["days_on_market"], prop["status"],
                prop["listing_url"], prop["latitude"], prop["longitude"],
                prop["image_count"], prop["raw_json"],
                datetime.now().isoformat()
            ))

            conn.commit()

        except sqlite3.IntegrityError as e:
            logger.debug(f"Property {prop['zpid']} already exists: {e}")
        finally:
            conn.close()

    def download_images(self, zpid, property_type, raw_data):
        """
        Download images for a property to local storage
        Prioritizes highest quality images (_e suffix)
        Downloads minimum 2, maximum 10 images
        """
        try:
            # Get image URLs from raw data
            photo_thumbs = raw_data.get("photoThumbs", [])
            if not photo_thumbs:
                return 0

            # Create property directory
            prop_dir = os.path.join(IMAGES_DIR, zpid)
            os.makedirs(prop_dir, exist_ok=True)

            # Download images
            downloaded = 0
            quality_order = IMAGE_SETTINGS["quality_suffix_order"]
            max_images = IMAGE_SETTINGS["max_per_property"]

            for idx, thumb_url in enumerate(photo_thumbs[:max_images]):
                if downloaded >= max_images:
                    break

                # Try quality variants
                image_saved = False
                for quality_suffix in quality_order:
                    # Replace quality suffix in URL
                    url = thumb_url.replace("_t.", f"{quality_suffix}.")

                    try:
                        response = self.session.get(url, timeout=15)
                        response.raise_for_status()

                        # Save image
                        filename = f"image_{idx + 1:02d}.jpg"
                        filepath = os.path.join(prop_dir, filename)

                        with open(filepath, "wb") as f:
                            f.write(response.content)

                        # Record in database
                        self._save_image_record(zpid, idx, url, filepath)
                        downloaded += 1
                        image_saved = True
                        logger.debug(f"Downloaded {filename} for {zpid}")
                        break

                    except requests.exceptions.RequestException:
                        continue

                if not image_saved:
                    logger.warning(f"Failed to download image {idx} for {zpid}")

                time.sleep(0.5)  # Small delay between downloads

            # Update property with download count
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE properties SET images_downloaded = ? WHERE zpid = ?",
                (downloaded, zpid)
            )
            conn.commit()
            conn.close()

            return downloaded

        except Exception as e:
            logger.error(f"Error downloading images for {zpid}: {e}")
            return 0

    def _save_image_record(self, zpid, image_index, url, filepath):
        """Record image metadata in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO images (zpid, image_index, url_original, local_path, downloaded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (zpid, image_index, url, filepath, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def flag_duplicates(self, zpid, address):
        """
        Check if property exists in other databases
        Currently checks against GMAR Matrix data if available
        """
        # TODO: Implement cross-database duplicate checking
        # For now, returns None (no duplicates found)
        pass

    def run_all(self):
        """
        Execute full scraping pipeline:
        - All 3 counties
        - Both property types (residential, commercial)
        - Paginate through all results
        - Download images
        - Flag duplicates
        """
        logger.info("=" * 70)
        logger.info("ZILLOW SOUTH TEXAS SCRAPER - STARTING FULL RUN")
        logger.info("=" * 70)

        total_properties = 0
        total_images = 0

        for county_key, county_info in COUNTIES.items():
            county_fips = county_info["fips"]
            county_name = county_info["name"]

            for prop_type in PROPERTY_TYPES:
                logger.info(f"\n[START] {county_name} - {prop_type}")

                try:
                    for raw_property in self.paginate_county(county_fips, prop_type):
                        # Extract and save property data
                        prop = self.extract_property(raw_property)
                        if prop:
                            self.save_property(prop, county_key, prop_type)

                            # Download images
                            images_downloaded = self.download_images(
                                prop["zpid"],
                                prop_type,
                                raw_property
                            )
                            if images_downloaded >= IMAGE_SETTINGS["min_per_property"]:
                                total_images += images_downloaded

                            total_properties += 1

                            if total_properties % 10 == 0:
                                logger.info(f"  Processed {total_properties} properties...")

                except Exception as e:
                    logger.error(f"Error processing {county_name}/{prop_type}: {e}")
                    continue

        logger.info("\n" + "=" * 70)
        logger.info(f"SCRAPING COMPLETE")
        logger.info(f"Total properties: {total_properties}")
        logger.info(f"Total images downloaded: {total_images}")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Images directory: {IMAGES_DIR}")
        logger.info("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Zillow South Texas Scraper")
    parser.add_argument("--county", choices=["hidalgo", "cameron", "starr"],
                        help="Scrape specific county")
    parser.add_argument("--type", choices=["residential", "commercial"],
                        help="Scrape specific property type")
    parser.add_argument("--pages", type=int, default=None,
                        help="Max pages to scrape (default: all)")
    parser.add_argument("--full", action="store_true",
                        help="Run full scrape (all counties, all types)")

    args = parser.parse_args()

    scraper = ZillowScraper()

    if args.full or (not args.county and not args.type):
        scraper.run_all()
    else:
        # Single county/type run
        if args.county and args.type:
            county_fips = COUNTIES[args.county]["fips"]
            county_name = COUNTIES[args.county]["name"]

            logger.info(f"Scraping {county_name} for {args.type}")

            total = 0
            for raw_property in scraper.paginate_county(county_fips, args.type, args.pages):
                prop = scraper.extract_property(raw_property)
                if prop:
                    scraper.save_property(prop, args.county, args.type)
                    images = scraper.download_images(prop["zpid"], args.type, raw_property)
                    total += 1
                    if total % 5 == 0:
                        logger.info(f"  Processed {total} properties...")

            logger.info(f"Completed: {total} properties saved to database")
        else:
            logger.error("Please specify --county and --type, or use --full")


if __name__ == "__main__":
    main()
