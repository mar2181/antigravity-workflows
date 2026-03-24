"""
Zillow Commercial Property Scraper - Browser Automation Version
Uses Playwright to bypass API blocking and extract data from search results
More reliable than API approach
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import re
import requests

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


class ZillowBrowserScraper:
    """Zillow commercial scraper using Playwright browser automation"""

    def __init__(self):
        self.base_url = "https://www.zillow.com"
        self.session_dir = Path("zillow_auth")
        self.session_dir.mkdir(exist_ok=True)
        self.properties_found = []

    async def search_commercial(self,
                               city: str = "McAllen",
                               state: str = "TX",
                               search_radius: float = 2.0) -> List[Dict]:
        """
        Search Zillow for commercial properties using browser automation

        Args:
            city: City to search
            state: State code
            search_radius: Search radius in miles

        Returns:
            List of property dictionaries with images
        """

        logger.info("\n" + "="*70)
        logger.info("ZILLOW COMMERCIAL PROPERTY SEARCH (Browser Automation)")
        logger.info("="*70)
        logger.info(f"City: {city}, {state}")
        logger.info(f"Radius: {search_radius} miles")
        logger.info(f"Property Types: Commercial, Industrial, Office, Retail")
        logger.info("="*70 + "\n")

        properties = []

        try:
            async with async_playwright() as p:
                logger.info("Launching Chrome browser...")

                # Launch with persistent context for faster subsequent runs
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_dir),
                    headless=False,  # Visible browser for anti-bot bypass
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox"
                    ]
                )

                page = await browser.new_page()

                logger.info("✓ Browser launched")

                # Navigate to Zillow
                search_url = self._build_search_url(city, state)
                logger.info(f"Navigating to: {search_url}")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=120000)
                    logger.info("✓ Zillow search page loaded")
                except Exception as e:
                    logger.warning(f"Page load warning: {e}")

                # Wait for commercial property listings to load
                logger.info("Waiting for search results to render...")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                except:
                    logger.warning("DomContentLoaded timeout - proceeding anyway")

                # Extra wait for JavaScript rendering
                await asyncio.sleep(3)

                # Extract properties from the loaded page
                properties = await self._extract_properties_from_page(page)

                logger.info(f"✓ Found {len(properties)} properties on current page")

                # Download images for each property
                logger.info(f"\nDownloading images for {len(properties)} properties...")
                for idx, prop in enumerate(properties, 1):
                    logger.info(f"[{idx}/{len(properties)}] {prop.get('address')}")
                    images = await self._download_property_images(prop)
                    prop['local_images'] = images
                    prop['images_count'] = len(images)

                await browser.close()

                self.properties_found = properties
                return properties

        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _build_search_url(self, city: str, state: str) -> str:
        """Build Zillow search URL for commercial properties"""
        # Zillow commercial search URL format
        query = f"{city}, {state}"
        return f"https://www.zillow.com/commercial/search/?q={query}&type=commercial"

    async def _extract_properties_from_page(self, page: Page) -> List[Dict]:
        """Extract property data from Zillow search page"""

        properties = []

        try:
            # Wait for listing containers to load
            await page.wait_for_selector("div[data-testid='property-card']", timeout=15000)

            # Get all property cards
            cards = await page.query_selector_all("div[data-testid='property-card']")
            logger.info(f"Found {len(cards)} property cards")

            for idx, card in enumerate(cards):
                try:
                    # Extract address
                    address_elem = await card.query_selector("h2[data-testid='property-address']")
                    address = await address_elem.inner_text() if address_elem else None

                    if not address:
                        continue

                    # Extract price
                    price_elem = await card.query_selector("span[data-testid='property-price']")
                    price_text = await price_elem.inner_text() if price_elem else None
                    price = self._parse_price(price_text)

                    # Extract property URL
                    link_elem = await card.query_selector("a[data-testid='property-link']")
                    prop_url = await link_elem.get_attribute("href") if link_elem else None

                    # Extract zpid from URL if available
                    zpid = None
                    if prop_url:
                        match = re.search(r'/(\d+)_zpid', prop_url)
                        if match:
                            zpid = match.group(1)
                        else:
                            zpid = address.replace(" ", "_")

                    # Extract images
                    images = []
                    image_elems = await card.query_selector_all("img[data-testid='property-image']")
                    for img in image_elems:
                        src = await img.get_attribute("src")
                        if src:
                            images.append(src)

                    property_data = {
                        'zpid': zpid,
                        'address': address,
                        'city': 'McAllen',  # Default, extract if possible
                        'state': 'TX',
                        'zip_code': None,
                        'price': price,
                        'property_type': 'commercial',
                        'images': images,
                        'source_url': prop_url,
                        'source_id': zpid,
                        'data_source': 'Zillow'
                    }

                    if address and price:
                        properties.append(property_data)
                        logger.debug(f"  Extracted: {address} - ${price:,.0f}")

                except Exception as e:
                    logger.debug(f"Error extracting property: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error extracting properties from page: {e}")

        return properties

    async def _download_property_images(self, property_data: Dict, max_images: int = 6) -> List[str]:
        """Download images for a single property"""

        images = property_data.get('images', [])
        local_images = []

        if not images:
            logger.warning(f"  No images available")
            return local_images

        zpid = property_data.get('zpid')
        images_dir = Path(CONFIG['images']['storage_dir'])
        prop_dir = images_dir / zpid
        prop_dir.mkdir(parents=True, exist_ok=True)

        for idx, image_url in enumerate(images[:max_images], 1):
            try:
                # Download image
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(image_url, headers=headers, timeout=10)
                response.raise_for_status()

                # Determine extension
                ext = 'jpg'
                if 'content-type' in response.headers:
                    ct = response.headers['content-type'].lower()
                    if 'png' in ct:
                        ext = 'png'
                    elif 'webp' in ct:
                        ext = 'webp'

                # Save
                local_path = prop_dir / f'image_{idx:02d}.{ext}'
                local_path.write_bytes(response.content)
                local_images.append(str(local_path))

                logger.info(f"  ✓ Image {idx}: {local_path.name}")

                await asyncio.sleep(0.3)

            except Exception as e:
                logger.warning(f"  ✗ Image {idx} failed: {e}")

        return local_images

    def _capture_response(self, response):
        """Capture API responses for data extraction (optional)"""
        try:
            if "async-create-search-page-state" in response.url:
                # This is the main search response - could be used for additional data
                pass
        except:
            pass

    @staticmethod
    def _parse_price(price_text: str) -> Optional[int]:
        """Parse price from text (e.g., '$1,234,567' -> 1234567)"""
        if not price_text:
            return None

        try:
            # Extract numbers
            numbers = re.sub(r'[^\d]', '', price_text)
            if numbers:
                return int(numbers)
        except:
            pass

        return None


async def main():
    """Run Zillow commercial search"""

    scraper = ZillowBrowserScraper()

    properties = await scraper.search_commercial(
        city="McAllen",
        state="TX",
        search_radius=2.0
    )

    if not properties:
        logger.warning("No properties found.")
        return

    # Save results
    results_file = "zillow_commercial_search_results.json"
    with open(results_file, "w") as f:
        json.dump(properties, f, indent=2, default=str)

    logger.info(f"\n✓ Results saved to: {results_file}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SEARCH RESULTS")
    logger.info("="*70)
    logger.info(f"Total properties: {len(properties)}")

    total_images = sum(len(p.get('local_images', [])) for p in properties)
    logger.info(f"Total images downloaded: {total_images}")

    for prop in properties[:3]:  # Show first 3
        logger.info(f"\n  {prop.get('address')}")
        logger.info(f"    Price: ${prop.get('price'):,.0f}")
        logger.info(f"    Images: {len(prop.get('local_images', []))}")

    logger.info("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
