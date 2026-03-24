#!/usr/bin/env python3
"""
screenpipe_pipe_runner.py — Run Screenpipe analysis pipes via REST API.

Queries Screenpipe's local API (localhost:3030) to generate activity reports
matching the pipe templates in ~/.screenpipe/pipes/.

Usage:
  python screenpipe_pipe_runner.py time-breakdown      # app usage breakdown
  python screenpipe_pipe_runner.py day-recap            # what you accomplished today
  python screenpipe_pipe_runner.py top-of-mind          # recurring topics/focus areas
  python screenpipe_pipe_runner.py ai-habits            # AI tool usage patterns
  python screenpipe_pipe_runner.py --daily              # all 4 above
  python screenpipe_pipe_runner.py --daily --telegram   # all 4 + send summary to Telegram
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

# App categories for time-breakdown
APP_CATEGORIES = {
    "coding": ["Antigravity.exe", "Code.exe", "code.exe", "WindowsTerminal.exe",
               "cmd.exe", "powershell.exe", "pwsh.exe", "node.exe", "python.exe"],
    "browsing": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"],
    "communication": ["Discord.exe", "Telegram.exe", "slack.exe", "Teams.exe",
                      "Zoom.exe", "WhatsApp.exe"],
    "ai_tools": ["claude.exe", "Antigravity.exe"],
    "system": ["explorer.exe", "Taskmgr.exe", "SearchHost.exe",
               "StartMenuExperienceHost.exe", "ShellExperienceHost.exe",
               "SystemSettings.exe", "ApplicationFrameHost.exe"],
}

# AI tool OCR keywords for ai-habits
AI_TOOL_KEYWORDS = {
    "Claude Code": ["claude.exe", "Claude Code"],
    "Antigravity (VS Code)": ["Antigravity.exe"],
    "ChatGPT": ["ChatGPT", "chat.openai.com"],
    "Gemini": ["Gemini", "gemini.google.com"],
    "Perplexity": ["Perplexity", "perplexity.ai"],
    "Copilot": ["GitHub Copilot", "Copilot"],
}

# Frame interval in seconds (Screenpipe captures at ~0.27 FPS)
FRAME_INTERVAL_SEC = 4


# ─── Helpers ────────────────────────────────────────────────────────────────

def _api_get(path: str, params: dict = None) -> dict | list | None:
    url = f"{SCREENPIPE_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  [API GET error: {e}]")
        return None


def _api_post(path: str, body: dict) -> dict | list | None:
    url = f"{SCREENPIPE_BASE}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  [API POST error: {e}]")
        return None


def _healthy() -> bool:
    result = _api_get("/health")
    return result is not None and result.get("status") == "healthy"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _categorize_app(app_name: str) -> str:
    for category, apps in APP_CATEGORIES.items():
        if app_name in apps:
            return category
    return "other"


def _save_report(pipe_name: str, content: str, today_str: str):
    day_dir = REPORTS_DIR / today_str
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{pipe_name}.md"
    path.write_text(content, encoding="utf-8")
    print(f"  Saved: {path}")
    return path


def _notify_mario(text: str) -> bool:
    try:
        from screenpipe_verifier import notify_mario
        return notify_mario(text)
    except ImportError:
        return False


# ─── Pipe: time-breakdown ───────────────────────────────────────────────────

def run_time_breakdown(start: datetime, end: datetime) -> str:
    """App usage breakdown with categories and productivity score."""
    print("  Running time-breakdown...")

    start_str = _iso(start)
    end_str = _iso(end)

    rows = _api_post("/raw_sql", {
        "query": f"SELECT app_name, COUNT(*) as frame_count FROM frames "
                 f"WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}' "
                 f"AND app_name != '' "
                 f"GROUP BY app_name ORDER BY frame_count DESC LIMIT 30"
    })

    if not rows:
        return "# Time Breakdown\n\nNo data available for this period.\n"

    total_frames = sum(r["frame_count"] for r in rows)
    total_minutes = total_frames * FRAME_INTERVAL_SEC / 60

    # By application
    lines = [
        "# Time Breakdown",
        f"**Period:** {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')} UTC",
        f"**Total tracked time:** {total_minutes:.0f} minutes ({total_minutes/60:.1f} hours)",
        "",
        "## By Application",
        "",
    ]

    for r in rows:
        app = r["app_name"]
        frames = r["frame_count"]
        minutes = frames * FRAME_INTERVAL_SEC / 60
        pct = (frames / total_frames * 100) if total_frames else 0
        bar = "#" * max(1, int(pct / 3))
        lines.append(f"- **{app}**: {minutes:.0f} min ({pct:.1f}%) {bar}")

    # By category
    cat_totals = defaultdict(int)
    for r in rows:
        cat = _categorize_app(r["app_name"])
        cat_totals[cat] += r["frame_count"]

    lines += ["", "## By Category", ""]
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    for cat, frames in sorted_cats:
        minutes = frames * FRAME_INTERVAL_SEC / 60
        pct = (frames / total_frames * 100) if total_frames else 0
        lines.append(f"- **{cat}**: {minutes:.0f} min ({pct:.1f}%)")

    # Productivity score
    productive_cats = {"coding", "ai_tools"}
    productive_frames = sum(cat_totals.get(c, 0) for c in productive_cats)
    productivity = (productive_frames / total_frames * 100) if total_frames else 0
    lines += [
        "",
        "## Productivity Score",
        f"**{productivity:.0f}%** (coding + AI tools vs total tracked time)",
        "",
    ]

    return "\n".join(lines)


# ─── Pipe: day-recap ────────────────────────────────────────────────────────

def run_day_recap(start: datetime, end: datetime) -> str:
    """Summary of accomplishments and where you left off."""
    print("  Running day-recap...")

    start_str = _iso(start)
    end_str = _iso(end)

    # Get app+window activity
    rows = _api_post("/raw_sql", {
        "query": f"SELECT app_name, window_name, COUNT(*) as frame_count "
                 f"FROM frames "
                 f"WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}' "
                 f"AND app_name != '' AND window_name != '' "
                 f"GROUP BY app_name, window_name "
                 f"ORDER BY frame_count DESC LIMIT 25"
    })

    if not rows:
        return "# Day Recap\n\nNo activity data available for this period.\n"

    # Get the last few frames (where you left off)
    last_rows = _api_post("/raw_sql", {
        "query": f"SELECT app_name, window_name, timestamp FROM frames "
                 f"WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}' "
                 f"AND app_name != '' "
                 f"ORDER BY timestamp DESC LIMIT 5"
    })

    lines = [
        "# Day Recap",
        f"**Period:** {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
    ]

    # Where you left off
    if last_rows:
        last = last_rows[0]
        lines += [
            "## Where You Left Off",
            f"- **App:** {last.get('app_name', '?')}",
            f"- **Window:** {last.get('window_name', '?')[:100]}",
            f"- **Time:** {last.get('timestamp', '?')}",
            "",
        ]

    # Top activities (accomplishments proxy)
    lines += ["## Top Activities (by time spent)", ""]
    for i, r in enumerate(rows[:10], 1):
        app = r.get("app_name", "?")
        window = r.get("window_name", "?")[:80]
        minutes = r.get("frame_count", 0) * FRAME_INTERVAL_SEC / 60
        lines.append(f"{i}. **{app}** — {window} ({minutes:.0f} min)")

    # Unique windows touched
    unique_windows = len(set(r.get("window_name", "") for r in rows))
    lines += [
        "",
        f"**Unique windows/tasks:** {unique_windows}",
        "",
    ]

    return "\n".join(lines)


# ─── Pipe: top-of-mind ──────────────────────────────────────────────────────

def run_top_of_mind(start: datetime, end: datetime) -> str:
    """Recurring topics from OCR text in the last 8 hours."""
    print("  Running top-of-mind...")

    # Use search API for OCR content
    results = _api_get("/search", {
        "content_type": "ocr",
        "limit": "200",
        "start_time": _iso(start),
        "end_time": _iso(end),
    })

    data = results.get("data", []) if results else []

    if not data:
        return "# Top of Mind\n\nNo OCR data available for this period.\n"

    # Extract meaningful words from OCR text
    noise_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
        "her", "was", "one", "our", "out", "has", "his", "how", "its", "may",
        "new", "now", "old", "see", "way", "who", "did", "get", "let", "say",
        "she", "too", "use", "from", "have", "been", "this", "that", "with",
        "they", "will", "each", "make", "like", "just", "over", "such", "take",
        "than", "them", "very", "when", "what", "your", "into", "some", "could",
        "other", "about", "which", "their", "there", "would", "these", "more",
        # OS/UI noise
        "minimize", "restore", "close", "file", "edit", "view", "help", "search",
        "open", "save", "copy", "paste", "ctrl", "shift", "alt", "tab",
        "window", "menu", "button", "click", "page", "home", "end",
        "http", "https", "www", "com", "html", "json", "null", "true", "false",
    }

    word_counter = Counter()
    app_topics = defaultdict(Counter)

    for item in data:
        content = item.get("content", {})
        text = content.get("text", "")
        app = content.get("app_name", "unknown")

        # Extract words (3+ chars, alpha)
        words = [w.lower() for w in text.split() if len(w) >= 3 and w.isalpha()]
        meaningful = [w for w in words if w not in noise_words]
        word_counter.update(meaningful)
        app_topics[app].update(meaningful)

    # Find recurring topics (appearing 3+ times)
    recurring = [(word, count) for word, count in word_counter.most_common(50)
                 if count >= 3]

    lines = [
        "# Top of Mind",
        f"**Period:** last {int((end - start).total_seconds() / 3600)} hours",
        f"**OCR frames analyzed:** {len(data)}",
        "",
        "## Recurring Topics (3+ appearances)",
        "",
    ]

    if recurring:
        for word, count in recurring[:20]:
            lines.append(f"- **{word}** ({count} mentions)")
    else:
        lines.append("- No strongly recurring topics found.")

    # Focus areas by app
    lines += ["", "## Focus Areas by App", ""]
    for app, counter in sorted(app_topics.items(), key=lambda x: sum(x[1].values()), reverse=True)[:5]:
        top_words = [w for w, _ in counter.most_common(5) if w not in noise_words]
        if top_words:
            lines.append(f"- **{app}**: {', '.join(top_words)}")

    lines.append("")
    return "\n".join(lines)


# ─── Pipe: ai-habits ────────────────────────────────────────────────────────

def run_ai_habits(start: datetime, end: datetime) -> str:
    """Track AI tool usage patterns."""
    print("  Running ai-habits...")

    start_str = _iso(start)
    end_str = _iso(end)

    # Get time per known AI-related app
    ai_apps = ["Antigravity.exe", "claude.exe"]
    in_clause = ",".join(f"'{a}'" for a in ai_apps)
    app_rows = _api_post("/raw_sql", {
        "query": f"SELECT app_name, COUNT(*) as frame_count FROM frames "
                 f"WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}' "
                 f"AND app_name IN ({in_clause}) "
                 f"GROUP BY app_name ORDER BY frame_count DESC LIMIT 20"
    })

    # Search OCR for browser-based AI tools
    browser_ai = {}
    for tool_name, keywords in AI_TOOL_KEYWORDS.items():
        if tool_name in ("Claude Code", "Antigravity (VS Code)"):
            continue  # Already counted via app_name
        for kw in keywords:
            results = _api_get("/search", {
                "q": kw,
                "content_type": "ocr",
                "limit": "50",
                "start_time": _iso(start),
                "end_time": _iso(end),
                "app_name": "chrome.exe",
            })
            hits = len(results.get("data", [])) if results else 0
            if hits > 0:
                browser_ai[tool_name] = browser_ai.get(tool_name, 0) + hits

    total_frames = _api_post("/raw_sql", {
        "query": f"SELECT COUNT(*) as total FROM frames "
                 f"WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}' LIMIT 1"
    })
    total = total_frames[0]["total"] if total_frames else 1

    lines = [
        "# AI Habits",
        f"**Period:** {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "## AI Tools Used (by screen time)",
        "",
    ]

    if app_rows:
        for r in app_rows:
            app = r["app_name"]
            frames = r["frame_count"]
            minutes = frames * FRAME_INTERVAL_SEC / 60
            pct = (frames / total * 100) if total else 0
            tool_name = "Antigravity (VS Code)" if app == "Antigravity.exe" else "Claude Code"
            lines.append(f"- **{tool_name}**: {minutes:.0f} min ({pct:.1f}% of total screen time)")

    if browser_ai:
        lines += ["", "## Browser-Based AI Tools (OCR detections)", ""]
        for tool, hits in sorted(browser_ai.items(), key=lambda x: x[1], reverse=True):
            est_min = hits * FRAME_INTERVAL_SEC / 60
            lines.append(f"- **{tool}**: ~{est_min:.0f} min ({hits} screen appearances)")

    # AI as % of total
    ai_frames = sum(r["frame_count"] for r in (app_rows or []))
    ai_pct = (ai_frames / total * 100) if total else 0
    lines += [
        "",
        "## Summary",
        f"- **AI tool time:** {ai_frames * FRAME_INTERVAL_SEC / 60:.0f} min ({ai_pct:.0f}% of total)",
        f"- **Total tracked time:** {total * FRAME_INTERVAL_SEC / 60:.0f} min",
        "",
    ]

    return "\n".join(lines)


# ─── Generate HTML wrapper ──────────────────────────────────────────────────

def generate_html(title: str, markdown_content: str, today_str: str) -> str:
    """Wrap markdown report in a dark-themed HTML page."""
    # Simple markdown-to-HTML conversion for our structured output
    html_body = ""
    for line in markdown_content.split("\n"):
        line = line.rstrip()
        if line.startswith("# "):
            html_body += f'<h1 style="color:#e6edf3;font-size:24px;margin:24px 0 8px">{line[2:]}</h1>\n'
        elif line.startswith("## "):
            html_body += f'<h2 style="color:#e6edf3;font-size:17px;margin:20px 0 10px;border-bottom:1px solid #30363d;padding-bottom:6px">{line[3:]}</h2>\n'
        elif line.startswith("- **"):
            # Bold item in list
            html_body += f'<div style="margin:4px 0;padding:4px 0;color:#c9d1d9;font-size:14px">{_md_bold(line[2:])}</div>\n'
        elif line.startswith("- "):
            html_body += f'<div style="margin:4px 0;padding:4px 0;color:#c9d1d9;font-size:14px">{line[2:]}</div>\n'
        elif line.startswith("**"):
            html_body += f'<p style="color:#c9d1d9;font-size:14px;margin:8px 0">{_md_bold(line)}</p>\n'
        elif line.strip().startswith(tuple(str(i) + "." for i in range(1, 20))):
            html_body += f'<div style="margin:4px 0;padding:4px 0;color:#c9d1d9;font-size:14px">{_md_bold(line)}</div>\n'
        elif line.strip():
            html_body += f'<p style="color:#8b949e;font-size:13px;margin:4px 0">{line}</p>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — {today_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding: 24px; }}
  .container {{ max-width: 860px; margin: 0 auto; }}
</style>
</head>
<body>
<div class="container">
{html_body}
</div>
</body>
</html>"""


def _md_bold(text: str) -> str:
    """Convert **bold** markdown to <strong> tags."""
    import re
    return re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#e6edf3">\1</strong>', text)


# ─── Main ───────────────────────────────────────────────────────────────────

PIPES = {
    "time-breakdown": run_time_breakdown,
    "day-recap": run_day_recap,
    "top-of-mind": run_top_of_mind,
    "ai-habits": run_ai_habits,
}

DAILY_PIPES = ["time-breakdown", "day-recap", "top-of-mind", "ai-habits"]


def run_pipe(pipe_name: str, hours_back: int = 16, send_telegram: bool = False) -> str | None:
    """Run a single pipe and save the report."""
    if pipe_name not in PIPES:
        print(f"  Unknown pipe: {pipe_name}")
        print(f"  Available: {', '.join(PIPES.keys())}")
        return None

    now = _now_utc()
    start = now - timedelta(hours=hours_back)
    today_str = now.strftime("%Y-%m-%d")

    content = PIPES[pipe_name](start, now)

    # Save markdown
    report_path = _save_report(pipe_name, content, today_str)

    # Save HTML
    html = generate_html(pipe_name.replace("-", " ").title(), content, today_str)
    html_path = report_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML:  {html_path}")

    if send_telegram:
        # Send a compact summary to Telegram
        summary_lines = content.split("\n")[:15]
        summary = "\n".join(summary_lines)
        _notify_mario(f"Screenpipe {pipe_name}\n\n{summary}")

    return content


def main():
    parser = argparse.ArgumentParser(description="Run Screenpipe analysis pipes")
    parser.add_argument("pipe", nargs="?", choices=list(PIPES.keys()),
                        help="Pipe to run")
    parser.add_argument("--daily", action="store_true",
                        help="Run all 4 daily pipes")
    parser.add_argument("--hours", type=int, default=16,
                        help="Hours to look back (default: 16)")
    parser.add_argument("--telegram", action="store_true",
                        help="Send summary to Telegram")
    args = parser.parse_args()

    if not args.pipe and not args.daily:
        parser.print_help()
        sys.exit(1)

    if not _healthy():
        print("Screenpipe is not running. Start it first.")
        sys.exit(1)

    print(f"Screenpipe Pipe Runner — {_now_utc().strftime('%Y-%m-%d %H:%M UTC')}")

    if args.daily:
        pipes_to_run = DAILY_PIPES
    else:
        pipes_to_run = [args.pipe]

    all_content = []
    for pipe_name in pipes_to_run:
        print(f"\n[{pipe_name}]")
        content = run_pipe(pipe_name, hours_back=args.hours, send_telegram=args.telegram)
        if content:
            all_content.append(content)

    # If daily + telegram, send a combined summary
    if args.daily and args.telegram and all_content:
        combined = "\n---\n".join(c.split("\n")[0] for c in all_content)
        _notify_mario(f"Daily Screenpipe Report\n\n{combined}")

    print(f"\nDone. Reports in: {REPORTS_DIR / _now_utc().strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    main()
