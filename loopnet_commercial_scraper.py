"""
LoopNet Commercial Property Scraper
Extracts commercial listings with full data + images
More automation-friendly than Zillow
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import requests
import re

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("Playwright not installed. Run: pip install playwright")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

with open("commercial_comp_config.json", "r") as f:
    CONFIG = json.load(f)


class LoopNetCommercialScraper:
    """LoopNet commercial property scraper"""

    def __init__(self):
        self.base_url = "https://www.loopnet.com"
        self.session_dir = Path("loopnet_auth")
        self.session_dir.mkdir(exist_ok=True)
        self.properties_found = []

    async def search_commercial(self,
                               city: str = "McAllen",
                               state: str = "TX",
                               property_types: List[str] = None) -> List[Dict]:
        """
        Search LoopNet for commercial properties

        Args:
            city: City to search
            state: State code
            property_types: List of types (industrial, office, retail, land, multifamily)

        Returns:
            List of property dictionaries
        """

        if property_types is None:
            property_types = ["industrial", "office", "retail", "land"]

        logger.info("\n" + "="*70)
        logger.info("LOOPNET COMMERCIAL PROPERTY SEARCH")
        logger.info("="*70)
        logger.info(f"Location: {city}, {state}")
        logger.info(f"Property Types: {', '.join(property_types)}")
        logger.info("="*70 + "\n")

        properties = []

        try:
            async with async_playwright() as p:
                logger.info("Launching browser...")

                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_dir),
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox"
                    ]
                )

                page = await browser.new_page()
                logger.info("✓ Browser launched\n")

                # Build search URL
                search_url = self._build_search_url(city, state, property_types)
                logger.info(f"Navigating to: {search_url}")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=120000)
                    logger.info("✓ LoopNet search page loaded")
                except Exception as e:
                    logger.warning(f"Load warning: {e}")

                # Wait for results to render
                logger.info("Waiting for search results...")
                await asyncio.sleep(3)

                # Extract properties
                properties = await self._extract_properties(page)

                logger.info(f"✓ Found {len(properties)} commercial properties\n")

                # Download images
                if properties:
                    logger.info("Downloading property images...")
                    for idx, prop in enumerate(properties, 1):
                        logger.info(f"[{idx}/{len(properties)}] {prop.get('address')}")
                        images = await self._download_images(prop)
                        prop['local_images'] = images
                        prop['image_count'] = len(images)

                await browser.close()

                self.properties_found = properties
                return properties

        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _build_search_url(self, city: str, state: str, property_types: List[str]) -> str:
        """Build LoopNet search URL"""
        # LoopNet search format
        location = f"{city},%20{state}"

        # Property type parameters
        type_params = "&".join([f"propertyType={pt}" for pt in property_types])

        return f"https://www.loopnet.com/Search/Commercial/ForSale/{location}/?{type_params}"

    async def _extract_properties(self, page: Page) -> List[Dict]:
        """Extract property data from LoopNet search results"""

        properties = []

        try:
            logger.info("Looking for property listings...")

            # Wait for listing containers
            try:
                await page.wait_for_selector("div[data-testid='listing-item']", timeout=15000)
            except:
                logger.warning("Standard selector not found, trying alternatives...")

            # Try multiple selector patterns for LoopNet
            selectors = [
                "div[data-testid='listing-item']",
                "div.search-result-card",
                "div.ListingCard",
                "article.listing-item",
                "div[class*='listing']"
            ]

            listing_elements = []
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"✓ Found {len(elements)} listings with selector: {selector}")
                        listing_elements = elements
                        break
                except:
                    continue

            logger.info(f"Extracting data from {len(listing_elements)} listings...")

            for idx, listing in enumerate(listing_elements[:50]):  # Max 50 properties
                try:
                    # Extract address
                    address = None
                    address_selectors = [
                        "h2 a",
                        "div[data-testid='title']",
                        ".listing-address",
                        "span[class*='address']"
                    ]

                    for addr_sel in address_selectors:
                        addr_elem = await listing.query_selector(addr_sel)
                        if addr_elem:
                            address = await addr_elem.inner_text()
                            if address:
                                break

                    if not address:
                        continue

                    # Extract price
                    price = None
                    price_text = None
                    price_selectors = [
                        "div[data-testid='price']",
                        ".price",
                        "span[class*='price']",
                        "div[class*='Price']"
                    ]

                    for price_sel in price_selectors:
                        price_elem = await listing.query_selector(price_sel)
                        if price_elem:
                            price_text = await price_elem.inner_text()
                            if price_text:
                                price = self._parse_price(price_text)
                                if price:
                                    break

                    # Extract property type
                    property_type = None
                    type_selectors = [
                        "span[class*='type']",
                        "div[data-testid='propertyType']"
                    ]

                    for type_sel in type_selectors:
                        type_elem = await listing.query_selector(type_sel)
                        if type_elem:
                            property_type = await type_elem.inner_text()
                            if property_type:
                                break

                    # Extract sqft
                    sqft = None
                    sqft_text = None
                    text_content = await listing.inner_text()

                    sqft_match = re.search(r'(\d+(?:,\d+)?)\s*(?:Sq\.?\s*Ft|sqft|sf)', text_content, re.IGNORECASE)
                    if sqft_match:
                        sqft = int(sqft_match.group(1).replace(',', ''))

                    # Extract URL
                    link_elem = await listing.query_selector("a[href*='/Property/']")
                    url = None
                    if link_elem:
                        url = await link_elem.get_attribute("href")
                        if url and not url.startswith("http"):
                            url = self.base_url + url

                    # Extract images
                    images = await self._extract_images_from_listing(listing)

                    # Build property record
                    property_data = {
                        'loopnet_id': url.split('/')[-1] if url else address.replace(" ", "_"),
                        'address': address.strip(),
                        'city': 'McAllen',
                        'state': 'TX',
                        'price': price,
                        'price_text': price_text,
                        'property_type': property_type or 'commercial',
                        'sqft': sqft,
                        'images': images,
                        'source_url': url,
                        'data_source': 'LoopNet',
                        'raw_listing_text': text_content[:500]
                    }

                    if address and (price or property_type):
                        properties.append(property_data)
                        logger.debug(f"  ✓ {address} - ${price:,.0f}" if price else f"  ✓ {address}")

                except Exception as e:
                    logger.debug(f"Error extracting property: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error during extraction: {e}")

        return properties

    async def _extract_images_from_listing(self, listing_element) -> List[str]:
        """Extract image URLs from a listing element"""

        images = []

        try:
            # Try to find images in the listing
            img_selectors = [
                "img[alt*='Property']",
                "img[class*='image']",
                "img[src*='property']",
                "img"
            ]

            for img_sel in img_selectors:
                img_elements = await listing_element.query_selector_all(img_sel)

                for img in img_elements:
                    src = await img.get_attribute("src")
                    if src and ("property" in src.lower() or "image" in src.lower()):
                        # Handle lazy-loaded images
                        if not src.startswith("http"):
                            src = self.base_url + src

                        if src not in images:
                            images.append(src)

                        if len(images) >= 10:  # Max 10 images
                            break

                if images:
                    break

        except Exception as e:
            logger.debug(f"Error extracting images: {e}")

        return images

    async def _download_images(self, property_data: Dict, max_images: int = 6) -> List[str]:
        """Download images for a property"""

        local_images = []
        images = property_data.get('images', [])

        if not images:
            return local_images

        loopnet_id = property_data.get('loopnet_id')
        images_dir = Path(CONFIG['images']['storage_dir'])
        prop_dir = images_dir / loopnet_id
        prop_dir.mkdir(parents=True, exist_ok=True)

        for idx, image_url in enumerate(images[:max_images], 1):
            try:
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
                local_path = prop_dir / f'image_{idx:02d}.{ext}'
                local_path.write_bytes(response.content)
                local_images.append(str(local_path))

                logger.info(f"  ✓ Image {idx}: {local_path.name}")
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.debug(f"  Image {idx} failed: {e}")

        return local_images

    @staticmethod
    def _parse_price(price_text: str) -> Optional[int]:
        """Parse price from text"""
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
    """Run LoopNet commercial search"""

    scraper = LoopNetCommercialScraper()

    properties = await scraper.search_commercial(
        city="McAllen",
        state="TX",
        property_types=["industrial", "office", "retail", "land"]
    )

    if not properties:
        logger.warning("No properties found.")
        return

    # Save results
    results_file = "loopnet_commercial_search_results.json"
    with open(results_file, "w") as f:
        json.dump(properties, f, indent=2, default=str)

    logger.info(f"\n✓ Results saved to: {results_file}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("LOOPNET SEARCH RESULTS")
    logger.info("="*70)
    logger.info(f"Total properties: {len(properties)}")

    total_images = sum(len(p.get('local_images', [])) for p in properties)
    logger.info(f"Total images downloaded: {total_images}")

    logger.info("\nProperties found:")
    for prop in properties[:5]:  # Show first 5
        logger.info(f"  {prop.get('address')}")
        if prop.get('price'):
            logger.info(f"    Price: ${prop.get('price'):,.0f}")
        logger.info(f"    Images: {len(prop.get('local_images', []))}")

    logger.info("="*70 + "\n")

    logger.info("Next: Run loopnet_to_commercial_db.py to integrate into database")


if __name__ == "__main__":
    asyncio.run(main())
