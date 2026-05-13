"""Check 6 — Sugar Shack drift: last FB post age + ranking deltas.

Reuses morning_brief helpers: parse_posting_log, days_since_last_post,
load_keyword_rankings.
"""

import importlib.util
from pathlib import Path

from . import Finding

CHECK_ID = "sugar_shack_drift"
CLIENT_KEY = "sugar_shack"
POST_AGE_THRESHOLD_DAYS = 7
RANK_DROP_THRESHOLD = 2

EXECUTION_DIR = Path("C:/Users/mario/.gemini/antigravity/tools/execution")
PROGRAM_MD = EXECUTION_DIR / CLIENT_KEY / "program.md"
PROPOSED_FIX = (
    "Run /sugar-shack-facebook to draft + post the next ad; "
    "see Terminal C instructions for the ranking-drift response plan"
)


def _load_morning_brief():
    spec = importlib.util.spec_from_file_location(
        "morning_brief", EXECUTION_DIR / "morning_brief.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load morning_brief.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run() -> Finding:
    try:
        mb = _load_morning_brief()
    except BaseException as exc:  # noqa: BLE001 — sys.exit from sub-imports must not kill audit
        if isinstance(exc, KeyboardInterrupt):
            raise
        return Finding.now(
            id=f"{CHECK_ID}_morning_brief_unavailable",
            severity="warn",
            problem="Cannot import morning_brief.py — drift check skipped",
            root_cause_guess=f"{type(exc).__name__}: {exc}",
            proposed_fix="Confirm morning_brief.py still imports clean",
        )

    days_ago = None
    if PROGRAM_MD.exists():
        try:
            md_text = PROGRAM_MD.read_text(encoding="utf-8", errors="replace")
            log = mb.parse_posting_log(md_text)
            days_ago = mb.days_since_last_post(log)
        except BaseException as exc:
            if isinstance(exc, KeyboardInterrupt):
                raise
            days_ago = None

    try:
        rankings = mb.load_keyword_rankings()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        rankings = {}

    biz_rankings = rankings.get(CLIENT_KEY, {}) if isinstance(rankings, dict) else {}
    big_drops = []
    for kw, data in biz_rankings.items():
        if not isinstance(data, dict):
            continue
        delta = data.get("delta")
        # delta convention in morning_brief: positive = improved, negative = dropped
        if isinstance(delta, (int, float)) and delta <= -RANK_DROP_THRESHOLD:
            position = data.get("position")
            big_drops.append(f"{kw} (now #{position}, Δ{int(delta)})")

    problems = []
    if days_ago is None:
        problems.append("posting log unparseable")
    elif days_ago > POST_AGE_THRESHOLD_DAYS:
        problems.append(f"last FB post {days_ago} days ago")

    if big_drops:
        sample = "; ".join(big_drops[:3])
        problems.append(f"{len(big_drops)} keyword drop ≥{RANK_DROP_THRESHOLD} pos ({sample})")

    if problems:
        return Finding.now(
            id=f"{CHECK_ID}_drift",
            severity="error" if (days_ago and days_ago > POST_AGE_THRESHOLD_DAYS) or big_drops else "warn",
            problem=f"Sugar Shack drift: {'; '.join(problems)}",
            root_cause_guess=f"program.md: {PROGRAM_MD}",
            proposed_fix=PROPOSED_FIX,
        )

    age_note = f"{days_ago}d since last post" if days_ago is not None else "post age unknown"
    return Finding.now(
        id=f"{CHECK_ID}_ok",
        severity="info",
        problem=f"Sugar Shack within tolerance ({age_note}, no rank drops ≥{RANK_DROP_THRESHOLD})",
        root_cause_guess="",
        proposed_fix="",
    )
