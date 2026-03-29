#!/usr/bin/env python3
"""
screenpipe_audio_miner.py — Mine audio transcriptions for client insights and action items.

Screenpipe records and transcribes all audio (microphone + system). This pipe
extracts client-relevant mentions, strategy ideas, and action items from those
transcriptions — data that was previously captured but never analyzed.

Usage:
  python screenpipe_audio_miner.py                       # last 24 hours
  python screenpipe_audio_miner.py --hours 8             # last 8 hours
  python screenpipe_audio_miner.py --client sugar_shack  # filter to one client
  python screenpipe_audio_miner.py --telegram            # send summary to Telegram
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

# Same client keywords as idea_scout for consistency
CLIENT_KEYWORDS = {
    "sugar_shack": ["sugar shack", "candy store", "candy shop", "south padre candy",
                    "spi candy", "sweets", "taffy", "fudge"],
    "island_arcade": ["island arcade", "arcade", "claw machine", "game room"],
    "island_candy": ["island candy", "ice cream", "frozen treats", "gelato", "shaved ice"],
    "juan": ["juan elizondo", "remax", "re/max", "real estate", "commercial property",
             "mls", "listing", "property", "mcallen"],
    "spi_fun_rentals": ["spi fun rentals", "golf cart", "beach rental", "rentals"],
    "custom_designs_tx": ["custom designs", "security camera", "alarm", "home theater",
                          "surveillance", "cctv", "cable routing"],
    "optimum_clinic": ["optimum clinic", "optimum health", "cash clinic", "night clinic",
                       "walk-in", "urgent care", "sick visit"],
    "optimum_foundation": ["optimum foundation", "wound care", "nonprofit", "regenerative",
                           "health foundation"],
}

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

# Action item trigger phrases
ACTION_TRIGGERS = [
    "i need to", "we need to", "i want to", "we should",
    "don't forget", "make sure", "remind me", "todo",
    "let's do", "have to", "got to", "gotta",
    "schedule", "deadline", "by friday", "by monday",
    "by tomorrow", "by next week", "this week",
]

# Strategy/insight trigger phrases
STRATEGY_TRIGGERS = [
    "the strategy", "our angle", "competitor", "they're doing",
    "ad copy", "campaign", "marketing", "engagement",
    "facebook", "google business", "reviews", "seo",
    "content", "blog post", "image", "video",
    "target audience", "demographic", "spring break",
    "tourist", "local", "bilingual",
]


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
    text_lower = text.lower()
    matches = []
    for client, keywords in CLIENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matches.append(client)
    return matches


def _extract_action_items(text: str) -> list:
    """Find sentences that look like action items."""
    items = []
    text_lower = text.lower()
    for trigger in ACTION_TRIGGERS:
        idx = text_lower.find(trigger)
        if idx >= 0:
            # Grab the sentence containing the trigger
            start = max(0, text_lower.rfind(".", 0, idx) + 1)
            end = text_lower.find(".", idx)
            if end < 0:
                end = min(len(text), idx + 150)
            sentence = text[start:end].strip()
            if len(sentence) > 15:
                items.append(sentence)
    return items


def _has_strategy_content(text: str) -> bool:
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in STRATEGY_TRIGGERS)


# ─── Main Mining Logic ──────────────────────────────────────────────────────

def run_audio_miner(hours_back: int = 24, client_filter: str = None,
                    send_telegram: bool = False) -> str:
    """Mine audio transcriptions for client insights and action items."""

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)

    print(f"Audio Miner — scanning last {hours_back} hours of transcriptions")
    print(f"  Period: {start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%H:%M')} UTC")

    # Fetch audio transcriptions
    print("  Fetching audio data...", end=" ")
    results = _api_get("/search", {
        "content_type": "audio",
        "limit": "500",
        "start_time": _iso(start),
        "end_time": _iso(now),
        "min_length": "20",
    })
    audio_data = results.get("data", []) if results else []
    print(f"{len(audio_data)} segments")

    if not audio_data:
        print("  No audio transcriptions found in this period.")
        return "No audio data available."

    # Analyze each segment
    client_mentions = defaultdict(list)   # {client: [{text, time, speaker}]}
    action_items = []                     # [{text, time, clients}]
    strategy_notes = []                   # [{text, time, clients}]
    speaker_counter = Counter()
    total_duration_sec = 0

    for item in audio_data:
        content = item.get("content", {})
        # Audio uses "transcription" field, not "text"
        text = content.get("transcription", "") or content.get("text", "")
        timestamp = content.get("timestamp", "")
        speaker_info = content.get("speaker", {})
        speaker = speaker_info.get("name", "") if isinstance(speaker_info, dict) else "Unknown"
        if not speaker:
            speaker = content.get("device_name", "Unknown")
        # Duration from start_time/end_time fields
        start_t = content.get("start_time", 0) or 0
        end_t = content.get("end_time", 0) or 0
        duration = max(0, end_t - start_t)

        if not text or len(text.strip()) < 15:
            continue

        total_duration_sec += duration
        speaker_counter[speaker] += 1

        # Tag to clients
        clients = _tag_client(text)
        for c in clients:
            if client_filter and c != client_filter:
                continue
            client_mentions[c].append({
                "text": text[:300],
                "time": timestamp,
                "speaker": speaker,
            })

        # Extract action items
        actions = _extract_action_items(text)
        for action in actions:
            action_items.append({
                "text": action,
                "time": timestamp,
                "clients": clients,
            })

        # Flag strategy-relevant segments
        if _has_strategy_content(text):
            strategy_notes.append({
                "text": text[:400],
                "time": timestamp,
                "clients": clients,
                "speaker": speaker,
            })

    # Generate report
    today_str = now.strftime("%Y-%m-%d")
    total_min = total_duration_sec / 60
    lines = [
        "# Audio Intelligence Report",
        f"**Period:** last {hours_back} hours ({start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%H:%M')} UTC)",
        f"**Audio segments analyzed:** {len(audio_data)}",
        f"**Total audio duration:** {total_min:.0f} minutes",
        "",
    ]

    # Speakers
    if speaker_counter:
        lines += ["## Speakers Detected", ""]
        for speaker, count in speaker_counter.most_common(10):
            lines.append(f"- **{speaker}**: {count} segments")
        lines.append("")

    # Action items
    if action_items:
        lines += ["## Action Items Detected", ""]
        seen = set()
        for item in action_items[:20]:
            short = item["text"][:150].strip()
            if short.lower() not in seen:
                seen.add(short.lower())
                client_tags = ", ".join(BUSINESS_NAMES.get(c, c) for c in item["clients"]) if item["clients"] else "general"
                lines.append(f"- [{client_tags}] {short}")
        lines.append("")
    else:
        lines += ["## Action Items Detected", "", "None found in this period.", ""]

    # Client mentions from voice
    if client_mentions:
        lines += ["## Client Mentions in Audio", ""]
        for client in sorted(client_mentions.keys()):
            if client_filter and client != client_filter:
                continue
            name = BUSINESS_NAMES.get(client, client)
            mentions = client_mentions[client]
            lines.append(f"### {name} ({len(mentions)} voice mentions)")
            lines.append("")
            seen = set()
            for m in mentions[:5]:
                short = m["text"][:200].replace("\n", " ").strip()
                if short[:50].lower() not in seen:
                    seen.add(short[:50].lower())
                    lines.append(f"- [{m['speaker']}] {short}")
            lines.append("")
    else:
        lines += ["## Client Mentions in Audio", "", "No client-specific audio detected.", ""]

    # Strategy notes
    if strategy_notes:
        lines += ["## Strategy & Marketing Notes", ""]
        seen = set()
        for note in strategy_notes[:15]:
            short = note["text"][:250].replace("\n", " ").strip()
            if short[:50].lower() not in seen:
                seen.add(short[:50].lower())
                client_tags = ", ".join(BUSINESS_NAMES.get(c, c) for c in note["clients"]) if note["clients"] else "general"
                lines.append(f"- [{client_tags}] {short}")
        lines.append("")

    # Summary
    lines += [
        "## Summary",
        f"- **Audio segments:** {len(audio_data)}",
        f"- **Duration:** {total_min:.0f} min",
        f"- **Client mentions:** {sum(len(v) for v in client_mentions.values())} across {len(client_mentions)} clients",
        f"- **Action items found:** {len(action_items)}",
        f"- **Strategy notes:** {len(strategy_notes)}",
        "",
    ]

    report = "\n".join(lines)

    # Save
    day_dir = REPORTS_DIR / today_str
    day_dir.mkdir(parents=True, exist_ok=True)
    report_path = day_dir / "audio-miner.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n  Saved: {report_path}")

    # Also save HTML
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Audio Intelligence — {today_str}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
h2 {{ color: #79c0ff; margin-top: 30px; }}
h3 {{ color: #d2a8ff; }}
li {{ margin-bottom: 8px; line-height: 1.5; }}
strong {{ color: #e6edf3; }}
code {{ background: #161b22; padding: 2px 6px; border-radius: 4px; }}
</style></head><body>
{"<br>".join(f"<p>{line}</p>" if not line.startswith("#") else f"<h{line.count('#')}>{line.lstrip('#').strip()}</h{line.count('#')}>" for line in lines if line)}
</body></html>"""
    html_path = day_dir / "audio-miner.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  Saved: {html_path}")

    if send_telegram:
        summary_lines = [l for l in lines if l.startswith("- **") or l.startswith("# ")][:15]
        _notify_mario(f"Audio Intelligence Report\n\n" + "\n".join(summary_lines))
        print("  Sent to Telegram")

    return report


def main():
    parser = argparse.ArgumentParser(description="Screenpipe Audio Miner — extract insights from voice transcriptions")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--telegram", action="store_true", help="Send summary to Telegram")
    parser.add_argument("--client", choices=list(CLIENT_KEYWORDS.keys()),
                        help="Filter to a specific client")
    args = parser.parse_args()

    if not _healthy():
        print("Screenpipe is not running. Start it first.")
        sys.exit(1)

    run_audio_miner(hours_back=args.hours, client_filter=args.client,
                    send_telegram=args.telegram)


if __name__ == "__main__":
    main()
