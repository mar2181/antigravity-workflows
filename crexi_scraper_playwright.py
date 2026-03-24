"""
Crexi Scraper - Playwright Interception Method
Launches real browser, intercepts API responses, extracts properties
Works around Cloudflare protection by using real browser session
"""

import json
import sqlite3
import os
import time
import logging
from datetime import datetime
from pathlib import Path
import re

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    exit(1)

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
IMAGES_DIR = IMAGE_SETTINGS["storage_dir"]
API_BASE = CONFIG["api"]["base_url"]


class CrexiScraperPlaywright:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_database()
        os.makedirs(IMAGES_DIR, exist_ok=True)
        self.captured_responses = []

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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
                broker_name TEXT,
                broker_company TEXT,
                image_count INTEGER DEFAULT 0,
                images_downloaded INTEGER DEFAULT 0,
                raw_json TEXT,
                scraped_at TEXT,
                UNIQUE(region, crexi_asset_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crexi_asset_id TEXT,
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

    def _handle_api_response(self, response):
        """Capture API responses"""
        try:
            if "properties/search" in response.url:
                data = response.json()
                if "data" in data:
                    self.captured_responses.append(data)
                    logger.debug(f"Captured {len(data['data'])} properties from API")
        except Exception as e:
            logger.debug(f"Could not parse response: {e}")

    def search_properties(self, location_key, property_type, pages=1):
        """
        Search properties using Playwright headful browser with network interception
        """
        logger.info(f"Launching headful browser for {location_key} {property_type}...")
        logger.info("**IMPORTANT:** You must MANUALLY LOG INTO CREXI when browser opens")
        logger.info("Do NOT close the browser - script will intercept API calls automatically")

        place_id = REGIONS["south_texas"]["place_ids"].get(location_key)
        if not place_id:
            logger.error(f"Unknown location: {location_key}")
            return []

        with sync_playwright() as p:
            # Launch headful browser (NOT headless)
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # Listen for API responses
            def on_response(response):
                if "properties/search" in response.url:
                    try:
                        data = response.json()
                        if "data" in data:
                            self.captured_responses.append(data)
                            logger.info(f"Captured {len(data['data'])} properties")
                    except Exception as e:
                        pass

            page.on("response", on_response)

            try:
                # Navigate to Crexi search
                logger.info("Navigating to Crexi properties search...")
                page.goto("https://www.crexi.com/properties/search", timeout=60000, wait_until="domcontentloaded")

                # Give user time to log in if needed
                logger.info("Waiting for page to load and authentication check...")
                page.wait_for_timeout(3000)

                # Check if already authenticated
                try:
                    page.wait_for_selector("input[placeholder*='Search'], button[aria-label*='Search']", timeout=5000)
                    logger.info("Page loaded and appears authenticated")
                except:
                    logger.warning("Could not find search controls - you may need to log in manually in the browser")

                # Build search parameters
                property_types_list = PROPERTY_TYPES["commercial"]
                if property_type.lower() != "all":
                    property_types_list = [property_type]

                logger.info(f"Searching for: Location={location_key}, Types={property_types_list}, Pages={pages}")
                logger.info("Please wait while API requests are intercepted...")

                # Construct the search URL with parameters
                search_params = {
                    "placeIds": [place_id],
                    "propertyTypes": property_types_list,
                    "sortBy": "Relevancy",
                    "sortOrder": "Descending"
                }

                # Try to trigger search by injecting JavaScript
                logger.info("Triggering API search via JavaScript...")
                page.evaluate(f"""
                    () => {{
                        const params = {json.dumps(search_params)};
                        // Try to find and click search filters
                        const searchButton = document.querySelector('button[type="submit"], button[class*="search"]');
                        if (searchButton) {{
                            searchButton.click();
                            console.log('Clicked search button');
                        }}
                    }}
                """)

                # Wait for network activity
                logger.info("Waiting for API responses (this may take 10-30 seconds)...")
                time.sleep(10)

                # Try pagination if more pages requested
                for page_num in range(2, pages + 1):
                    logger.info(f"Attempting to navigate to page {page_num}...")
                    try:
                        page.wait_for_timeout(2000)
                        next_button = page.locator("button:has-text('Next'), a[aria-label*='next'], button[class*='next']").first
                        if next_button.is_visible():
                            next_button.click()
                            time.sleep(5)
                        else:
                            logger.info(f"No more pages available")
                            break
                    except Exception as e:
                        logger.warning(f"Could not navigate to page {page_num}: {e}")
                        break

            except Exception as e:
                logger.error(f"Error during search: {e}")

            finally:
                logger.info(f"\nCaptured {len(self.captured_responses)} API responses total")
                context.close()
                browser.close()

        return self.captured_responses

    def extract_and_save_properties(self, api_responses, region):
        """Extract properties from captured API responses and save to database"""
        saved_count = 0

        for response_data in api_responses:
            if "data" not in response_data:
                continue

            for prop in response_data["data"]:
                try:
                    asset_id = prop.get("crexiAssetId", "")
                    if not asset_id:
                        continue

                    address_obj = prop.get("address", {})
                    street = address_obj.get("streetAddress", "")
                    city = address_obj.get("city", "")
                    state = address_obj.get("state", "")
                    zip_code = address_obj.get("zipCode", "")
                    full_address = f"{street}, {city}, {state} {zip_code}".strip()

                    price = prop.get("price", 0)
                    sqft = prop.get("sqft", 0)
                    units = prop.get("units", 0)
                    price_per_sqft = (price / sqft) if sqft > 0 else 0
                    price_per_unit = (price / units) if units > 0 else 0

                    images = prop.get("crexiListingImages", [])
                    image_count = len(images)

                    broker = prop.get("broker", {})
                    broker_name = broker.get("brokerName", "")
                    broker_company = broker.get("company", {}).get("companyName", "")

                    # Save to database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT OR REPLACE INTO properties (
                            crexi_asset_id, region, property_type, address,
                            street_address, city, state, zip_code,
                            price, price_per_sqft, price_per_unit,
                            sqft, units, year_built, building_class,
                            broker_name, broker_company, image_count,
                            raw_json, scraped_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        asset_id,
                        region,
                        prop.get("crexiPropertyType", ""),
                        full_address,
                        street,
                        city,
                        state,
                        zip_code,
                        price,
                        price_per_sqft,
                        price_per_unit,
                        sqft,
                        units,
                        prop.get("yearBuilt", 0),
                        prop.get("buildingClass", ""),
                        broker_name,
                        broker_company,
                        image_count,
                        json.dumps(prop),
                        datetime.now().isoformat()
                    ))

                    # Save image URLs
                    for idx, img_url in enumerate(images[:IMAGE_SETTINGS["max_per_property"]], 1):
                        cursor.execute("""
                            INSERT INTO images (crexi_asset_id, image_index, url_original)
                            VALUES (?, ?, ?)
                        """, (asset_id, idx, img_url))

                    conn.commit()
                    conn.close()
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error processing property: {e}")

        logger.info(f"Saved {saved_count} properties to database")
        return saved_count

    def download_images(self):
        """Download images from captured data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT crexi_asset_id, image_index, url_original
            FROM images
            WHERE local_path IS NULL
            ORDER BY crexi_asset_id, image_index
        """)

        images_to_download = cursor.fetchall()
        conn.close()

        if not images_to_download:
            logger.info("No images to download")
            return

        logger.info(f"Downloading {len(images_to_download)} images...")
        downloaded = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            for asset_id, idx, url in images_to_download:
                try:
                    asset_dir = os.path.join(IMAGES_DIR, asset_id)
                    os.makedirs(asset_dir, exist_ok=True)

                    filename = f"image_{idx:02d}.jpg"
                    filepath = os.path.join(asset_dir, filename)

                    # Download image
                    response = context.request.get(url, timeout=30000)
                    if response.ok:
                        with open(filepath, "wb") as f:
                            f.write(response.body())

                        # Update database
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE images
                            SET local_path = ?, downloaded_at = ?
                            WHERE crexi_asset_id = ? AND image_index = ?
                        """, (filepath, datetime.now().isoformat(), asset_id, idx))
                        conn.commit()
                        conn.close()

                        downloaded += 1
                        if downloaded % 10 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(images_to_download)} images")

                except Exception as e:
                    logger.error(f"Failed to download image {asset_id}/{idx}: {e}")

            browser.close()

        logger.info(f"Completed: {downloaded} images downloaded")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crexi Scraper (Playwright)")
    parser.add_argument("--location", default="mcallen", help="Location key (mcallen, brownsville, rio_grande_city)")
    parser.add_argument("--type", default="Industrial", help="Property type")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--download-images", action="store_true", help="Download images after scraping")

    args = parser.parse_args()

    scraper = CrexiScraperPlaywright()

    logger.info(f"Starting Crexi scrape: {args.location} / {args.type} / {args.pages} pages")
    api_responses = scraper.search_properties(args.location, args.type, args.pages)

    if api_responses:
        saved = scraper.extract_and_save_properties(api_responses, "south_texas")
        logger.info(f"Total: {saved} properties saved")

        if args.download_images:
            scraper.download_images()
    else:
        logger.warning("No API responses captured. Browser may not have logged in properly.")
        logger.info("Try running again and make sure to log into Crexi when the browser opens.")


if __name__ == "__main__":
    main()
