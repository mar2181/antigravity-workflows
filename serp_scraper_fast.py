#!/usr/bin/env python3
"""Fast SERP scraper using Bright Data SERP API zone (serp_api1)."""
import json, re, sys, time, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

TOKEN = "7fe773b11b190ba758a122c288438d14deef5356a694ef707a3c847de5af3b5c"
BD_URL = "https://api.brightdata.com/request"
CONFIG_PATH = Path(__file__).parent / "keyword_rankings_config.json"
STATE_PATH = Path(__file__).parent / "keyword_rankings_state.json"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def fetch_serp(keyword: str, tbm: str = "") -> str | None:
    """Fetch Google SERP via Bright Data SERP API. Returns raw HTML text."""
    enc = urllib.parse.quote_plus(keyword)
    if tbm:
        url = f"https://www.google.com/search?q={enc}&tbm={tbm}&gl=us&hl=en"
    else:
        url = f"https://www.google.com/search?q={enc}&gl=us&hl=en&pws=0"

    payload = json.dumps({"zone": "serp_api1", "url": url, "format": "raw"}).encode()
    req = urllib.request.Request(
        BD_URL, data=payload,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"      [BD SERP error: {e}]")
        return None

def strip_html(raw: str) -> str:
    """Strip HTML tags, return plain text lines."""
    raw = re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<style[^>]*>.*?</style>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<(?:br|p|div|li|tr|h[1-6])[^>]*/?>', '\n', raw, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', raw)
    text = __import__('html').unescape(text)
    return '\n'.join(l.strip() for l in text.split('\n') if l.strip())

def parse_local_list(body: str) -> list:
    """Parse Google local search (tbm=lcl) results."""
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    entries = []
    rating_re = re.compile(r'^[1-5]\.[0-9]$')
    reviews_re = re.compile(r'^\(([\d,]+)\)$')
    rating_inline_re = re.compile(r'^([1-5]\.[0-9])\s*\(?([\d,]*)\)?\s*[·\-]')
    ui_skip = {"accessibility", "skip to", "sign in", "filters", "ai mode",
               "images", "forums", "places", "short videos", "more", "tools",
               "open now", "top rated", "small business", "search results",
               "delete", "see more", "google search", "send feedback"}

    i = 0
    while i < len(lines) and len(entries) < 20:
        line = lines[i]
        ll = line.lower()
        if (any(s in ll for s in ui_skip) or ll in {"all", "maps", "more", "(", ")"}
                or rating_inline_re.match(line) or rating_re.match(line)
                or reviews_re.match(line)
                or re.match(r'^(Open|Closed|Opens|Closes|·|")', line)):
            i += 1
            continue
        # Name then rating
        if i + 1 < len(lines):
            if rating_inline_re.match(lines[i + 1]):
                m = rating_inline_re.match(lines[i + 1])
                entries.append({"name": line, "rating": m.group(1), "reviews": m.group(2)})
                i += 5; continue
            if rating_re.match(lines[i + 1]):
                rating = lines[i + 1]
                reviews = ""
                advance = 2
                if i + 2 < len(lines):
                    rm = reviews_re.match(lines[i + 2])
                    if rm:
                        reviews = rm.group(1)
                        advance = 3
                entries.append({"name": line, "rating": rating, "reviews": reviews})
                i += advance + 2; continue
        i += 1
    return entries

def parse_organic(body: str) -> list:
    """Parse organic SERP results from text."""
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    results = []
    seen = set()
    url_re = re.compile(r'^(https?://)?(www\.)?([a-z0-9-]+\.)+[a-z]{2,12}(/[^\s]*)?(\s*[›>].*)?$', re.IGNORECASE)
    domain_re = re.compile(r'^(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)', re.IGNORECASE)
    skip = ("google.com/search", "google.com/maps", "support.google", "accounts.google")

    for i, line in enumerate(lines):
        if not url_re.match(line): continue
        if any(s in line.lower() for s in skip): continue
        m = domain_re.match(line)
        if not m: continue
        domain = m.group(1).lower()
        if domain in seen: continue
        seen.add(domain)
        title = ""
        for j in range(i - 1, max(-1, i - 4), -1):
            prev = lines[j]
            if url_re.match(prev): continue
            if len(prev) >= 5 and len(prev) <= 200:
                title = prev; break
        results.append({"title": title, "url": line, "domain": domain})
        if len(results) >= 20: break
    return results

def matches_biz(text: str, match_names: list, match_domains: list) -> bool:
    t = text.lower()
    for n in match_names:
        if n.lower() in t: return True
    for d in match_domains:
        if d.lower() in t: return True
    return False

def run():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)

    biz = config["businesses"]["custom_designs_tx"]
    match_names = biz["match_names"]
    match_domains = biz["match_domains"]
    keywords = biz["keywords"]
    today = date.today().isoformat()

    # Load existing state
    state = {}
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)

    biz_state = state.get("custom_designs_tx", {})

    print(f"[Custom Designs TX] {len(keywords)} keywords — using Bright Data SERP API\n")

    results = []
    for idx, kw in enumerate(keywords):
        print(f"  [{idx+1}/{len(keywords)}] {kw} ...", end=" ", flush=True)

        # Step 1: Local pack search
        local_body = fetch_serp(kw, tbm="lcl")
        if not local_body:
            print("BD FAIL")
            results.append((kw, {"error": "BD API failed"}))
            time.sleep(2)
            continue

        local_text = strip_html(local_body)
        local_entries = parse_local_list(local_text)

        our_map_pos = None
        our_maps_pos = None
        for i, e in enumerate(local_entries):
            if matches_biz(e.get("name", ""), match_names, match_domains):
                if i < 3 and our_map_pos is None:
                    our_map_pos = i + 1
                if our_maps_pos is None:
                    our_maps_pos = i + 1

        top3_map = [
            {"name": e.get("name", ""), "rating": e.get("rating", ""),
             "is_ours": matches_biz(e.get("name", ""), match_names, match_domains)}
            for e in local_entries[:3]
        ]

        # Step 2: Organic SERP
        our_org_pos = None
        top3_org = []
        if our_maps_pos is None:
            time.sleep(1.5)
            org_body = fetch_serp(kw)
            if org_body:
                org_text = strip_html(org_body)
                org_entries = parse_organic(org_text)
                for i, e in enumerate(org_entries):
                    check = f"{e.get('title','')} {e.get('domain','')}"
                    if our_org_pos is None and matches_biz(check, match_names, match_domains):
                        our_org_pos = i + 1
                top3_org = [
                    {"title": e.get("title", ""), "url": e.get("url", ""),
                     "is_ours": matches_biz(f"{e.get('title','')} {e.get('domain','')}", match_names, match_domains)}
                    for e in org_entries[:3]
                ]

        # Status
        if our_map_pos:
            status = f"3-pack #{our_map_pos}"
        elif our_maps_pos:
            status = f"maps #{our_maps_pos}"
        elif our_org_pos:
            status = f"organic #{our_org_pos}"
        else:
            status = "not found"
        print(status)

        snapshot = {
            "map_pack_position": our_map_pos,
            "maps_position": our_maps_pos,
            "organic_position": our_org_pos,
            "top3_map_pack": top3_map,
            "top3_maps_entries": [
                {"name": e.get("name", ""), "rating": e.get("rating", ""), "reviews": e.get("reviews", "")}
                for e in local_entries[:3]
            ],
            "top3_organic": top3_org,
            "error": None,
        }

        # Update state
        kw_history = biz_state.get(kw, {})
        kw_history[today] = snapshot
        dates = sorted(kw_history.keys())
        if len(dates) > 30:
            for old in dates[:-30]:
                del kw_history[old]
        biz_state[kw] = kw_history

        # Save incrementally every 10 keywords
        if (idx + 1) % 10 == 0:
            state["custom_designs_tx"] = biz_state
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print(f"  [saved {idx+1}/{len(keywords)}]")

        # Rate limit
        time.sleep(2.5 + __import__('random').random() * 2)

    # Final save
    state["custom_designs_tx"] = biz_state
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    # Summary
    found = sum(1 for d in biz_state.values()
                if today in d and (d[today].get("map_pack_position") or d[today].get("maps_position") or d[today].get("organic_position")))
    errors = sum(1 for d in biz_state.values() if today in d and d[today].get("error"))
    not_found = len(keywords) - found - errors
    print(f"\n{'='*50}")
    print(f"Done. {len(keywords)} keywords: {found} found, {not_found} not found, {errors} errors")
    print(f"State saved to: {STATE_PATH}")

if __name__ == "__main__":
    run()
