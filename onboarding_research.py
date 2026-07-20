#!/usr/bin/env python3
"""
Onboarding Research Engine — Antigravity Digital
==================================================
Gathers real research data for client onboarding:
  - Website deep scan: Firecrawl /scrape (JS rendering) when FIRECRAWL_API_KEY is set,
    else legacy Bright Data Scraping Browser, else plain fetch
  - Google SERP research: Serper.dev JSON API when SERPER_API_KEY is set (organic +
    People-Also-Ask + related searches — no HTML parsing), else legacy Bright Data
  - Technical SEO sweep (plain Python requests)
  - Outputs a research_bundle.json for onboard_client.py

Keys live in Mission Control's .env.local (C:/Users/mario/missioncontrol/dashboard/
.env.local) — the loader reads the local .env.local first, then falls back to MC's.
Bright Data is fully optional (account hl_b6130486 suspended 2026-07; kept as fallback only).

Usage:
    python onboarding_research.py --name "Custom Designs TX" --url "https://customdesignstx.com" --city "McAllen" --vertical "Low Voltage & Security"
"""

import json
import os
import re
import sys
import base64
import argparse
import textwrap
from pathlib import Path
from datetime import datetime, timezone
from urllib import request as _ureq
from urllib.error import URLError
from urllib.robotparser import RobotFileParser
import ssl
import socket

# ── Paths ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ONBOARDING_DIR = SCRIPT_DIR / "onboarding_reports"

# ── .env.local loader ───────────────────────────────────────────────────
_ENV = {}
_ENV_LOADED = False

_MC_ENV_PATH = Path("C:/Users/mario/missioncontrol/dashboard/.env.local")

def _load_env() -> dict:
    global _ENV, _ENV_LOADED
    if _ENV_LOADED:
        return _ENV
    # Local .env.local wins; MC dashboard .env.local fills in anything missing
    # (SERPER_API_KEY / FIRECRAWL_API_KEY live there — one canonical key location).
    for env_path in (SCRIPT_DIR / ".env.local", _MC_ENV_PATH):
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    _ENV.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    _ENV_LOADED = True
    return _ENV

# ── Serper.dev (SERP JSON — primary) + Firecrawl (JS page render — primary) ─

def _serper_key() -> str:
    return _load_env().get("SERPER_API_KEY") or os.environ.get("SERPER_API_KEY", "")

def _firecrawl_key() -> str:
    return _load_env().get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_API_KEY", "")

def serper_search(query: str, num: int = 20, timeout: int = 20) -> dict | None:
    """Google SERP via Serper.dev — returns the parsed JSON, or None on failure."""
    key = _serper_key()
    if not key:
        return None
    try:
        req = _ureq.Request(
            "https://google.serper.dev/search",
            data=json.dumps({"q": query, "gl": "us", "hl": "en", "num": num}).encode("utf-8"),
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
        )
        with _ureq.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [WARN] Serper search failed for '{query}': {e}", file=sys.stderr)
        return None

def firecrawl_fetch(url: str, timeout: int = 60) -> str | None:
    """Fetch a URL through Firecrawl /scrape (full JS rendering). Returns raw HTML or None."""
    key = _firecrawl_key()
    if not key:
        return None
    try:
        req = _ureq.Request(
            "https://api.firecrawl.dev/v1/scrape",
            data=json.dumps({"url": url, "formats": ["rawHtml"]}).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with _ureq.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        html = (payload.get("data") or {}).get("rawHtml") or (payload.get("data") or {}).get("html")
        if html and len(html) > 100:
            return html
        print(f"  [WARN] Firecrawl returned empty content for {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [WARN] Firecrawl fetch failed for {url}: {e}", file=sys.stderr)
        return None


# ── Bright Data Web Unlocker (LEGACY fallback — account suspended 2026-07) ──

_BD_URL = "https://api.brightdata.com/request"

def _wb_token() -> str:
    env = _load_env()
    return env.get("BRIGHTDATA_WEB_UNLOCKER_API") or env.get("BRIGHT_DATA_KEY") or os.environ.get("BRIGHT_DATA_KEY", "")

def _bd_auth_header(token: str) -> str:
    if ":" in token:
        return f"Basic {base64.b64encode(token.encode('utf-8')).decode('utf-8')}"
    return f"Bearer {token}"

def bright_fetch(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL through Bright Data Web Unlocker (raw HTML, no JS). LEGACY fallback."""
    token = _wb_token()
    if not token:
        return None
    try:
        req = _ureq.Request(
            _BD_URL,
            data=json.dumps({
                "zone": "web_unlocker1",
                "url": url,
                "format": "raw",
            }).encode("utf-8"),
            headers={
                "Authorization": _bd_auth_header(token),
                "Content-Type": "application/json",
            },
        )
        with _ureq.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Bright Data Web Unlocker fetch failed for {url}: {e}", file=sys.stderr)
        return None


# ── Bright Data Scraping Browser (full JS rendering via Playwright CDP) ─

def bright_browser_fetch(url: str, wait_ms: int = 3000, timeout_ms: int = 60000) -> str | None:
    """Fetch a URL through Bright Data Scraping Browser — full JS execution.

    Connects Playwright to Bright Data's headless Chrome via CDP WebSocket.
    Essential for Next.js / Vercel / JS-rendered sites where 'raw' format
    returns only the HTML shell (~5KB) instead of the full rendered page.

    Cost: ~$0.01–0.03 per page (Scraping Browser metered by bandwidth).
    """
    env = _load_env()
    ws_url = env.get("BRIGHTDATA_SCRAPING_BROWSER_WS") or env.get("BRIGHTDATA_SCRAPING_BROWSER")
    if not ws_url:
        print("  [WARN] No BRIGHTDATA_SCRAPING_BROWSER_WS in .env.local — cannot render JS pages", file=sys.stderr)
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [WARN] playwright not installed — run: pip install playwright && playwright install chromium", file=sys.stderr)
        return None

    import time
    last_err = None

    for attempt in range(3):
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(ws_url)
                page = None
                try:
                    if browser.contexts:
                        context = browser.contexts[0]
                        page = context.pages[0] if context.pages else context.new_page()
                    else:
                        context = browser.new_context()
                        page = context.new_page()

                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(wait_ms)
                    html = page.content()
                    return html
                finally:
                    if page:
                        try:
                            page.close()
                        except Exception:
                            pass
                    try:
                        browser.close()
                    except Exception:
                        pass
        except Exception as e:
            last_err = e
            if attempt < 2:
                cooldown = (attempt + 1) * 3
                print(f"  [RETRY] Scraping Browser attempt {attempt + 1} failed, waiting {cooldown}s...", file=sys.stderr)
                time.sleep(cooldown)

    print(f"  [WARN] Bright Data Scraping Browser failed after 3 attempts. Last error: {last_err}", file=sys.stderr)
    return None


def plain_fetch(url: str, timeout: int = 15) -> tuple[int, dict, str]:
    """Plain Python fetch. Returns (status_code, headers_dict, body)."""
    try:
        ctx = ssl.create_default_context()
        req = _ureq.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with _ureq.urlopen(req, timeout=timeout, context=ctx) as resp:
            headers = dict(resp.headers)
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, headers, body
    except Exception as e:
        return 0, {}, str(e)

def extract_text_from_html(html: str) -> str:
    """Strip HTML tags, get readable text."""
    if not html:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


# ── Website Deep Scan ───────────────────────────────────────────────────

def scan_website(url: str, name: str) -> dict:
    """Scrape homepage + key pages. Firecrawl (JS render) first, then legacy BD, then plain."""
    print(f"  [1/3] Fetching homepage (browser render): {url}")
    html = firecrawl_fetch(url) or bright_browser_fetch(url) or bright_fetch(url) or plain_fetch(url)[2]

    if not html or len(html) < 100:
        return {"error": f"Could not fetch {url}", "business_summary": "", "services": [], "trust_signals": [], "contact_info": {}, "content_audit": {}, "brand_voice": ""}

    text = extract_text_from_html(html)

    # Extract title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    # Extract meta description
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    desc = desc_match.group(1) if desc_match else ""

    # Look for common patterns: phone numbers, emails, addresses
    phones = list(set(re.findall(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text)))
    emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)))

    # Look for address patterns
    addr_patterns = re.findall(r'\d{1,5}\s+\w+(?:\s+\w+){1,4},?\s+\w+,\s+\w{2}\s+\d{5}', text)
    addresses = list(set(addr_patterns))

    # Detect services from heading tags and list items
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)
    lis = re.findall(r'<li[^>]*>(.*?)</li>', html, re.IGNORECASE)

    # Trust signals
    trust_keywords = ['licensed', 'insured', 'certified', 'bonded', 'accredited', 'award', 'years', 'bbb', 'warranty', 'guarantee', 'testimonial', 'review']
    trust_lines = []
    for line in text.split('\n'):
        line_lower = line.lower()
        if any(kw in line_lower for kw in trust_keywords):
            trust_lines.append(line.strip()[:200])

    # Content audit
    has_blog = bool(re.search(r'(?:blog|article|news)', html, re.IGNORECASE))
    has_about = bool(re.search(r'(?:about|our story)', html, re.IGNORECASE))
    has_contact = bool(re.search(r'(?:contact|get in touch)', html, re.IGNORECASE))
    has_faq = bool(re.search(r'(?:faq|frequently asked)', html, re.IGNORECASE))

    # Build service list from H2s and menu items
    services = []
    for h2 in h2s[:10]:
        clean = re.sub(r'<[^>]+>', '', h2).strip()
        if clean and len(clean) > 3 and len(clean) < 100:
            services.append(clean)

    # Gather body text for business summary (first 1000 chars of visible text)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body_html = body_match.group(1) if body_match else html
    body_text = extract_text_from_html(body_html)
    summary_lines = [l.strip() for l in body_text.split('\n') if len(l.strip()) > 40][:20]
    business_summary = '\n'.join(summary_lines[:8])

    # Brand voice detection
    brand_indicators = []
    if re.search(r'\b(you|your|we|our|us)\b', text, re.IGNORECASE):
        brand_indicators.append("First/second-person voice — direct customer address")
    if re.search(r'\b(trusted|reliable|premium|quality|expert|professional|best)\b', text, re.IGNORECASE):
        brand_indicators.append("Authority/quality-focused language")
    if re.search(r'\b(community|local|family|neighbor|RGV|Rio Grande|valley)\b', text, re.IGNORECASE):
        brand_indicators.append("Community/local-focused positioning")

    # Try about page
    about_html = None
    for about_path in ['/about', '/about-us', '/our-company']:
        about_url = url.rstrip('/') + about_path
        about_html = firecrawl_fetch(about_url) or bright_browser_fetch(about_url, wait_ms=2000) or bright_fetch(about_url)
        if about_html and len(about_html) > 100:
            break

    about_text = ""
    if about_html:
        about_text = extract_text_from_html(about_html)

    return {
        "business_summary": business_summary[:2000] if business_summary else f"Website analysis of {name} at {url}. Title: {title}",
        "title": title,
        "meta_description": desc,
        "services": services[:12] if services else ["Services extracted from website — review and refine"],
        "brand_voice": "; ".join(brand_indicators) if brand_indicators else "Professional, service-oriented",
        "trust_signals": trust_lines[:8] if trust_lines else ["Website analyzed — manual review recommended for trust signals"],
        "contact_info": {
            "Phone": phones[0] if phones else "Found on website",
            "Email": emails[0] if emails else "Found on website",
            "Address": addresses[0] if addresses else "Found on website",
        },
        "content_audit": {
            "Blog": f"Yes — detected" if has_blog else "Not detected on homepage",
            "About Page": f"Present — {len(about_text)} chars extracted" if about_text else "Not detected",
            "Contact Page": "Detected" if has_contact else "Not detected",
            "FAQ": "Detected" if has_faq else "Not detected — opportunity",
            "Total Pages Estimate": f"~{len(html.split('<a '))} internal links found on homepage",
        },
    }


# ── Technical SEO Sweep ─────────────────────────────────────────────────

def scan_technical_seo(url: str) -> dict:
    """Check technical SEO health via plain HTTP requests."""
    print(f"  [2/3] Technical SEO sweep: {url}")
    findings = []
    hostname = re.sub(r'https?://(www\.)?', '', url).rstrip('/')
    base_url = re.sub(r'^(https?://[^/]+).*', r'\1', url)

    # HTTPS check
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                findings.append({"check": "HTTPS / SSL", "status": "pass", "detail": f"Valid SSL, expires {cert.get('notAfter', 'unknown')}"})
    except Exception as e:
        findings.append({"check": "HTTPS / SSL", "status": "fail", "detail": str(e)[:100]})

    # robots.txt
    try:
        status, headers, body = plain_fetch(f"{base_url}/robots.txt")
        if status == 200 and len(body) > 10:
            findings.append({"check": "robots.txt", "status": "pass", "detail": f"Present ({len(body)} bytes)"})
            # Check if AI crawlers are allowed
            ai_bots = ['GPTBot', 'Claude-Extended', 'PerplexityBot', 'CCBot']
            allowed_ai = []
            for bot in ai_bots:
                if bot in body:
                    if f'Allow: /' in body or f'Allow: *' in body:
                        allowed_ai.append(bot)
            if allowed_ai:
                findings.append({"check": "AI Crawler Access", "status": "pass", "detail": f"Allowed: {', '.join(allowed_ai)}"})
            else:
                findings.append({"check": "AI Crawler Access", "status": "warn", "detail": "No explicit AI crawler rules found"})
        else:
            findings.append({"check": "robots.txt", "status": "fail", "detail": f"Missing or empty (HTTP {status})"})
    except Exception as e:
        findings.append({"check": "robots.txt", "status": "fail", "detail": str(e)[:100]})

    # sitemap.xml
    try:
        status, headers, body = plain_fetch(f"{base_url}/sitemap.xml")
        if status == 200 and len(body) > 50:
            url_count = len(re.findall(r'<url>', body)) or len(re.findall(r'<loc>', body))
            findings.append({"check": "sitemap.xml", "status": "pass", "detail": f"Present — {url_count} URLs"})
        else:
            findings.append({"check": "sitemap.xml", "status": "warn", "detail": f"Not found at /sitemap.xml (HTTP {status})"})
    except Exception as e:
        findings.append({"check": "sitemap.xml", "status": "warn", "detail": str(e)[:100]})

    # Fetch homepage for meta tag checks
    try:
        status, headers, body = plain_fetch(url)
        if status == 200:
            # Title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', body, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            if title and len(title) > 10:
                findings.append({"check": "Title Tag", "status": "pass", "detail": f"{title[:80]}"})
            else:
                findings.append({"check": "Title Tag", "status": "fail", "detail": "Missing or too short"})

            # Meta description
            desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', body, re.IGNORECASE)
            if desc_match:
                findings.append({"check": "Meta Description", "status": "pass", "detail": f"{desc_match.group(1)[:100]}"})
            else:
                findings.append({"check": "Meta Description", "status": "warn", "detail": "Not found on homepage"})

            # Viewport / Mobile
            viewport = re.search(r'<meta[^>]+name=["\']viewport["\']', body, re.IGNORECASE)
            if viewport:
                findings.append({"check": "Mobile Responsive", "status": "pass", "detail": "Viewport meta tag present"})
            else:
                findings.append({"check": "Mobile Responsive", "status": "warn", "detail": "No viewport meta tag"})

            # Schema / JSON-LD
            jsonld_matches = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.DOTALL | re.IGNORECASE)
            if jsonld_matches:
                schema_types = []
                for m in jsonld_matches:
                    types = re.findall(r'"@type"\s*:\s*"([^"]+)"', m)
                    schema_types.extend(types)
                findings.append({"check": "Schema Markup (JSON-LD)", "status": "pass", "detail": f"Found: {', '.join(schema_types[:6])}" if schema_types else "Found JSON-LD but no @type detected"})
            else:
                findings.append({"check": "Schema Markup (JSON-LD)", "status": "fail", "detail": "No JSON-LD schema detected — critical for AI visibility and rich results"})

            # Open Graph
            og_title = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', body, re.IGNORECASE)
            og_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', body, re.IGNORECASE)
            og_image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', body, re.IGNORECASE)
            og_count = sum(1 for x in [og_title, og_desc, og_image] if x)
            if og_count >= 2:
                findings.append({"check": "Open Graph Tags", "status": "pass", "detail": f"Present — {og_count} of 3 core tags"})
            elif og_count == 1:
                findings.append({"check": "Open Graph Tags", "status": "warn", "detail": "Partial — only 1 of 3 core tags"})
            else:
                findings.append({"check": "Open Graph Tags", "status": "fail", "detail": "Missing — no OG tags found"})

            # Canonical
            canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', body, re.IGNORECASE)
            if canonical:
                findings.append({"check": "Canonical Tag", "status": "pass", "detail": f"Present: {canonical.group(1)[:60]}"})
            else:
                findings.append({"check": "Canonical Tag", "status": "warn", "detail": "Not found on homepage"})

            # H1 count
            h1s = re.findall(r'<h1[^>]*>', body, re.IGNORECASE)
            if len(h1s) == 1:
                findings.append({"check": "Heading Hierarchy", "status": "pass", "detail": "Single H1 — correct structure"})
            elif len(h1s) == 0:
                findings.append({"check": "Heading Hierarchy", "status": "warn", "detail": "No H1 tag found"})
            else:
                findings.append({"check": "Heading Hierarchy", "status": "warn", "detail": f"{len(h1s)} H1s — should be 1"})

            # Security headers
            csp = headers.get("Content-Security-Policy", "")
            hsts = headers.get("Strict-Transport-Security", "")
            xfo = headers.get("X-Frame-Options", "")
            xcto = headers.get("X-Content-Type-Options", "")
            sec_count = sum(1 for x in [csp, hsts, xfo, xcto] if x)
            if sec_count >= 3:
                findings.append({"check": "Security Headers", "status": "pass", "detail": f"{sec_count}/4 core headers present"})
            elif sec_count >= 1:
                missing_hdrs = [x for x, v in [('CSP',csp),('HSTS',hsts),('XFO',xfo),('XCTO',xcto)] if not v]
                missing_str = f" (missing: {', '.join(missing_hdrs)})" if missing_hdrs else ""
                findings.append({"check": "Security Headers", "status": "warn", "detail": f"Only {sec_count}/4 core headers present{missing_str}"})
            else:
                findings.append({"check": "Security Headers", "status": "fail", "detail": "None of 4 core security headers present"})

            # Server info
            server = headers.get("Server", "")
            if server:
                findings.append({"check": "Server Header", "status": "warn", "detail": f"Exposed: {server} — consider suppressing for security"})

    except Exception as e:
        findings.append({"check": "Homepage Fetch", "status": "fail", "detail": str(e)[:100]})

    # Calculate a rough score
    pass_count = sum(1 for f in findings if f["status"] == "pass")
    warn_count = sum(1 for f in findings if f["status"] == "warn")
    fail_count = sum(1 for f in findings if f["status"] == "fail")
    total = len(findings)
    score = max(10, min(95, int((pass_count / max(total, 1)) * 100) - (fail_count * 5)))

    return {
        "summary": f"Technical SEO sweep complete: {pass_count} pass, {warn_count} warn, {fail_count} fail across {total} checks.",
        "score": score,
        "findings": findings,
    }


# ── Google SERP Research (Serper.dev primary, Bright Data legacy fallback) ──

_SKIP_DOMAINS = ('google.com', 'youtube.com', 'yelp.com', 'facebook.com')

def _serp_research_serper(queries: list[str]) -> tuple[list, list]:
    """Competitor + keyword intel from Serper.dev structured JSON. No HTML parsing."""
    competitors, top_keywords = [], []
    for query in queries:
        data = serper_search(query)
        if not data:
            continue
        for entry in (data.get("organic") or [])[:20]:
            link = entry.get("link") or ""
            domain = re.sub(r'https?://(www\.)?', '', link).split('/')[0]
            if not domain or any(domain.endswith(sd) for sd in _SKIP_DOMAINS):
                continue
            competitors.append({
                "name": (entry.get("title") or domain.split('.')[0].replace('-', ' ').title())[:100],
                "domain": domain,
                "url": link,
                "rating": str(entry.get("rating") or ""),
                "reviews": str(entry.get("ratingCount") or ""),
                "found_for": query,
            })
        for paa in (data.get("peopleAlsoAsk") or [])[:10]:
            q = (paa.get("question") or "").strip()
            if len(q) > 10:
                top_keywords.append({"keyword": q, "source": "People Also Ask"})
        for rel in (data.get("relatedSearches") or [])[:10]:
            q = (rel.get("query") or "").strip()
            if len(q) > 5:
                top_keywords.append({"keyword": q, "source": "Related Search"})
    return competitors, top_keywords


def serp_research(name: str, city: str, vertical: str) -> dict:
    """Search Google SERPs for competitor and keyword intelligence."""
    print(f"  [3/3] SERP research: '{vertical} in {city}'")

    competitors = []
    top_keywords = []

    # Search for competitors
    queries = [
        f"{vertical} in {city}",
        f"best {vertical} {city}",
        f"top {vertical} companies {city} tx",
    ]

    if _serper_key():
        print("      [Serper.dev SERP API]")
        competitors, top_keywords = _serp_research_serper(queries)
        return _serp_compile(competitors, top_keywords, queries)

    for query in queries:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=en"
        html = bright_fetch(search_url, timeout=25)
        if not html:
            continue

        # Extract organic results
        # Look for linked headings (typical Google SERP pattern for organic results)
        result_blocks = re.findall(r'<a[^>]*href="(/url\?q=https?://[^"&]+)[^"]*"[^>]*>(.*?)</a>', html)
        seen_domains = set()

        for href, anchor_text in result_blocks[:20]:
            clean_href = re.sub(r'^/url\?q=', '', href)
            clean_href = re.sub(r'&.*$', '', clean_href)
            domain = re.sub(r'https?://(www\.)?', '', clean_href).split('/')[0]

            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            anchor_clean = re.sub(r'<[^>]+>', '', anchor_text).strip()
            if anchor_clean and len(anchor_clean) > 3 and domain not in ('google.com', 'youtube.com', 'yelp.com', 'facebook.com'):
                # Extract rating if present
                rating_match = re.search(r'(\d+\.?\d*)\s*(?:★|star)', html[html.find(anchor_clean):html.find(anchor_clean)+500] if anchor_clean in html else '')
                review_match = re.search(r'\(?(\d[\d,]*)\)?\s*reviews?', html[html.find(anchor_clean):html.find(anchor_clean)+500] if anchor_clean in html else '')

                competitors.append({
                    "name": domain.split('.')[0].replace('-', ' ').title(),
                    "domain": domain,
                    "url": clean_href,
                    "rating": rating_match.group(1) if rating_match else "",
                    "reviews": review_match.group(1).replace(',', '') if review_match else "",
                    "found_for": query,
                })

        # Also look for "People also ask" / related questions for keyword ideas
        paq = re.findall(r'<div[^>]*class="[^"]*related-question[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for q in paq[:10]:
            q_clean = re.sub(r'<[^>]+>', '', q).strip()
            if q_clean and len(q_clean) > 10:
                top_keywords.append({"keyword": q_clean, "source": "People Also Ask"})

        # Extract suggested related searches
        related = re.findall(r'<a[^>]*><b>(.*?)</b></a>', html)
        for r in related[:10]:
            r_clean = re.sub(r'<[^>]+>', '', r).strip()
            if r_clean and len(r_clean) > 5:
                top_keywords.append({"keyword": r_clean, "source": "Related Search"})

    return _serp_compile(competitors, top_keywords, queries)


def _serp_compile(competitors: list, top_keywords: list, queries: list) -> dict:
    # Deduplicate competitors by domain
    seen = set()
    unique_competitors = []
    for c in competitors:
        if c["domain"] not in seen:
            seen.add(c["domain"])
            unique_competitors.append(c)

    return {
        "competitors": unique_competitors[:10],
        "keyword_opportunities": list({k["keyword"]: k for k in top_keywords}.values())[:15],
        "queries_run": queries,
    }


# ── Main Research Orchestrator ──────────────────────────────────────────

def run_research(name: str, url: str, city: str, vertical: str, output_dir: str | None = None) -> str:
    """Run full research pipeline and output JSON bundle."""
    print()
    print("=" * 60)
    print(f"  Onboarding Research: {name}")
    print(f"  URL: {url}")
    print(f"  City: {city}")
    print(f"  Vertical: {vertical}")
    print("=" * 60)
    print()

    # Phase 1a: Website Deep Scan
    website_data = scan_website(url, name)

    # Phase 1b: Technical SEO
    tech_seo_data = scan_technical_seo(url)

    # Phase 1c: SERP Research
    serp_data = serp_research(name, city, vertical)

    # ── Compile JSON Bundle ──
    client_key = re.sub(r'[^a-z0-9]+', '_', name.lower().strip())
    if output_dir is None:
        output_dir = str(ONBOARDING_DIR / client_key)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    bundle = {
        "client": {
            "name": name,
            "url": url,
            "city": city,
            "vertical": vertical,
            "onboarded_at": datetime.now(timezone.utc).isoformat(),
        },
        "executive_summary": f"{name} is a {vertical} provider serving {city} and surrounding areas. Automated research gathered website content, technical SEO metrics, and SERP intelligence. Manual review and enrichment recommended before client delivery.",
        "scores": {
            "overall_readiness": 0,  # Filled after synthesis
            "website_quality": 60,   # Baseline
            "gbp_completeness": 0,   # Filled by GBP CLI
            "technical_seo": tech_seo_data.get("score", 50),
            "ai_visibility": 0,      # Filled by manual research
            "social_presence": 0,    # Filled by manual research
            "backlink_strength": 0,  # Filled by manual research
            "keyword_coverage": 50,  # Baseline from SERP
        },
        "website_scan": website_data,
        "technical_seo": tech_seo_data,
        "serp_research": serp_data,
        "gbp_audit": {"note": "To be filled by google-business-profile-pp-cli"},
        "competitor_intel": {"note": "To be synthesized from SERP research + WebSearch"},
        "ai_visibility": {"note": "To be filled by WebSearch/WebFetch research"},
        "social_scan": {"note": "To be filled by WebSearch + facebook-graph-pp-cli"},
        "backlink_profile": {"note": "To be filled by WebSearch research"},
        "keyword_map": {"note": "To be synthesized from SERP + google-serp-pp-cli"},
        "prioritized_actions": [],
        "ninety_day_plan": {"month_1": [], "month_2": [], "month_3": []},
    }

    bundle_path = Path(output_dir) / "research_bundle.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print()
    print(f"  Research bundle saved: {bundle_path}")
    print(f"  Next: enrich with GBP CLI, WebSearch, then generate report")
    return str(bundle_path)


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Onboarding Research Engine — Antigravity Digital",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python onboarding_research.py --name "Custom Designs TX" --url "https://customdesignstx.com" --city "McAllen" --vertical "Security Installation"
              python onboarding_research.py --name "Sugar Shack" --url "https://the-sugar-shack.com" --city "South Padre Island" --vertical "Candy Store"
        """),
    )
    parser.add_argument("--name", required=True, help="Business name")
    parser.add_argument("--url", required=True, help="Website URL")
    parser.add_argument("--city", required=True, help="City")
    parser.add_argument("--vertical", required=True, help="Vertical/category")
    parser.add_argument("--output", type=str, help="Output directory (optional)")

    args = parser.parse_args()
    run_research(args.name, args.url, args.city, args.vertical, args.output)


if __name__ == "__main__":
    main()
