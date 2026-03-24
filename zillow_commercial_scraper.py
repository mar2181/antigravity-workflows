"""
Zillow Commercial Property Scraper
Full implementation with API authentication, image downloading, and data extraction
Subject: 1204 Upas Avenue, McAllen, TX (Commercial)
"""

import json
import logging
import asyncio
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re
from urllib.parse import urljoin, quote

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    print("Then: playwright install")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load config
with open("commercial_comp_config.json", "r") as f:
    CONFIG = json.load(f)


class ZillowAuthenticator:
    """Handles Zillow authentication and cookie management"""

    def __init__(self):
        self.cookies_file = "zillow_cookies.json"
        self.auth_cookies = {}
        self.session = requests.Session()

    def has_valid_cookies(self) -> bool:
        """Check if we have saved cookies"""
        if not Path(self.cookies_file).exists():
            return False

        try:
            with open(self.cookies_file, "r") as f:
                self.auth_cookies = json.load(f)
                required_cookies = ['zjs_user_id', 'zjs_anonymous_id', 'zguid', 'zgsession']
                return all(c in self.auth_cookies for c in required_cookies)
        except:
            return False

    def load_cookies(self) -> bool:
        """Load saved authentication cookies"""
        try:
            with open(self.cookies_file, "r") as f:
                self.auth_cookies = json.load(f)
                logger.info("✓ Loaded Zillow authentication cookies")
                return True
        except Exception as e:
            logger.warning(f"Could not load cookies: {e}")
            return False

    def save_cookies(self, cookies: Dict):
        """Save authentication cookies for future use"""
        try:
            self.auth_cookies = cookies
            with open(self.cookies_file, "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"✓ Saved {len(cookies)} cookies to {self.cookies_file}")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")

    async def interactive_login(self) -> bool:
        """Open Zillow in browser and let user log in manually"""
        logger.info("\n" + "="*70)
        logger.info("ZILLOW AUTHENTICATION REQUIRED")
        logger.info("="*70)
        logger.info("Opening Zillow in browser...")
        logger.info("Please log in to your Zillow account in the browser.")
        logger.info("Press ENTER in this terminal when you've logged in and confirmed access.")
        logger.info("="*70 + "\n")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()

                # Navigate to Zillow
                await page.goto("https://www.zillow.com", wait_until="networkidle", timeout=60000)
                logger.info("✓ Zillow loaded in browser")

                # Wait for user to log in
                input("Press ENTER after you've logged in successfully...")

                # Extract cookies
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}

                # Save cookies
                self.save_cookies(cookie_dict)

                await browser.close()
                return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def get_session_headers(self) -> Dict:
        """Get headers for API requests with authentication"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.zillow.com',
            'X-Requested-With': 'XMLHttpRequest'
        }


class ZillowCommercialPropertyExtractor:
    """Extracts commercial property data from Zillow JSON responses"""

    @staticmethod
    def extract_properties(response_json: Dict) -> List[Dict]:
        """Extract property data from Zillow API response"""
        properties = []

        try:
            # Zillow's search results are typically in a specific structure
            # This needs to be adjusted based on actual API response format

            results = response_json.get('searchPageState', {}).get('listData', {}).get('mapResults', [])

            if not results:
                results = response_json.get('searchResults', [])

            for item in results:
                try:
                    prop = {
                        'zpid': item.get('zpid') or item.get('id'),
                        'address': item.get('address'),
                        'city': item.get('city'),
                        'state': item.get('state'),
                        'zip_code': item.get('zipcode'),
                        'price': item.get('price'),
                        'price_per_sqft': item.get('pricePerSqft'),
                        'sqft': item.get('living_area') or item.get('sqft'),
                        'year_built': item.get('yearBuilt'),
                        'property_type': item.get('propertyType') or 'commercial',
                        'latitude': item.get('latitude'),
                        'longitude': item.get('longitude'),
                        'images': item.get('images', []),
                        'source_url': f"https://www.zillow.com/property/{item.get('zpid')}",
                        'source_id': item.get('zpid'),
                        'data_source': 'Zillow'
                    }

                    if prop['address'] and prop['price']:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Error extracting property: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing response: {e}")

        return properties

    @staticmethod
    def extract_images(images_data: List) -> List[str]:
        """Extract image URLs from property data"""
        image_urls = []

        try:
            for image in images_data[:10]:  # Max 10 images per property
                if isinstance(image, dict):
                    # Try multiple possible URL fields
                    url = image.get('url') or image.get('highResLink') or image.get('mixedSources', {}).get('photo')
                    if url:
                        # Ensure we use the highest quality suffix (_e = extra large)
                        if '_' not in url.split('.')[-2]:
                            url = url.replace('.jpg', '_e.jpg').replace('.png', '_e.png')
                        image_urls.append(url)
                elif isinstance(image, str):
                    image_urls.append(image)

        except Exception as e:
            logger.debug(f"Error extracting images: {e}")

        return image_urls


class ZillowCommercialScraper:
    """Complete Zillow commercial property scraper"""

    def __init__(self):
        self.auth = ZillowAuthenticator()
        self.extractor = ZillowCommercialPropertyExtractor()
        self.base_url = "https://www.zillow.com"
        self.api_endpoint = "https://www.zillow.com/async-create-search-page-state"
        self.properties_found = []

    async def search_commercial(self,
                               city: str = "McAllen",
                               state: str = "TX",
                               county_fips: str = "48215") -> List[Dict]:
        """
        Search Zillow for commercial properties

        Args:
            city: City to search
            state: State
            county_fips: County FIPS code (48215 = Hidalgo)

        Returns:
            List of property dictionaries
        """

        logger.info("\n" + "="*70)
        logger.info("ZILLOW COMMERCIAL PROPERTY SEARCH")
        logger.info("="*70)
        logger.info(f"City: {city}, {state}")
        logger.info(f"County FIPS: {county_fips} (Hidalgo County)")
        logger.info(f"Property Type: Commercial, Industrial, Office, Retail")
        logger.info("="*70 + "\n")

        # Check authentication
        if not self.auth.has_valid_cookies():
            logger.info("No valid authentication cookies found.")
            logger.info("Initiating interactive login...")

            if not await self.auth.interactive_login():
                logger.error("Authentication failed. Cannot proceed.")
                return []

        self.auth.load_cookies()

        try:
            # Build search payload
            payload = self._build_search_payload(city, state, county_fips)

            logger.info("Sending search request to Zillow API...")
            logger.info(f"Endpoint: {self.api_endpoint}")

            # Make API request with cookies
            headers = self.auth.get_session_headers()
            cookies = self.auth.auth_cookies

            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                cookies=cookies,
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"✓ Response received (Status: {response.status_code})")

            # Parse response
            response_data = response.json()

            # Extract properties
            properties = self.extractor.extract_properties(response_data)

            logger.info(f"✓ Extracted {len(properties)} commercial properties")

            # Enrich with images
            for prop in properties:
                prop['images'] = self.extractor.extract_images(prop.get('images', []))

            self.properties_found = properties
            return properties

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            logger.info("\nTroubleshooting:")
            logger.info("- Check if cookies are still valid (may have expired)")
            logger.info("- Try logging in again")
            logger.info("- Check Zillow hasn't changed their API endpoint")
            return []

        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _build_search_payload(self, city: str, state: str, county_fips: str) -> Dict:
        """Build the API payload for commercial property search"""

        # This is the structure for Zillow's async search endpoint
        # Adjust based on actual API requirements
        return {
            "searchPageState": {
                "regionSelection": [
                    {
                        "regionId": int(county_fips),  # County FIPS code
                        "regionType": 2  # 2 = County
                    }
                ],
                "filterState": {
                    "price": {
                        "min": 0,
                        "max": 10000000  # Up to $10M
                    },
                    "propertyType": {
                        "commercial": True,
                        "commercialSaleListings": True
                    },
                    "sort": {
                        "value": "globalrelevanceex"
                    },
                    "isAllHomes": False,
                    "isSingleFamily": False,
                    "isMultiFamily": False,
                    "isCommercial": True,
                    "isManufactured": False,
                    "isApartment": False,
                    "isCondoCoop": False,
                    "isLotLand": False,
                    "isTownhouse": False,
                    "isForSaleByAgent": False,
                    "isForSaleByOwner": False,
                    "isNewHome": False,
                    "isComingSoon": False,
                    "isAuction": False,
                    "isForRent": False
                },
                "isMap": False,
                "pagination": {
                    "currentPage": 1
                }
            }
        }

    async def download_property_images(self, properties: List[Dict], max_images_per_property: int = 6) -> List[Dict]:
        """Download images for all properties"""

        logger.info(f"\nDownloading images for {len(properties)} properties...")

        images_dir = Path(CONFIG['images']['storage_dir'])
        images_dir.mkdir(exist_ok=True)

        for idx, prop in enumerate(properties, 1):
            zpid = prop.get('zpid')
            images = prop.get('images', [])

            logger.info(f"\n[{idx}/{len(properties)}] {prop.get('address')}")

            if not images:
                logger.warning(f"  No images available")
                continue

            prop_dir = images_dir / zpid
            prop_dir.mkdir(exist_ok=True)

            downloaded = 0
            for img_idx, image_url in enumerate(images[:max_images_per_property], 1):
                try:
                    # Download image
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(image_url, headers=headers, timeout=10)
                    response.raise_for_status()

                    # Determine file extension
                    ext = 'jpg'
                    if 'content-type' in response.headers:
                        ct = response.headers['content-type'].lower()
                        if 'png' in ct:
                            ext = 'png'
                        elif 'webp' in ct:
                            ext = 'webp'

                    # Save image
                    local_path = prop_dir / f'image_{img_idx:02d}.{ext}'
                    local_path.write_bytes(response.content)

                    # Update property with local path
                    if 'local_images' not in prop:
                        prop['local_images'] = []
                    prop['local_images'].append(str(local_path))

                    downloaded += 1
                    logger.info(f"  ✓ Image {img_idx}: {local_path.name} ({len(response.content) / 1024:.1f} KB)")

                    # Rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"  ✗ Image {img_idx} failed: {e}")

            logger.info(f"  ✓ Downloaded {downloaded}/{len(images[:max_images_per_property])} images")

        return properties


async def main():
    """Run Zillow commercial property scraper"""

    scraper = ZillowCommercialScraper()

    # Search for commercial properties
    properties = await scraper.search_commercial(
        city="McAllen",
        state="TX",
        county_fips="48215"
    )

    if not properties:
        logger.error("\nNo properties found. Check authentication or API status.")
        return

    # Download images
    logger.info(f"\n{'='*70}")
    logger.info(f"DOWNLOADING IMAGES")
    logger.info(f"{'='*70}")

    properties_with_images = await scraper.download_property_images(properties)

    # Save results to JSON
    results_file = "zillow_commercial_search_results.json"
    with open(results_file, "w") as f:
        json.dump(properties_with_images, f, indent=2, default=str)

    logger.info(f"\n✓ Results saved to: {results_file}")

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SEARCH SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total properties found: {len(properties_with_images)}")
    total_images = sum(len(p.get('local_images', [])) for p in properties_with_images)
    logger.info(f"Total images downloaded: {total_images}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
