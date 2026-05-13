"""
GSC Live Audit for customdesignstx.com — 2026-05-04
Pulls: Search Analytics (top pages), URL Inspection (8 URLs), Sitemaps
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN_FILE = Path("C:/Users/mario/.gemini/antigravity/tools/execution/gsc_token.json")
OUTPUT_FILE = Path("C:/Users/mario/.gemini/antigravity/tools/execution/custom_designs_tx/GSC_LIVE_DATA_2026-05-04.md")
SITE_URL = "https://www.customdesignstx.com/"
SITE_URL_ALT = "sc-domain:customdesignstx.com"

INSPECT_URLS = [
    "https://www.customdesignstx.com/blog/home-theater-surround-sound-mcallen",
    "https://www.customdesignstx.com/blog/surround-sound-installation-mcallen-tx",
    "https://www.customdesignstx.com/blog/cctv-installation-mcallen-tx",
    "https://www.customdesignstx.com/blog/alarm-system-installation-mcallen-tx",
    "https://www.customdesignstx.com/blog/security-camera-installation-edinburg-tx",
    "https://www.customdesignstx.com/blog/security-camera-installation-harlingen-tx",
    "https://www.customdesignstx.com/blog/security-camera-installation-mission-tx",
    "https://www.customdesignstx.com/blog/security-camera-installation-pharr-tx",
]

def load_creds():
    token_data = json.loads(TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"]
    )
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
            # Save refreshed token
            token_data["token"] = creds.token
            TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
            print("Token refreshed and saved.")
    return creds

def detect_property(service):
    """Try to find the correct property URL from verified list."""
    try:
        sites = service.sites().list().execute()
        site_entries = sites.get("siteEntry", [])
        print(f"Verified properties: {[s['siteUrl'] for s in site_entries]}")
        # Prefer exact match, then domain property, then prefix
        for url in [SITE_URL, SITE_URL_ALT, "https://customdesignstx.com/"]:
            for s in site_entries:
                if s["siteUrl"] == url:
                    return url
        # Return first if nothing matches
        if site_entries:
            return site_entries[0]["siteUrl"]
    except Exception as e:
        print(f"Could not list sites: {e}")
    return SITE_URL

def get_search_analytics(service, site_url):
    """Top 20 pages by impressions, last 28 days."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=28)

    body = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": ["page"],
        "rowLimit": 20,
        "startRow": 0,
    }
    try:
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        return resp.get("rows", []), str(start_date), str(end_date)
    except HttpError as e:
        print(f"Search analytics error: {e}")
        return [], str(start_date), str(end_date)

def get_sitemaps(service, site_url):
    """List all submitted sitemaps."""
    try:
        resp = service.sitemaps().list(siteUrl=site_url).execute()
        return resp.get("sitemap", [])
    except HttpError as e:
        print(f"Sitemaps error: {e}")
        return []

def inspect_url(sc_service, url, site_url):
    """Inspect a single URL via URL Inspection API."""
    try:
        body = {
            "inspectionUrl": url,
            "siteUrl": site_url,
        }
        resp = sc_service.urlInspection().index().inspect(body=body).execute()
        result = resp.get("inspectionResult", {})
        index_status = result.get("indexStatusResult", {})
        mobile_status = result.get("mobileUsabilityResult", {})

        coverage = index_status.get("coverageState", "UNKNOWN")
        verdict = index_status.get("verdict", "UNKNOWN")
        last_crawl = index_status.get("lastCrawlTime", "never")
        crawled_as = index_status.get("crawledAs", "")
        referring_urls = index_status.get("referringUrls", [])
        sitemap = index_status.get("sitemap", [])
        robots_txt_state = index_status.get("robotsTxtState", "")
        indexing_state = index_status.get("indexingState", "")
        page_fetch_state = index_status.get("pageFetchState", "")

        return {
            "url": url,
            "verdict": verdict,
            "coverage": coverage,
            "indexing_state": indexing_state,
            "page_fetch_state": page_fetch_state,
            "robots_txt": robots_txt_state,
            "last_crawl": last_crawl,
            "crawled_as": crawled_as,
            "in_sitemap": bool(sitemap),
            "referring_urls": len(referring_urls),
            "error": None,
        }
    except HttpError as e:
        print(f"  URL inspection error for {url}: {e}")
        return {
            "url": url,
            "verdict": "API_ERROR",
            "coverage": str(e),
            "error": str(e),
        }

def format_verdict(r):
    v = r.get("verdict", "")
    c = r.get("coverage", "")
    if v == "PASS":
        return "INDEXED"
    elif v == "NEUTRAL":
        return f"NOT INDEXED ({c})"
    elif v == "FAIL":
        return f"ERROR ({c})"
    elif v == "API_ERROR":
        return f"API ERROR"
    else:
        return f"{v} / {c}"

def main():
    print("Loading credentials...")
    creds = load_creds()

    # Build both API services
    webmasters = build("webmasters", "v3", credentials=creds)
    sc_service = build("searchconsole", "v1", credentials=creds)

    # Auto-detect property
    print("Detecting property...")
    site_url = detect_property(webmasters)
    print(f"Using property: {site_url}")

    # 1. Search Analytics
    print("\n[1/3] Pulling search analytics (top 20 pages)...")
    rows, start_date, end_date = get_search_analytics(webmasters, site_url)
    total_clicks = sum(r.get("clicks", 0) for r in rows)
    total_impressions = sum(r.get("impressions", 0) for r in rows)
    print(f"  Total clicks (top 20): {total_clicks} | Total impressions: {total_impressions}")

    # 2. Sitemaps
    print("\n[2/3] Pulling sitemaps...")
    sitemaps = get_sitemaps(webmasters, site_url)
    print(f"  Found {len(sitemaps)} sitemap(s)")

    # 3. URL Inspection
    print("\n[3/3] Inspecting 8 URLs...")
    inspections = []
    for url in INSPECT_URLS:
        print(f"  Checking: {url}")
        result = inspect_url(sc_service, url, site_url)
        inspections.append(result)
        print(f"    => {format_verdict(result)}")

    # Build report
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append(f"# GSC Live Audit — customdesignstx.com")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Property:** `{site_url}`  ")
    lines.append(f"**Date range:** {start_date} → {end_date} (28 days)")
    lines.append("")

    # Summary box
    lines.append("## Summary")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Clicks (all pages) | {int(total_clicks):,} |")
    lines.append(f"| Total Impressions (all pages) | {int(total_impressions):,} |")
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    lines.append(f"| Overall CTR | {overall_ctr:.2f}% |")
    lines.append(f"| Sitemaps submitted | {len(sitemaps)} |")
    indexed_count = sum(1 for r in inspections if r.get("verdict") == "PASS")
    lines.append(f"| New URLs indexed (of 8 checked) | {indexed_count} / 8 |")
    lines.append("")

    # Search Analytics
    lines.append("## Search Analytics — Top 20 Pages by Impressions")
    lines.append(f"*Last 28 days: {start_date} to {end_date}*")
    lines.append("")
    if rows:
        lines.append("| # | Page | Clicks | Impressions | CTR | Avg Position |")
        lines.append("|---|------|--------|-------------|-----|--------------|")
        for i, row in enumerate(rows, 1):
            page = row["keys"][0]
            clicks = int(row.get("clicks", 0))
            impressions = int(row.get("impressions", 0))
            ctr = row.get("ctr", 0) * 100
            pos = row.get("position", 0)
            # Shorten URL for readability
            short_page = page.replace("https://www.customdesignstx.com", "")
            lines.append(f"| {i} | `{short_page}` | {clicks:,} | {impressions:,} | {ctr:.1f}% | {pos:.1f} |")
    else:
        lines.append("*No search analytics data returned. Site may have insufficient traffic or property mismatch.*")
    lines.append("")

    # URL Inspection
    lines.append("## URL Inspection — 8 Target URLs")
    lines.append("")
    lines.append("| URL | Status | Coverage State | Last Crawl | In Sitemap |")
    lines.append("|-----|--------|----------------|------------|------------|")
    for r in inspections:
        url_short = r["url"].replace("https://www.customdesignstx.com", "")
        verdict = format_verdict(r)
        coverage = r.get("coverage", "")
        last_crawl = r.get("last_crawl", "never")
        if last_crawl and last_crawl != "never":
            last_crawl = last_crawl[:10]  # date only
        in_sitemap = "Yes" if r.get("in_sitemap") else "No"
        if r.get("error"):
            lines.append(f"| `{url_short}` | API ERROR | {r['error'][:60]} | — | — |")
        else:
            lines.append(f"| `{url_short}` | **{verdict}** | {coverage} | {last_crawl} | {in_sitemap} |")
    lines.append("")

    # Detailed inspection breakdown
    lines.append("### Detailed Inspection Results")
    lines.append("")
    for r in inspections:
        url_short = r["url"].replace("https://www.customdesignstx.com", "")
        lines.append(f"#### `{url_short}`")
        lines.append(f"- **Verdict:** {r.get('verdict', 'N/A')}")
        lines.append(f"- **Coverage State:** {r.get('coverage', 'N/A')}")
        lines.append(f"- **Indexing State:** {r.get('indexing_state', 'N/A')}")
        lines.append(f"- **Page Fetch State:** {r.get('page_fetch_state', 'N/A')}")
        lines.append(f"- **Robots.txt:** {r.get('robots_txt', 'N/A')}")
        lines.append(f"- **Last Crawl:** {r.get('last_crawl', 'never')}")
        lines.append(f"- **Crawled As:** {r.get('crawled_as', 'N/A')}")
        lines.append(f"- **In Sitemap:** {'Yes' if r.get('in_sitemap') else 'No'}")
        lines.append(f"- **Referring URLs:** {r.get('referring_urls', 0)}")
        lines.append("")

    # Sitemaps
    lines.append("## Sitemaps")
    lines.append("")
    if sitemaps:
        lines.append("| Sitemap URL | Type | Last Downloaded | Submitted | Indexed | Warnings | Errors |")
        lines.append("|-------------|------|----------------|-----------|---------|----------|--------|")
        for sm in sitemaps:
            sm_url = sm.get("path", "")
            sm_type = sm.get("type", "")
            last_dl = sm.get("lastDownloaded", "")[:10] if sm.get("lastDownloaded") else "never"
            submitted = sm.get("contents", [{}])[0].get("submitted", 0) if sm.get("contents") else 0
            indexed = sm.get("contents", [{}])[0].get("indexed", 0) if sm.get("contents") else 0
            warnings = sm.get("warnings", 0)
            errors = sm.get("errors", 0)
            lines.append(f"| `{sm_url}` | {sm_type} | {last_dl} | {submitted} | {indexed} | {warnings} | {errors} |")

        # Raw sitemap details
        lines.append("")
        lines.append("### Sitemap Details (raw)")
        lines.append("```json")
        lines.append(json.dumps(sitemaps, indent=2, default=str))
        lines.append("```")
    else:
        lines.append("*No sitemaps found or property not verified.*")
    lines.append("")

    # Raw analytics (top 10 extended)
    lines.append("## Raw Search Analytics (all rows)")
    lines.append("```json")
    lines.append(json.dumps(rows[:20], indent=2, default=str))
    lines.append("```")

    report = "\n".join(lines)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {OUTPUT_FILE}")

    # Print summary to console
    print("\n" + "="*60)
    print("AUDIT COMPLETE — SUMMARY")
    print("="*60)
    print(f"Total Clicks (last 28d): {int(total_clicks):,}")
    print(f"Total Impressions (last 28d): {int(total_impressions):,}")
    print(f"Sitemaps: {len(sitemaps)}")
    print(f"\nURL Inspection Results:")
    for r in inspections:
        short = r["url"].split("/blog/")[-1]
        print(f"  {short:<55} => {format_verdict(r)}")

if __name__ == "__main__":
    main()
