"""Check 4 — War Room browser console errors via Playwright headless."""

import json
import time
from pathlib import Path

from . import Finding

CHECK_ID = "war_room_console"
TARGET_URL = "http://localhost:3001/war-room"
BASELINE_PATH = (
    Path(__file__).resolve().parent.parent / "console_baseline.json"
)


def _load_ignore_substrings() -> list:
    try:
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        return [s for s in data.get("ignore_substrings", []) if isinstance(s, str)]
    except Exception:
        return []


def run() -> Finding:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return Finding.now(
            id=f"{CHECK_ID}_playwright_missing",
            severity="warn",
            problem="Playwright not installed — skipping console error capture",
            root_cause_guess="`playwright` Python package not on this interpreter",
            proposed_fix="pip install playwright && playwright install chromium",
        )

    ignore_subs = _load_ignore_substrings()
    errors: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = browser.new_context()
            page = ctx.new_page()

            def on_console(msg):
                if msg.type == "error":
                    text = msg.text
                    if not any(sub in text for sub in ignore_subs):
                        errors.append(text)

            page.on("console", on_console)

            try:
                page.goto(TARGET_URL, timeout=10000, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001 — surface any goto failure
                browser.close()
                return Finding.now(
                    id=f"{CHECK_ID}_load_failed",
                    severity="warn",
                    problem=f"Could not load {TARGET_URL} for console capture",
                    root_cause_guess=f"{type(exc).__name__}: {exc}",
                    proposed_fix="Confirm MC dev server is running (see check mc_dev_server)",
                )

            time.sleep(5)
            browser.close()
    except Exception as exc:  # noqa: BLE001
        return Finding.now(
            id=f"{CHECK_ID}_playwright_error",
            severity="warn",
            problem="Playwright crashed while capturing console errors",
            root_cause_guess=f"{type(exc).__name__}: {exc}",
            proposed_fix="playwright install chromium  # ensure browser binaries present",
        )

    if errors:
        sample = " | ".join(errors[:3])
        return Finding.now(
            id=f"{CHECK_ID}_new_errors",
            severity="error",
            problem=f"{len(errors)} new console.error event(s) on /war-room",
            root_cause_guess=f"Sample: {sample}",
            proposed_fix=(
                "Open DevTools on localhost:3001/war-room; once fixed, "
                f"add silenced substrings to {BASELINE_PATH.name}"
            ),
        )

    return Finding.now(
        id=f"{CHECK_ID}_clean",
        severity="info",
        problem="No new console.error events on /war-room in 5s window",
        root_cause_guess="",
        proposed_fix="",
    )
