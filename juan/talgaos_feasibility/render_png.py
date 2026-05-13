"""Render dashboard.html to PNG via Playwright. Outputs dashboard.png in same folder."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).parent

async def main():
    html = HERE / "dashboard.html"
    out = HERE / "dashboard.png"
    if not html.exists():
        raise SystemExit(f"missing {html}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 1600}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(html.as_uri())
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.screenshot(path=str(out), full_page=True)
        await browser.close()
    print(f"Wrote {out}")

if __name__ == "__main__":
    asyncio.run(main())
