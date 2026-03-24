#!/usr/bin/env python3
"""
account_health_check.py — Audit all 8 client accounts for GBP completeness,
website linkage, sitemap presence, and indexing health.

No browser needed — pure HTTP + Google Places API.

Usage:
  python account_health_check.py              # all clients
  python account_health_check.py --client optimum_clinic
  python account_health_check.py --no-telegram  # skip Telegram send
"""

import sys
import json
import argparse
import urllib.parse
import urllib.request
import re
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ─── Paths ────────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).parent
BRIEFS_DIR    = EXECUTION_DIR / "morning_briefs"
BRIEFS_DIR.mkdir(exist_ok=True)

CONFIG_PATH = EXECUTION_DIR / "gbp_config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    GBP_CONFIG = json.load(f)

API_KEY = GBP_CONFIG.get("places_api_key", "")

# ─── Client Master Config ─────────────────────────────────────────────────────
# Combines gbp_config.json data with domain names from program.md

CLIENTS = {
    "sugar_shack": {
        "name":         "The Sugar Shack",
        "domain":       None,
        "gbp_access":   "ok",
        "places_query": "The Sugar Shack South Padre Island TX",
        "expected_name":"sugar shack",
    },
    "island_arcade": {
        "name":         "Island Arcade SPI",
        "domain":       None,
        "gbp_access":   "duplicate",
        "places_query": "Island Arcade SPI South Padre Island TX",
        "expected_name":"island arcade",
    },
    "island_candy": {
        "name":         "Island Candy",
        "domain":       None,
        "gbp_access":   "ok",
        "places_query": "Island Candy South Padre Island TX arcade",
        "expected_name":"island candy",
    },
    "juan": {
        "name":         "Juan Elizondo RE/MAX Elite",
        "domain":       "juanjoseelizondo.com",
        "gbp_access":   "suspended",
        "places_query": "Juan Elizondo RE/MAX McAllen TX",
        "expected_name":"elizondo",
    },
    "spi_fun_rentals": {
        "name":         "SPI Fun Rental & Island Surf Rental",
        "domain":       "spifunrental.com",
        "gbp_access":   "duplicate",
        "places_query": "SPI Fun Rental Island Surf Rental South Padre Island TX",
        "expected_name":"spi fun",
    },
    "custom_designs_tx": {
        "name":         "Custom Designs TX",
        "domain":       "customdesignstx.com",
        "gbp_access":   "ok",
        "places_query": "Custom Designs TX McAllen",
        "expected_name":"custom designs",
    },
    "optimum_clinic": {
        "name":         "Optimum Health & Wellness Clinic",
        "domain":       "optimumhealthrx.com",
        "gbp_access":   "duplicate",
        "places_query": "Optimum Health Wellness Clinic Pharr TX",
        "expected_name":"optimum",
    },
    "optimum_foundation": {
        "name":         "Optimum Health and Wellness Foundation",
        "domain":       None,
        "gbp_access":   "no_access",
        "places_query": None,
        "expected_name":"optimum foundation",
    },
}

# ─── GBP Check via Places API ────────────────────────────────────────────────

def _places_textsearch(query: str) -> dict | None:
    """Call Places Text Search, return first result dict or None."""
    try:
        q   = urllib.parse.quote_plus(query)
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={q}&key={API_KEY}"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        results = data.get("results", [])
        return results[0] if results else None
    except Exception as e:
        return {"_error": str(e)}


def _places_details(place_id: str) -> dict:
    """Call Places Details API for rich fields."""
    fields = "website,formatted_phone_number,opening_hours,photos,types,business_status,rating,user_ratings_total,name,formatted_address"
    try:
        url = (f"https://maps.googleapis.com/maps/api/place/details/json"
               f"?place_id={place_id}&fields={fields}&key={API_KEY}")
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        return data.get("result", {})
    except Exception as e:
        return {"_error": str(e)}


def check_gbp(_client_key: str, cfg: dict) -> dict:
    """
    Returns GBP health dict:
      place_id, name_found, website_url, categories, phone, hours_set,
      photo_count, rating, review_count, business_status, error
    """
    result = {
        "place_id":       None,
        "name_found":     None,
        "website_url":    None,
        "categories":     [],
        "phone":          None,
        "hours_set":      False,
        "photo_count":    0,
        "rating":         None,
        "review_count":   None,
        "business_status": None,
        "error":          None,
    }

    if not cfg.get("places_query") or not API_KEY:
        result["error"] = "No places_query or API key"
        return result

    top = _places_textsearch(cfg["places_query"])
    if not top:
        result["error"] = "Not found in Places search"
        return result
    if "_error" in top:
        result["error"] = top["_error"]
        return result

    # Basic fields from text search
    result["place_id"]     = top.get("place_id")
    result["name_found"]   = top.get("name")
    result["rating"]       = top.get("rating")
    result["review_count"] = top.get("user_ratings_total")

    # Enrich with Details API
    if result["place_id"]:
        details = _places_details(result["place_id"])
        if "_error" not in details:
            result["website_url"]    = details.get("website")
            result["phone"]          = details.get("formatted_phone_number")
            result["hours_set"]      = bool(details.get("opening_hours"))
            result["photo_count"]    = len(details.get("photos", []))
            result["business_status"] = details.get("business_status")
            # Categories = first 3 types, strip underscores
            raw_types = details.get("types", [])
            skip = {"point_of_interest", "establishment", "store"}
            result["categories"] = [
                t.replace("_", " ").title()
                for t in raw_types
                if t not in skip
            ][:3]
            # Use better rating from details if available
            if details.get("rating"):
                result["rating"] = details["rating"]
            if details.get("user_ratings_total"):
                result["review_count"] = details["user_ratings_total"]

    return result


# ─── Website & Sitemap Check ─────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 8) -> tuple[int, str]:
    """Return (status_code, body_text). Status 0 = connection error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AccountHealthBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(50000).decode("utf-8", errors="replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def check_website(domain: str) -> dict:
    """
    Returns website health dict:
      homepage_ok, sitemap_exists, sitemap_url_count, robots_allows_google,
      gsc_verified, error
    """
    result = {
        "homepage_ok":          False,
        "sitemap_exists":       False,
        "sitemap_url_count":    0,
        "robots_allows_google": None,
        "gsc_verified":         False,
        "error":                None,
    }

    base = f"https://{domain}"

    # Homepage
    status, body = _http_get(base)
    result["homepage_ok"] = (status == 200)
    if status == 0:
        result["error"] = "Homepage unreachable"

    # GSC verification meta tag
    if body:
        gsc_match = re.search(
            r'<meta\s+name=["\']google-site-verification["\']', body, re.IGNORECASE
        )
        result["gsc_verified"] = bool(gsc_match)

    # Sitemap
    for sm_path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/"]:
        sm_status, sm_body = _http_get(f"{base}{sm_path}")
        if sm_status == 200 and sm_body.strip().startswith("<"):
            result["sitemap_exists"] = True
            # Count <url> or <sitemap> tags
            count = len(re.findall(r"<url>|<sitemap>", sm_body))
            result["sitemap_url_count"] = count
            break

    # robots.txt
    rob_status, rob_body = _http_get(f"{base}/robots.txt")
    if rob_status == 200 and rob_body:
        # Check for Disallow: / for Googlebot or User-agent: *
        lines = rob_body.lower().splitlines()
        in_google_block = False
        in_all_block    = False
        disallowed_all  = False
        for line in lines:
            if line.startswith("user-agent: googlebot"):
                in_google_block = True
                in_all_block    = False
            elif line.startswith("user-agent: *"):
                in_all_block    = True
                in_google_block = False
            elif line.startswith("user-agent:"):
                in_google_block = False
                in_all_block    = False
            elif line.startswith("disallow: /") and (in_google_block or in_all_block):
                # Disallow: / blocks everything
                if line.strip() == "disallow: /":
                    disallowed_all = True
        result["robots_allows_google"] = not disallowed_all
    else:
        result["robots_allows_google"] = True  # No robots.txt = allowed

    return result


# ─── HTML Report Generator ───────────────────────────────────────────────────

STATUS_ICONS = {
    "ok":         ("OK", "#22c55e"),       # green
    "warning":    ("WARN", "#f59e0b"),     # amber
    "error":      ("ISSUE", "#ef4444"),    # red
    "info":       ("INFO", "#6366f1"),     # indigo
}

GBP_ACCESS_LABELS = {
    "ok":         ("GBP Active", "ok"),
    "duplicate":  ("DUPLICATE LISTING - Fix Required", "error"),
    "suspended":  ("SUSPENDED - Reinstatement Needed", "error"),
    "no_access":  ("No GBP Access", "warning"),
}

def _badge(text: str, level: str) -> str:
    _, color = STATUS_ICONS.get(level, ("?", "#888"))
    bg = color + "22"
    return (f'<span style="background:{bg};color:{color};border:1px solid {color};'
            f'border-radius:4px;padding:2px 7px;font-size:11px;font-weight:700;'
            f'font-family:monospace;">{text}</span>')


def _row(label: str, value: str, level: str = "ok") -> str:
    _, color = STATUS_ICONS.get(level, ("?", "#888"))
    icon = {"ok": "&#10003;", "warning": "&#9888;", "error": "&#10007;", "info": "&#9432;"}.get(level, "")
    return (f'<tr><td style="color:#94a3b8;padding:3px 8px 3px 0;white-space:nowrap;">{label}</td>'
            f'<td style="padding:3px 0;"><span style="color:{color}">{icon}</span> {value}</td></tr>')


def render_client_card(_client_key: str, cfg: dict, gbp: dict, site: dict | None) -> str:
    access_label, access_level = GBP_ACCESS_LABELS.get(cfg["gbp_access"], ("Unknown", "warning"))
    domain = cfg.get("domain")

    # Card header color
    header_color = {"ok": "#22c55e", "duplicate": "#ef4444", "suspended": "#ef4444", "no_access": "#f59e0b"}.get(cfg["gbp_access"], "#888")

    rows = []

    # GBP access status
    rows.append(_row("GBP Status", f"{_badge(access_label, access_level)}", access_level))

    # GBP details
    if gbp.get("error"):
        rows.append(_row("GBP Lookup", gbp["error"], "warning"))
    else:
        name = gbp.get("name_found") or "Not found"
        rows.append(_row("Listed As", name, "ok" if gbp.get("name_found") else "warning"))

        # Website URL on GBP
        gbp_site = gbp.get("website_url")
        if gbp_site:
            # Strip trailing slash and protocol for display
            display = re.sub(r"^https?://", "", gbp_site).rstrip("/")
            if domain and domain.lower() in gbp_site.lower():
                rows.append(_row("Website on GBP", display, "ok"))
            else:
                rows.append(_row("Website on GBP", f"{display} (expected: {domain or 'none'})", "warning"))
        else:
            rows.append(_row("Website on GBP", "NOT SET &mdash; Google cannot connect site to listing", "error"))

        # Phone
        phone = gbp.get("phone")
        rows.append(_row("Phone", phone or "Not listed", "ok" if phone else "warning"))

        # Hours
        rows.append(_row("Hours", "Set", "ok") if gbp.get("hours_set") else _row("Hours", "NOT SET", "warning"))

        # Photos
        pc = gbp.get("photo_count", 0)
        photo_level = "ok" if pc >= 5 else ("warning" if pc >= 1 else "error")
        rows.append(_row("Photos", f"{pc} photos", photo_level))

        # Rating + reviews
        rating  = gbp.get("rating")
        reviews = gbp.get("review_count")
        if rating:
            rows.append(_row("Rating", f"{rating} &#9733; ({reviews or 0} reviews)", "ok"))

        # Categories
        cats = gbp.get("categories")
        if cats:
            rows.append(_row("Categories", ", ".join(cats), "info"))

    # Website health
    if site:
        rows.append(_row("Homepage", "200 OK" if site["homepage_ok"] else "UNREACHABLE", "ok" if site["homepage_ok"] else "error"))

        if site["sitemap_exists"]:
            n = site["sitemap_url_count"]
            rows.append(_row("Sitemap", f"sitemap.xml found &mdash; {n} URLs", "ok"))
        else:
            rows.append(_row("Sitemap", "NOT FOUND &mdash; Google may miss new pages", "error"))

        rob = site.get("robots_allows_google")
        if rob is True:
            rows.append(_row("robots.txt", "Googlebot allowed", "ok"))
        elif rob is False:
            rows.append(_row("robots.txt", "Googlebot BLOCKED", "error"))

        gsc = site.get("gsc_verified")
        rows.append(_row("Search Console", "Verification tag found", "ok") if gsc
                    else _row("Search Console", "NOT verified &mdash; submit sitemap manually at search.google.com/search-console", "warning"))

    elif domain:
        rows.append(_row("Website", "Check failed", "warning"))
    else:
        rows.append(_row("Website", "No website &mdash; ranking on GBP signals only", "info"))

    rows_html = "\n".join(rows)

    return f"""
<div style="background:#1e293b;border-radius:10px;margin-bottom:16px;overflow:hidden;border:1px solid #334155;">
  <div style="background:{header_color}18;border-bottom:2px solid {header_color};padding:10px 16px;display:flex;align-items:center;gap:10px;">
    <span style="font-weight:700;font-size:15px;color:#f1f5f9;">{cfg['name']}</span>
    {f'<span style="color:#94a3b8;font-size:12px;">&mdash; {domain}</span>' if domain else ''}
  </div>
  <div style="padding:12px 16px;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      {rows_html}
    </table>
  </div>
</div>"""


def generate_html(results: list, date_str: str) -> str:
    cards = "\n".join(r["card_html"] for r in results)

    issues = []
    for r in results:
        for issue in r.get("issues", []):
            issues.append(f"<li><strong>{r['name']}:</strong> {issue}</li>")
    issues_html = ("\n".join(issues)) if issues else "<li>No critical issues found.</li>"

    why_html = """
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:20px;border:1px solid #334155;">
  <h3 style="margin:0 0 10px;color:#f1f5f9;font-size:14px;">Why Rankings Change (Even While Posting)</h3>
  <ol style="color:#94a3b8;font-size:13px;margin:0;padding-left:18px;line-height:1.8;">
    <li><strong style="color:#ef4444;">Duplicate GBP listing</strong> = Google splits ranking authority between two profiles. Neither ranks well.</li>
    <li><strong style="color:#ef4444;">No website URL in GBP</strong> = Google cannot connect your site to your local listing.</li>
    <li><strong style="color:#ef4444;">No sitemap submitted</strong> = Google may not find new pages for weeks or months.</li>
    <li><strong style="color:#ef4444;">GBP suspension</strong> = listing is invisible in Google Maps &mdash; zero local visibility.</li>
    <li><strong style="color:#f59e0b;">Facebook posting</strong> = zero direct impact on Google rankings (social signals are indirect at best).</li>
    <li><strong style="color:#22c55e;">GBP posting</strong> = moderate positive impact on local map pack rankings. Keep doing it.</li>
    <li><strong style="color:#22c55e;">Website blogging</strong> = strong impact on organic rankings <em>if</em> the site is indexed by Google.</li>
  </ol>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Account Health Check — {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }}
  .container {{ max-width: 820px; margin: 0 auto; }}
  h1 {{ font-size: 22px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }}
  .subtitle {{ color: #64748b; font-size: 13px; margin-bottom: 20px; }}
  h2 {{ font-size: 15px; font-weight: 700; color: #94a3b8; margin: 20px 0 10px; text-transform: uppercase; letter-spacing: .05em; }}
  ul {{ color: #94a3b8; font-size: 13px; padding-left: 18px; line-height: 1.8; }}
  strong {{ color: #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
  <h1>Account Health Check</h1>
  <div class="subtitle">{date_str} &mdash; Generated {datetime.now().strftime("%I:%M %p")}</div>

  <h2>Issues Requiring Action</h2>
  <ul style="background:#1e293b;border-radius:10px;padding:14px 14px 14px 30px;border:1px solid #334155;margin-bottom:20px;">
    {issues_html}
  </ul>

  {why_html}

  <h2>Client Accounts</h2>
  {cards}
</div>
</body>
</html>"""


# ─── Telegram ────────────────────────────────────────────────────────────────

def _load_telegram_creds() -> tuple[str, str]:
    env = {}
    env_path = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_USER_ID", "")


def notify_mario(text: str) -> bool:
    try:
        token, chat_id = _load_telegram_creds()
        if not token or not chat_id:
            return False
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        resp = urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=data
            ), timeout=10
        )
        return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False


def send_document(file_path: Path, caption: str = "") -> bool:
    try:
        token, chat_id = _load_telegram_creds()
        if not token or not chat_id or not file_path.exists():
            return False
        boundary = "----HealthCheckBoundary"
        def field(name, value):
            return (f"--{boundary}\r\nContent-Disposition: form-data; "
                    f'name="{name}"\r\n\r\n{value}\r\n').encode()
        parts = [field("chat_id", chat_id)]
        if caption:
            parts.append(field("caption", caption[:1024]))
        fb = file_path.read_bytes()
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="document"; filename="{file_path.name}"\r\n'
             f"Content-Type: text/html\r\n\r\n").encode() + fb + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp   = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  [Telegram doc failed: {e}]")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit GBP + website health for all clients")
    parser.add_argument("--client",       default=None, help="Run for one client only")
    parser.add_argument("--no-telegram",  action="store_true", help="Skip Telegram notification")
    args = parser.parse_args()

    date_str = date.today().isoformat()
    out_path = BRIEFS_DIR / f"account_health_{date_str}.html"

    clients = {k: v for k, v in CLIENTS.items()
               if args.client is None or k == args.client}

    print(f"\nAccount Health Check -- {date_str}")
    print(f"Checking {len(clients)} client(s)...\n")

    results = []
    all_issues = []

    for key, cfg in clients.items():
        print(f"  [{key}]")

        # GBP check
        print(f"    GBP... ", end="", flush=True)
        gbp = check_gbp(key, cfg)
        gbp_summary = gbp.get("name_found") or gbp.get("error") or "?"
        print(gbp_summary[:50])

        # Website check
        site = None
        if cfg.get("domain"):
            print(f"    Website... ", end="", flush=True)
            site = check_website(cfg["domain"])
            site_summary = ("OK" if site["homepage_ok"] else "UNREACHABLE") + \
                           (", sitemap found" if site["sitemap_exists"] else ", NO SITEMAP")
            print(site_summary)

        # Collect issues
        issues = []
        access = cfg.get("gbp_access", "ok")
        if access == "duplicate":
            issues.append("DUPLICATE GBP listing — fix via Google Business Profile dashboard")
        elif access == "suspended":
            issues.append("GBP SUSPENDED — submit reinstatement request at business.google.com")
        elif access == "no_access":
            issues.append("No GBP access configured")

        if not gbp.get("error"):
            if not gbp.get("website_url"):
                issues.append("No website URL set in GBP listing")
            elif cfg.get("domain") and cfg["domain"].lower() not in gbp.get("website_url", "").lower():
                issues.append(f"Wrong website URL on GBP (expected {cfg['domain']})")
            if not gbp.get("hours_set"):
                issues.append("Business hours not set on GBP")
            if gbp.get("photo_count", 0) < 3:
                issues.append(f"Only {gbp.get('photo_count',0)} photos — add more for better rankings")

        if site:
            if not site["homepage_ok"]:
                issues.append(f"Website unreachable at {cfg['domain']}")
            if not site["sitemap_exists"]:
                issues.append("No sitemap.xml — submit one at search.google.com/search-console")
            if not site.get("gsc_verified"):
                issues.append("Google Search Console not verified — cannot monitor indexing")

        # Render HTML card
        card_html = render_client_card(key, cfg, gbp, site)

        results.append({
            "key":      key,
            "name":     cfg["name"],
            "card_html": card_html,
            "issues":   issues,
        })
        all_issues.extend([(cfg["name"], i) for i in issues])

    # Write HTML report
    html = generate_html(results, date_str)
    out_path.write_text(html, encoding="utf-8")
    print(f"\n  Report saved: {out_path}")

    # Summary to console
    print(f"\n  ISSUES FOUND ({len(all_issues)} total):")
    for name, issue in all_issues:
        print(f"    [{name}] {issue}")

    if not all_issues:
        print("    All accounts look healthy!")

    # Telegram
    if not args.no_telegram:
        issue_lines = [f"- {name}: {issue}" for name, issue in all_issues[:15]]
        msg = (
            f"[Account Health Check] {date_str}\n\n"
            f"{len(all_issues)} issues found across {len(clients)} accounts\n\n"
            + ("\n".join(issue_lines) if issue_lines else "All accounts healthy!")
        )
        if notify_mario(msg):
            print("\n  Telegram: summary sent")
        if send_document(out_path, caption=f"Account Health Report {date_str}"):
            print("  Telegram: HTML report sent")

    return 0


if __name__ == "__main__":
    sys.exit(main())
