"""
Crexi Commercial Property Scraper
Extracts commercial properties (Industrial, Retail, Office, Multifamily) from Crexi API
Stores in SQLite with local image downloads
Primary source for commercial comparables in South Texas
"""

import json
import sqlite3
import requests
import os
import time
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
with open("crexi_config.json", "r") as f:
    CONFIG = json.load(f)

REGIONS = CONFIG["regions"]
PROPERTY_TYPES = CONFIG["property_types"]
SEARCH_SETTINGS = CONFIG["search_settings"]
IMAGE_SETTINGS = CONFIG["images"]
DB_PATH = CONFIG["database"]
COOKIES_FILE = CONFIG["cookies_file"]
USER_AGENT = CONFIG["user_agent"]
IMAGES_DIR = IMAGE_SETTINGS["storage_dir"]
API_BASE = CONFIG["api"]["base_url"]


class CrexiScraper:
    def __init__(self):
        self.db_path = DB_PATH
        self.cookies = self._load_cookies()
        self.session = self._create_session()
        self._init_database()
        os.makedirs(IMAGES_DIR, exist_ok=True)

    def _load_cookies(self):
        """Load Crexi cookies from JSON file"""
        if not os.path.exists(COOKIES_FILE):
            raise FileNotFoundError(
                f"Cookies file not found: {COOKIES_FILE}\n"
                "You need Crexi authentication cookies.\n"
                "Log into Crexi.com manually and export cookies."
            )

        with open(COOKIES_FILE, "r") as f:
            cookies_dict = json.load(f)

        logger.info(f"Loaded {len(cookies_dict)} cookies from {COOKIES_FILE}")
        return cookies_dict

    def _create_session(self):
        """Create authenticated requests session"""
        session = requests.Session()

        # Add cookies
        for name, value in self.cookies.items():
            session.cookies.set(name, value)

        # Add headers
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": "https://www.crexi.com/"
        })

        return session

    def _init_database(self):
        """Initialize SQLite database for commercial properties"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create properties table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                crexi_asset_id TEXT PRIMARY KEY,
                region TEXT NOT NULL,
                property_type TEXT NOT NULL,
                address TEXT NOT NULL,
                street_address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                price INTEGER,
                price_per_sqft REAL,
                price_per_unit REAL,
                sqft INTEGER,
                units INTEGER,
                lot_size_sqft INTEGER,
                year_built INTEGER,
                building_class TEXT,
                status TEXT,
                listing_url TEXT,
                latitude REAL,
                longitude REAL,
                image_count INTEGER,
                images_downloaded INTEGER DEFAULT 0,
                broker_name TEXT,
                broker_company TEXT,
                description TEXT,
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
                crexi_asset_id TEXT NOT NULL,
                image_index INTEGER,
                url_original TEXT,
                local_path TEXT,
                width INTEGER,
                height INTEGER,
                downloaded_at TEXT,
                FOREIGN KEY (crexi_asset_id) REFERENCES properties(crexi_asset_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def search_properties(self, place_id, property_type, page=1):
        """
        Execute search on Crexi API for properties
        Returns raw JSON response
        """
        url = f"{API_BASE}{CONFIG['api']['search_endpoint']}"

        payload = {
            "query": "",
            "filters": {
                "placeIds": [place_id],
                "propertyTypes": [property_type]
            },
            "pageSize": SEARCH_SETTINGS["page_size"],
            "pageNumber": page,
            "sortBy": SEARCH_SETTINGS["sort_by"],
            "sortOrder": SEARCH_SETTINGS["sort_order"]
        }

        try:
            logger.info(f"Searching Crexi for {property_type} in place_id={place_id[:20]}... (Page {page})")
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            time.sleep(SEARCH_SETTINGS["request_delay_seconds"])
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None

    def paginate_properties(self, place_id, property_type, max_pages=None):
        """
        Paginate through all properties for a location/type
        Yields raw property data from each page
        """
        page = 1
        properties_found = 0

        while True:
            if max_pages and page > max_pages:
                break

            data = self.search_properties(place_id, property_type, page)

            if not data or "data" not in data:
                logger.warning(f"No data on page {page}")
                break

            properties = data.get("data", [])

            if not properties:
                logger.info(f"No more properties on page {page}")
                break

            for prop in properties:
                yield prop
                properties_found += 1

            total = data.get("totalCount", 0)
            logger.info(f"Page {page}: {len(properties)} properties (Total: {total})")

            if properties_found >= total and total > 0:
                break

            page += 1

        logger.info(f"Paginated {properties_found} properties")

    def extract_property(self, raw_data):
        """
        Parse a property from raw Crexi JSON
        """
        try:
            address_obj = raw_data.get("address", {})

            prop = {
                "crexi_asset_id": str(raw_data.get("crexiAssetId", "")),
                "address": f"{address_obj.get('streetAddress', '')}, {address_obj.get('city', '')}, {address_obj.get('state', '')}",
                "street_address": address_obj.get("streetAddress", ""),
                "city": address_obj.get("city", ""),
                "state": address_obj.get("state", ""),
                "zip_code": address_obj.get("zipCode", ""),
                "price": int(raw_data.get("price", 0)) if raw_data.get("price") else None,
                "sqft": raw_data.get("squareFeet") or raw_data.get("sqft"),
                "units": raw_data.get("units"),
                "lot_size_sqft": raw_data.get("lotSizeSquareFeet"),
                "year_built": raw_data.get("yearBuilt"),
                "building_class": raw_data.get("buildingClass"),
                "status": raw_data.get("status", ""),
                "listing_url": f"https://www.crexi.com/properties/{raw_data.get('crexiAssetId')}",
                "latitude": raw_data.get("latitude"),
                "longitude": raw_data.get("longitude"),
                "image_urls": raw_data.get("crexiListingImages", []),
                "image_count": len(raw_data.get("crexiListingImages", [])),
                "broker_name": raw_data.get("brokerName", ""),
                "broker_company": raw_data.get("brokerCompany", ""),
                "description": raw_data.get("description", ""),
                "raw_json": json.dumps(raw_data)
            }

            # Calculate price metrics
            if prop["price"] and prop["sqft"]:
                prop["price_per_sqft"] = prop["price"] / prop["sqft"]

            if prop["price"] and prop["units"] and prop["units"] > 0:
                prop["price_per_unit"] = prop["price"] / prop["units"]

            return prop

        except Exception as e:
            logger.error(f"Error extracting property: {e}")
            return None

    def save_property(self, prop, region, property_type):
        """Save property to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO properties (
                    crexi_asset_id, region, property_type, address, street_address,
                    city, state, zip_code, price, price_per_sqft, price_per_unit,
                    sqft, units, lot_size_sqft, year_built, building_class, status,
                    listing_url, latitude, longitude, image_count,
                    broker_name, broker_company, description, raw_json, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prop["crexi_asset_id"], region, property_type, prop["address"],
                prop["street_address"], prop["city"], prop["state"], prop["zip_code"],
                prop["price"], prop.get("price_per_sqft"), prop.get("price_per_unit"),
                prop["sqft"], prop["units"], prop["lot_size_sqft"],
                prop["year_built"], prop["building_class"], prop["status"],
                prop["listing_url"], prop["latitude"], prop["longitude"],
                prop["image_count"], prop["broker_name"], prop["broker_company"],
                prop["description"], prop["raw_json"], datetime.now().isoformat()
            ))

            conn.commit()

        except sqlite3.IntegrityError:
            logger.debug(f"Property {prop['crexi_asset_id']} already exists")
        finally:
            conn.close()

    def download_images(self, crexi_asset_id, image_urls):
        """Download property images locally"""
        if not image_urls:
            return 0

        # Create property directory
        prop_dir = os.path.join(IMAGES_DIR, crexi_asset_id)
        os.makedirs(prop_dir, exist_ok=True)

        downloaded = 0
        max_images = IMAGE_SETTINGS["max_per_property"]

        for idx, url in enumerate(image_urls[:max_images]):
            if downloaded >= max_images:
                break

            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()

                # Save image
                filename = f"image_{idx + 1:02d}.jpg"
                filepath = os.path.join(prop_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(response.content)

                logger.debug(f"Downloaded {filename} for {crexi_asset_id}")
                downloaded += 1

            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to download image {idx} for {crexi_asset_id}: {e}")

            time.sleep(0.5)

        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE properties SET images_downloaded = ? WHERE crexi_asset_id = ?",
            (downloaded, crexi_asset_id)
        )
        conn.commit()
        conn.close()

        return downloaded

    def run_all(self):
        """Full scraping pipeline for all regions and property types"""
        logger.info("=" * 70)
        logger.info("CREXI SOUTH TEXAS SCRAPER - FULL RUN".center(70))
        logger.info("=" * 70)

        total_properties = 0
        total_images = 0

        # Get place IDs for our regions
        region = REGIONS["south_texas"]
        place_ids = region["place_ids"]

        for location_name, place_id in place_ids.items():
            for prop_type in PROPERTY_TYPES["commercial"]:
                logger.info(f"\n[START] {location_name.upper()} - {prop_type}")

                try:
                    for raw_property in self.paginate_properties(place_id, prop_type):
                        # Extract and save
                        prop = self.extract_property(raw_property)
                        if prop:
                            self.save_property(prop, location_name, prop_type)

                            # Download images
                            images = self.download_images(
                                prop["crexi_asset_id"],
                                prop["image_urls"]
                            )

                            if images >= IMAGE_SETTINGS["min_per_property"]:
                                total_images += images

                            total_properties += 1

                            if total_properties % 10 == 0:
                                logger.info(f"  Processed {total_properties} properties...")

                except Exception as e:
                    logger.error(f"Error processing {location_name}/{prop_type}: {e}")

        logger.info("\n" + "=" * 70)
        logger.info(f"SCRAPING COMPLETE")
        logger.info(f"Total properties: {total_properties}")
        logger.info(f"Total images downloaded: {total_images}")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Images directory: {IMAGES_DIR}")
        logger.info("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crexi Commercial Property Scraper")
    parser.add_argument("--location", choices=["mcallen", "brownsville", "rio_grande_city", "all"],
                        help="Scrape specific location")
    parser.add_argument("--type", choices=["Industrial", "Retail", "Office", "Multifamily"],
                        help="Scrape specific property type")
    parser.add_argument("--pages", type=int, default=None,
                        help="Max pages to scrape")
    parser.add_argument("--full", action="store_true",
                        help="Run full scrape (all locations, all types)")

    args = parser.parse_args()

    scraper = CrexiScraper()

    if args.full:
        scraper.run_all()
    else:
        if args.location and args.type:
            place_id = REGIONS["south_texas"]["place_ids"].get(args.location)
            if not place_id:
                logger.error(f"Unknown location: {args.location}")
                return

            total = 0
            for raw_property in scraper.paginate_properties(place_id, args.type, args.pages):
                prop = scraper.extract_property(raw_property)
                if prop:
                    scraper.save_property(prop, args.location, args.type)
                    images = scraper.download_images(prop["crexi_asset_id"], prop["image_urls"])
                    total += 1
                    if total % 5 == 0:
                        logger.info(f"  Processed {total} properties...")

            logger.info(f"Completed: {total} properties saved")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
