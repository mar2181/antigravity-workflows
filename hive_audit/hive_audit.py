#!/usr/bin/env python3
"""
hive_audit.py — v1 diagnose-only hive infrastructure self-audit.

Runs 7 checks (MCP, War Room bridge, MC dev server, console errors, Supabase env,
Sugar Shack drift, dashboard build) and reports findings to a markdown file
and to Mario via Telegram. Takes ZERO automated fixes.

Usage:
  python hive_audit.py
  python hive_audit.py --no-telegram
  python hive_audit.py --only mcp_health,supabase_env
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Make the audit_checks package importable when run as a script
sys.path.insert(0, str(HERE))

from audit_checks import Finding  # noqa: E402

CHECKS = [
    ("mcp_health", "MCP health"),
    ("war_room_bridge", "War Room bridge"),
    ("mc_dev_server", "MC dev server"),
    ("war_room_console", "War Room console errors"),
    ("supabase_env", "Supabase env"),
    ("sugar_shack_drift", "Sugar Shack drift"),
    ("dashboard_build", "Dashboard build"),
]

SEVERITY_EMOJI = {"info": "🟢", "warn": "🟡", "error": "🔴"}


def _safe_run(module_slug: str) -> Finding:
    try:
        mod = importlib.import_module(f"audit_checks.{module_slug}")
        result = mod.run()
        if not isinstance(result, Finding):
            raise TypeError(f"{module_slug}.run() returned {type(result).__name__}, not Finding")
        return result
    except KeyboardInterrupt:
        raise
    except BaseException as exc:  # noqa: BLE001 — also catch SystemExit from imported modules
        return Finding.now(
            id=f"{module_slug}_check_crashed",
            severity="error",
            problem=f"Check `{module_slug}` crashed: {type(exc).__name__}: {exc}",
            root_cause_guess=traceback.format_exc().splitlines()[-1] if traceback.format_exc() else "",
            proposed_fix=f"Inspect hive_audit/audit_checks/{module_slug}.py and re-run",
        )


def render_markdown(findings: list[tuple[str, Finding]], started_at: datetime) -> str:
    counts = {"info": 0, "warn": 0, "error": 0}
    for _, f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines = [
        f"# Hive Audit — {started_at:%Y-%m-%d %H:%M}",
        "",
        "## Summary",
        f"- Total checks: {len(findings)}",
        f"- Pass: {counts['info']} | Warn: {counts['warn']} | Error: {counts['error']}",
        "",
        "## Findings",
        "",
    ]

    severity_order = ["error", "warn", "info"]
    for sev in severity_order:
        subset = [(label, f) for label, f in findings if f.severity == sev]
        if not subset:
            continue
        emoji = SEVERITY_EMOJI[sev]
        for label, f in subset:
            lines.append(f"### {emoji} {sev.upper()} — {label}: {f.problem}")
            lines.append(f"- **Check id:** `{f.id}`")
            if f.root_cause_guess:
                lines.append(f"- **Root cause guess:** {f.root_cause_guess}")
            if f.proposed_fix:
                lines.append(f"- **Proposed fix:** `{f.proposed_fix}`")
            lines.append(f"- **First seen:** {f.first_seen}")
            lines.append("")

    lines.append("---")
    lines.append("_v1 is diagnose-only. No fixes were executed. Mario approves any changes manually._")
    return "\n".join(lines) + "\n"


def _load_telegram_env() -> tuple[str, str]:
    env_path = Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")
    token = chat_id = ""
    if not env_path.exists():
        return token, chat_id
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k == "TELEGRAM_BOT_TOKEN":
                token = v
            elif k == "TELEGRAM_USER_ID":
                chat_id = v
    return token, chat_id


def notify_mario(text: str) -> bool:
    token, chat_id = _load_telegram_env()
    if not token or not chat_id:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
        return bool(payload.get("ok"))
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Hive self-audit v1 (diagnose-only)")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    parser.add_argument("--only", help="Comma-separated check slugs to run")
    args = parser.parse_args()

    started_at = datetime.now()
    print(f"[hive-audit] starting at {started_at:%Y-%m-%d %H:%M:%S}")

    only = set(s.strip() for s in args.only.split(",")) if args.only else None
    findings: list[tuple[str, Finding]] = []
    for slug, label in CHECKS:
        if only and slug not in only:
            continue
        print(f"[hive-audit] running {slug} …")
        finding = _safe_run(slug)
        findings.append((label, finding))
        print(f"  -> {finding.severity.upper()}: {finding.problem}")

    md = render_markdown(findings, started_at)
    report_path = REPORTS_DIR / f"{started_at:%Y-%m-%d_%H%M}.md"
    report_path.write_text(md, encoding="utf-8")
    print(f"[hive-audit] report saved: {report_path}")

    counts = {"info": 0, "warn": 0, "error": 0}
    for _, f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    top_issue = next(
        (f.problem for _, f in findings if f.severity == "error"),
        next((f.problem for _, f in findings if f.severity == "warn"), "All green"),
    )

    summary = (
        f"Hive Audit {started_at:%Y-%m-%d %H:%M}\n"
        f"✅ Green: {counts['info']}  🟡 Warn: {counts['warn']}  🔴 Error: {counts['error']}\n"
        f"Report: {report_path}\n"
        f"Top issue: {top_issue}"
    )

    if args.no_telegram:
        print("[hive-audit] --no-telegram set; skipping Telegram")
    else:
        ok = notify_mario(summary)
        print(f"[hive-audit] telegram delivered: {ok}")

    print("[hive-audit] done.")
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
