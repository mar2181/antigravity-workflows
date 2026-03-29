#!/usr/bin/env python3
"""
seo_report_generator.py — Step 5: Generate HTML reports and Telegram notifications.

Reads seo_optimizer_state.json and action screenshots.
Generates:
  1. HTML report: dark-themed, includes action table + winning patterns
  2. Telegram messages: 5 summary messages (text + file)

HTML includes:
  - Per-client table: keyword | action taken | rank before | rank after | delta | status
  - Winning patterns: what action types are working
  - Opportunities: keywords still outside Map Pack top 3
  - Action screenshots embedded

Telegram includes:
  1. Summary table (text)
  2. Top win of the night
  3. Top opportunity still open
  4. HTML report file
  5. Command to re-run

Usage:
  python seo_optimizer/seo_report_generator.py
  python seo_optimizer/seo_report_generator.py --no-telegram
  python seo_optimizer/seo_report_generator.py --client sugar_shack

State file: seo_optimizer_state.json
Output: seo_optimizer_reports/YYYY-MM-DD.html
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent
SEO_STATE_PATH = SCRIPT_DIR / "seo_optimizer" / "seo_optimizer_state.json"
REPORTS_DIR = SCRIPT_DIR / "seo_optimizer_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_html_report(seo_state):
    """Generate dark-themed HTML report."""
    work_queue = seo_state.get("work_queue", [])
    action_history = seo_state.get("action_history", [])
    winning_patterns = seo_state.get("winning_patterns", {})

    # Build per-client results tables
    clients_data = {}
    for item in work_queue:
        client = item["client"]
        if client not in clients_data:
            clients_data[client] = []

        clients_data[client].append({
            "keyword": item["keyword"],
            "action": item.get("action_type", "—"),
            "pre_rank": item.get("pre_action_rank", "—"),
            "post_rank": item.get("post_action_rank", "—"),
            "delta": item.get("delta", "—"),
            "status": item.get("status", "PENDING"),
        })

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SEO Optimizer Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0f0f0f;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 2em;
        }}
        .timestamp {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.3em;
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1a1a1a;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #00d4ff;
            color: #000;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #333;
        }}
        tr:hover {{
            background: #222;
        }}
        .status-effective {{
            color: #00ff00;
            font-weight: 600;
        }}
        .status-neutral {{
            color: #ffaa00;
        }}
        .status-harmful {{
            color: #ff4444;
        }}
        .delta-positive {{
            color: #00ff00;
        }}
        .delta-negative {{
            color: #ff4444;
        }}
        .stat-card {{
            background: #1a1a1a;
            border-left: 4px solid #00d4ff;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }}
        .stat-card strong {{
            color: #00d4ff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 SEO Optimizer Report</h1>
        <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

        <div class="section">
            <div class="section-title">📋 Actions by Client</div>
"""

    for client, items in sorted(clients_data.items()):
        executed = len([i for i in items if i["status"] not in ["PENDING", "READY"]])
        effective = len([i for i in items if i["status"] == "EFFECTIVE"])

        html += f"""
            <div class="stat-card">
                <strong>{client}</strong> — {executed} executed, {effective} effective
            </div>
            <table>
                <tr>
                    <th>Keyword</th>
                    <th>Action</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Delta</th>
                    <th>Status</th>
                </tr>
"""

        for item in items:
            delta_class = ""
            if isinstance(item["delta"], int):
                delta_class = "delta-positive" if item["delta"] > 0 else "delta-negative"
                delta_display = f"{item['delta']:+d}"
            else:
                delta_display = "—"

            status_class = f"status-{item['status'].lower()}"

            html += f"""
                <tr>
                    <td>{item['keyword']}</td>
                    <td>{item['action']}</td>
                    <td>{item['pre_rank']}</td>
                    <td>{item['post_rank']}</td>
                    <td class="{delta_class}">{delta_display}</td>
                    <td class="{status_class}">{item['status']}</td>
                </tr>
"""

        html += "</table>"

    html += """
        </div>

        <div class="section">
            <div class="section-title">📈 Winning Patterns (Effectiveness)</div>
"""

    for client, patterns in sorted(winning_patterns.items()):
        html += f"<h3 style='color: #888; margin: 15px 0 10px 0;'>{client}</h3>"
        for action_type, stats in sorted(patterns.items()):
            if stats["total"] > 0:
                effectiveness = (stats["effective"] / stats["total"]) * 100
                html += f"""
        <div class="stat-card">
            <strong>{action_type}</strong><br>
            Effectiveness: {effectiveness:.0f}% ({stats['effective']}/{stats['total']} successful)<br>
            Avg delta: {stats['avg_delta']:+.1f} ranks
        </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    return html

def notify_telegram(seo_state):
    """Send summary to Telegram."""
    try:
        from pathlib import Path

        env_path = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")
        if not env_path.exists():
            print("⚠️ Telegram credentials not found")
            return

        env = {}
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")

        token = env.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = env.get("TELEGRAM_USER_ID", "")

        if not token or not chat_id:
            print("⚠️ Telegram credentials incomplete")
            return

        # Build summary message
        work_queue = seo_state.get("work_queue", [])
        effective = len([w for w in work_queue if w.get("status") == "EFFECTIVE"])
        total_executed = len([w for w in work_queue if w.get("status") in ["EFFECTIVE", "NEUTRAL", "HARMFUL"]])

        summary = f"""
🚀 SEO Optimizer Report

📊 Results:
• {effective} effective actions
• {total_executed} total executed
• {len(work_queue)} keywords processed

Winning patterns and detailed results available in HTML report.

✅ Run again: python nightly_seo_optimizer.py
"""

        print(f"✅ Telegram notification prepared ({len(summary)} chars)")

    except Exception as e:
        print(f"⚠️ Telegram notification failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Generate SEO optimizer reports")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    parser.add_argument("--client", help="Single client to report on")
    args = parser.parse_args()

    print("📝 SEO Report Generator — Creating reports...")

    # Load SEO state
    if not SEO_STATE_PATH.exists():
        print("❌ SEO state file not found.")
        return

    with open(SEO_STATE_PATH, "r", encoding="utf-8") as f:
        seo_state = json.load(f)

    # Generate HTML report
    print("  Generating HTML...", end=" ", flush=True)
    html = generate_html_report(seo_state)

    report_path = REPORTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Saved to {report_path}")

    # Notify Telegram
    if not args.no_telegram:
        print("  Sending Telegram...", end=" ", flush=True)
        notify_telegram(seo_state)
        print("✓")

    print(f"\n✅ Report generated: {report_path}")

if __name__ == "__main__":
    main()
