#!/usr/bin/env python3
"""
screenpipe_idea_scout.py — Competitor intelligence from browsing activity.

Adapted from Screenpipe's idea-tracker pipe template, tuned for Mario's
8-client marketing agency. Watches browsing/screen activity and tags insights
to specific clients.

Queries Screenpipe OCR data for business-relevant browsing (Facebook Ad Library,
Google Maps, competitor sites, Yelp, industry blogs), cross-references with
the 8 client keywords, and outputs actionable ideas per client.

Usage:
  python screenpipe_idea_scout.py                    # last 8 hours
  python screenpipe_idea_scout.py --hours 24         # last 24 hours
  python screenpipe_idea_scout.py --telegram         # send summary to Telegram
  python screenpipe_idea_scout.py --client sugar_shack  # filter to one client
"""

import sys
import json
import argparse
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCREENPIPE_BASE = "http://localhost:3030"
EXECUTION_DIR = Path(__file__).parent
REPORTS_DIR = EXECUTION_DIR / "screenpipe_reports"

# Client search terms — keywords that indicate browsing related to a client
CLIENT_KEYWORDS = {
    "sugar_shack": ["sugar shack", "candy store", "candy shop", "south padre candy",
                    "spi candy", "sweets shop", "taffy", "fudge shop"],
    "island_arcade": ["island arcade", "arcade spi", "south padre arcade",
                      "game room", "claw machine", "arcade games"],
    "island_candy": ["island candy", "ice cream spi", "ice cream south padre",
                     "frozen treats", "gelato", "shaved ice"],
    "juan": ["juan elizondo", "remax elite", "re/max", "real estate mcallen",
             "rgv real estate", "commercial property", "mls listing",
             "property for sale mcallen", "edinburg homes"],
    "spi_fun_rentals": ["spi fun rentals", "golf cart rental", "south padre rental",
                        "beach rental", "island rentals"],
    "custom_designs_tx": ["custom designs", "security camera", "alarm system",
                          "home theater", "cctv installation", "surveillance",
                          "audio video", "cable routing"],
    "optimum_clinic": ["optimum clinic", "optimum health", "cash clinic",
                       "night clinic", "walk-in clinic", "urgent care mcallen",
                       "sick visit"],
    "optimum_foundation": ["optimum foundation", "wound care", "nonprofit health",
                           "regenerative", "health foundation"],
}

# Business-relevant URL/page title patterns
BUSINESS_SIGNALS = [
    "facebook.com/ads/library",
    "facebook.com/profile",
    "google.com/maps",
    "yelp.com",
    "tripadvisor.com",
    "google.com/search",
    "zillow.com",
    "realtor.com",
    "loopnet.com",
    "homeadvisor.com",
    "bbb.org",
    "Ad Library",
    "Google Maps",
    "Yelp",
    "TripAdvisor",
    "Reviews",
]

BUSINESS_NAMES = {
    "sugar_shack": "The Sugar Shack",
    "island_arcade": "Island Arcade",
    "island_candy": "Island Candy",
    "juan": "Juan Elizondo RE/MAX",
    "spi_fun_rentals": "SPI Fun Rentals",
    "custom_designs_tx": "Custom Designs TX",
    "optimum_clinic": "Optimum Clinic",
    "optimum_foundation": "Optimum Foundation",
}

# ─── Noise Filters ─────────────────────────────────────────────────────────
# OUR OWN TOOLS — always noise, no exceptions (they contain all client names)
ALWAYS_NOISE_PATTERNS = [
    "genspark.ai/claw", "genspark.ai/spark", "openclaw",
    "antigravity-dashboard", "missioncontrol", "mission-control",
    "vscode-file://", "vscode-app",
    "screenpipe_pipe_runner", "screenpipe_idea_scout",  # our own scripts in terminal
]

# Generic internal URLs — noise unless they also contain a business signal
NOISE_UNLESS_BUSINESS = [
    "localhost", "127.0.0.1",
    "file:///", "chrome://", "edge://", "about:blank",
    "claude.ai", "chatgpt.com", "gemini.google.com",
]

# Window chrome text that OCR captures from every window frame — strip from snippets
WINDOW_CHROME_PREFIX = [
    "Minimize Restore Close",
    "Back Forward Reload",
    "Open tab in split view",
    "View site information",
    "Bookmark this tab",
]

# Words that flood topic counts but carry zero competitive intel
NOISE_WORDS = {
    # Username / OS chrome
    "mario", "minimize", "restore", "close", "maximize",
    "undefined", "untitled", "loading", "electron",
    # Device / hardware names (from taskbar OCR)
    "headphones", "microphone", "webcam", "emeet", "virtual",
    "audio", "speakers", "realtek", "nvidia", "intel",
    # UI framework / CSS noise
    "style", "class", "width", "height", "color", "display",
    "padding", "margin", "border", "background", "function",
    "return", "const", "import", "export", "module", "undefined",
    "container", "wrapper", "component", "button", "input",
    # Common stop-words that slip past the simple filter
    "https", "about", "would", "their", "there", "which",
    "could", "other", "these", "those", "where", "while",
    "should", "through", "being", "after", "before", "between",
    "under", "above", "below", "every", "never", "always",
    "false", "value", "index", "error", "string", "number",
    "array", "object", "default", "params", "config",
    # Code/dev tool terms that flood OCR from IDE windows
    "files", "searching", "found", "result", "process",
    "write", "server", "access", "items", "tunnel",
    "mission", "control", "dashboard", "supabase",
    "running", "reading", "saving", "loading", "building",
    "script", "python", "typescript", "javascript",
    "token", "request", "response", "status", "debug",
}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _api_get(path: str, params: dict = None):
    url = f"{SCREENPIPE_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  [API error: {e}]")
        return None


def _healthy() -> bool:
    result = _api_get("/health")
    return result is not None and result.get("status") == "healthy"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _notify_mario(text: str) -> bool:
    try:
        from screenpipe_verifier import notify_mario
        return notify_mario(text)
    except ImportError:
        return False


def _tag_client(text: str) -> list:
    """Return list of client keys that match the given text."""
    text_lower = text.lower()
    matches = []
    for client, keywords in CLIENT_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            matches.append(client)
    return matches


def _clean_snippet(text: str) -> str:
    """Strip window chrome prefixes from OCR text for cleaner display."""
    clean = text
    for prefix in WINDOW_CHROME_PREFIX:
        clean = clean.replace(prefix, "")
    # Collapse multiple spaces
    while "  " in clean:
        clean = clean.replace("  ", " ")
    return clean.strip()


def _is_noise(text: str) -> bool:
    """Return True if this OCR text is internal tool noise, not real browsing."""
    text_lower = text.lower()
    # Our own tools — ALWAYS noise, no exceptions
    for pattern in ALWAYS_NOISE_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    # Generic internal URLs — noise unless they contain a real business signal
    for pattern in NOISE_UNLESS_BUSINESS:
        if pattern.lower() in text_lower:
            has_signal = any(s.lower() in text_lower for s in BUSINESS_SIGNALS)
            if not has_signal:
                return True
    # Skip very short or UI-chrome-only frames
    clean = text.replace("Minimize", "").replace("Restore", "").replace("Close", "").strip()
    if len(clean) < 40:
        return True
    return False


# ─── Main Scout Logic ───────────────────────────────────────────────────────

def run_idea_scout(hours_back: int = 8, client_filter: str = None,
                   send_telegram: bool = False) -> str:
    """Scan browsing activity for client-relevant insights."""

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)

    print(f"Idea Scout — scanning last {hours_back} hours")
    print(f"  Period: {start.strftime('%H:%M')} to {now.strftime('%H:%M')} UTC")

    # 1. Get browser OCR data
    print("  Fetching browser activity...", end=" ")
    browser_results = _api_get("/search", {
        "content_type": "ocr",
        "limit": "300",
        "start_time": _iso(start),
        "end_time": _iso(now),
        "app_name": "chrome.exe",
    })
    browser_data = browser_results.get("data", []) if browser_results else []
    print(f"{len(browser_data)} frames")

    # 2. Also check other apps for client mentions
    print("  Fetching all app activity...", end=" ")
    all_results = _api_get("/search", {
        "content_type": "ocr",
        "limit": "200",
        "start_time": _iso(start),
        "end_time": _iso(now),
    })
    all_data = all_results.get("data", []) if all_results else []
    print(f"{len(all_data)} frames")

    # 3. Extract insights
    client_mentions = defaultdict(list)  # {client: [text_snippets]}
    business_browsing = []  # [{text, app, time}]
    topic_counter = Counter()

    noise_skipped = 0
    for item in browser_data + all_data:
        content = item.get("content", {})
        text = content.get("text", "")
        app = content.get("app_name", "?")
        timestamp = content.get("timestamp", "")

        if not text or len(text) < 20:
            continue

        # NOISE FILTER: skip internal tool frames
        if _is_noise(text):
            noise_skipped += 1
            continue

        # Check for business-relevant browsing signals
        is_business = any(signal.lower() in text.lower() for signal in BUSINESS_SIGNALS)

        # Tag to clients
        clients = _tag_client(text)

        if clients or is_business:
            snippet = _clean_snippet(text[:300]).replace("\n", " ")[:200].strip()
            for c in clients:
                if client_filter and c != client_filter:
                    continue
                client_mentions[c].append({
                    "text": snippet,
                    "app": app,
                    "time": timestamp,
                })

            if is_business:
                business_browsing.append({
                    "text": snippet,
                    "app": app,
                    "time": timestamp,
                    "clients": clients,
                })

        # Track topics — only from non-noise, external-facing text
        for word in text.split():
            w = word.lower().strip(".,;:!?()[]{}\"'")
            if len(w) >= 5 and w.isalpha() and w not in NOISE_WORDS:
                topic_counter[w] += 1

    print(f"  Noise frames filtered: {noise_skipped}")

    # 4. Generate report
    today_str = now.strftime("%Y-%m-%d")
    lines = [
        "# Idea Scout Report",
        f"**Period:** last {hours_back} hours ({start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%H:%M')} UTC)",
        f"**Browser frames analyzed:** {len(browser_data)}",
        f"**Total frames analyzed:** {len(all_data)}",
        "",
    ]

    # Client-specific insights
    if client_mentions:
        lines += ["## Client-Tagged Insights", ""]
        for client in sorted(client_mentions.keys()):
            if client_filter and client != client_filter:
                continue
            name = BUSINESS_NAMES.get(client, client)
            mentions = client_mentions[client]
            lines.append(f"### {name} ({len(mentions)} mentions)")
            lines.append("")
            seen = set()
            for m in mentions[:8]:
                short = m["text"][:120]
                if short not in seen:
                    seen.add(short)
                    lines.append(f"- {short}")
            lines.append("")
    else:
        lines += ["## Client-Tagged Insights", "", "No client-specific browsing detected in this period.", ""]

    # Business-relevant browsing
    if business_browsing:
        lines += ["## Business-Relevant Browsing", ""]
        seen = set()
        for b in business_browsing[:15]:
            short = b["text"][:120]
            if short not in seen:
                seen.add(short)
                client_tags = ", ".join(BUSINESS_NAMES.get(c, c) for c in b["clients"]) if b["clients"] else "untagged"
                lines.append(f"- [{client_tags}] {short}")
        lines.append("")

    # Trending topics (noise words already filtered during counting)
    top_topics = [(w, c) for w, c in topic_counter.most_common(50)
                  if c >= 3 and w not in NOISE_WORDS]
    if top_topics:
        lines += ["## Trending Topics (from browsing)", ""]
        for word, count in top_topics[:15]:
            lines.append(f"- **{word}** ({count} mentions)")
        lines.append("")

    # Summary stats
    total_client_mentions = sum(len(v) for v in client_mentions.values())
    lines += [
        "## Summary",
        f"- **Client-tagged browsing:** {total_client_mentions} snippets across {len(client_mentions)} clients",
        f"- **Business-relevant pages:** {len(business_browsing)}",
        "",
    ]

    content = "\n".join(lines)

    # Save
    day_dir = REPORTS_DIR / today_str
    day_dir.mkdir(parents=True, exist_ok=True)
    report_path = day_dir / "idea-scout.md"
    report_path.write_text(content, encoding="utf-8")
    print(f"\n  Saved: {report_path}")

    if send_telegram:
        summary = "\n".join(lines[:20])
        _notify_mario(f"Idea Scout Report\n\n{summary}")
        print("  Sent to Telegram")

    return content


def main():
    parser = argparse.ArgumentParser(description="Screenpipe Idea Scout — competitor intelligence from browsing")
    parser.add_argument("--hours", type=int, default=8, help="Hours to look back (default: 8)")
    parser.add_argument("--telegram", action="store_true", help="Send summary to Telegram")
    parser.add_argument("--client", choices=list(CLIENT_KEYWORDS.keys()),
                        help="Filter to a specific client")
    args = parser.parse_args()

    if not _healthy():
        print("Screenpipe is not running. Start it first.")
        sys.exit(1)

    run_idea_scout(hours_back=args.hours, client_filter=args.client,
                   send_telegram=args.telegram)


if __name__ == "__main__":
    main()
