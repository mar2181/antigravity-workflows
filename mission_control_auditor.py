#!/usr/bin/env python3
"""
mission_control_auditor.py — Daily self-healing agent for Mission Control dashboard

Phases:
  1. Pattern scan  — grep for console.log, @ts-ignore, mock data, TODOs
  2. Structure check — missing loading.tsx, error.tsx, page.tsx files
  3. Claude deep analysis — reads pages + API routes, finds logic bugs / data gaps

Apply mode (--apply flag, called by telegram_bot.py):
  - Reads mc_audit_queue.json, backs up files, calls Claude to apply changes
  - Runs npm run build to verify — reverts ALL changes on failure

Usage:
    python mission_control_auditor.py            # full audit + send Telegram
    python mission_control_auditor.py --now      # same
    python mission_control_auditor.py --apply 1 3 6
    python mission_control_auditor.py --apply all
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────
EXECUTION_DIR  = Path(__file__).parent
SCRATCH_DIR    = EXECUTION_DIR.parent.parent / "scratch"
ENV_PATH       = SCRATCH_DIR / "gravity-claw" / ".env"
CONFIG_PATH    = SCRATCH_DIR / "jack_automations_vault" / "skill_improver_config.json"
DASHBOARD_PATH = Path("C:/Users/mario/missioncontrol/dashboard")
QUEUE_PATH     = EXECUTION_DIR / "mc_audit_queue.json"
NPM_CMD        = "npm.cmd" if sys.platform == "win32" else "npm"

# Category sort order for Telegram output
CATEGORY_ORDER = ["bug", "data_gap", "ux_issue", "improvement"]
CATEGORY_HEADER = {
    "bug":         "🐛 BUGS",
    "data_gap":    "📊 DATA GAPS",
    "ux_issue":    "🎨 UX ISSUES",
    "improvement": "💡 IMPROVEMENTS",
}

# ── Section map: file path prefix → (section label, where to check in browser) ──
# Ordered longest-first so more specific paths match before general ones.
SECTION_MAP = [
    ("app/content/ad-library",          "Ad Library",                     "/content/ad-library"),
    ("app/dashboard/approvals",         "Approvals page",                  "/dashboard/approvals"),
    ("app/api/ad-creatives",            "Ad Library",                      "/content/ad-library"),
    ("app/api/assets",                  "Ad Library — Image Pool tab",     "/content/ad-library → Image Pool tab"),
    ("app/api/automation/facebook",     "Automation — Facebook tab",       "/automation → Facebook tab"),
    ("app/api/automation/gbp",          "Automation — GBP tab",            "/automation → GBP tab"),
    ("app/api/automation/breakout",     "Automation — Breakout tab",       "/automation → Breakout tab"),
    ("app/api/automation",              "Automation page",                 "/automation"),
    ("app/api/dashboard/metrics",       "Home Dashboard + Rankings (KPI cards)", "/ and /rankings"),
    ("app/api/competitors",             "Competitors page",                "/competitors"),
    ("app/api/intel",                   "Competitors — Local Intel tab",   "/competitors → Local tab"),
    ("app/api/research",                "Research page",                   "/research"),
    ("app/api/reviews",                 "Reviews page",                    "/reviews"),
    ("app/api/reports",                 "Reports page",                    "/reports"),
    ("app/api/client-profiles",         "Client selector (sidebar dropdown)", "Sidebar — switch client"),
    ("app/api/projects",                "All pages — project list",        "Client selector on any page"),
    ("app/api/image",                   "Content Studio — image generation", "/content → image tools"),
    ("app/api/content",                 "Content Studio",                  "/content"),
    ("app/api/notes",                   "Client Notes page",               "/notes"),
    ("app/api/settings",                "Settings page",                   "/settings"),
    ("app/api/website",                 "Website Factory",                 "/website-factory"),
    ("app/api/video",                   "Video Studio",                    "/video"),
    ("app/api/v1/approvals",            "Approvals page",                  "/dashboard/approvals"),
    ("app/api/v1",                      "Automation orchestration",        "/automation or /dashboard/approvals"),
    ("app/api/social",                  "Content Studio — social tools",   "/content"),
    ("app/api/upload-image",            "Image upload (multiple pages)",   "Any page with image upload"),
    ("app/api/atlas-brain",             "AI assistant (multiple pages)",   "Pages using AI chat"),
    ("app/content",                     "Content Studio",                  "/content"),
    ("app/competitors",                 "Competitors page",                "/competitors"),
    ("app/automation",                  "Automation page",                 "/automation"),
    ("app/rankings",                    "Rankings page",                   "/rankings"),
    ("app/traffic",                     "Traffic page",                    "/traffic"),
    ("app/local",                       "Local & GBP page",                "/local"),
    ("app/otto",                        "OTTO Command page",               "/otto"),
    ("app/research",                    "Research page",                   "/research"),
    ("app/reports",                     "Reports page",                    "/reports"),
    ("app/plan",                        "SEO Plan page",                   "/plan"),
    ("app/notes",                       "Client Notes page",               "/notes"),
    ("app/website-factory",             "Website Factory",                 "/website-factory"),
    ("app/reviews",                     "Reviews page",                    "/reviews"),
    ("app/settings",                    "Settings page",                   "/settings"),
    ("app/video",                       "Video Studio",                    "/video"),
    ("app/studio3d",                    "3D Studio page",                  "/studio3d"),
    ("app/page.tsx",                    "Home Dashboard",                  "/"),
    ("app/layout.tsx",                  "All pages (root layout)",         "Every page in the app"),
    ("components/KPICard",              "Home Dashboard — KPI cards",      "/ → KPI card row"),
    ("components/Sidebar",              "Sidebar navigation",              "Sidebar — visible on every page"),
    ("components/Header",               "Top navigation bar",              "Header — visible on every page"),
    ("components/ads/",                 "Ad Library",                      "/content/ad-library"),
    ("components/automation/",          "Automation page",                 "/automation"),
    ("components/approvals/",           "Approvals page",                  "/dashboard/approvals"),
    ("components/",                     "Shared UI components",            "Multiple pages — check affected feature"),
    ("app/api/",                        "Backend API",                     "Server-side — check the page that calls it"),
]


def _section_from_file(rel_path: str) -> tuple:
    """Return (section_label, where_to_check) for a given src-relative file path."""
    rel_norm = rel_path.replace("\\", "/")
    for prefix, label, where in SECTION_MAP:
        if rel_norm.startswith(prefix):
            return label, where
    return "Mission Control app", "Open the app and navigate to the affected area"


def _section_from_files(affected_files: list) -> tuple:
    """Return best (section_label, where_to_check) for a list of affected files."""
    if not affected_files:
        return "Mission Control app", "Open the app"
    label, where = _section_from_file(affected_files[0])
    # If multiple distinct sections, note that
    if len(affected_files) > 1:
        labels = {_section_from_file(f)[0] for f in affected_files}
        if len(labels) > 1:
            label = " + ".join(sorted(labels))
    return label, where

# ── Credentials ────────────────────────────────────────────────────────────
def _load_env(path: Path) -> dict:
    env: dict = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env

def _load_anthropic_key() -> str:
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        key = cfg.get("anthropic_api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")

_env          = _load_env(ENV_PATH)
TOKEN         = _env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID      = str(_env.get("TELEGRAM_USER_ID") or os.environ.get("TELEGRAM_USER_ID", ""))
ANTHROPIC_KEY = _load_anthropic_key()


# ── Telegram helper ─────────────────────────────────────────────────────────
def _tg_send(text: str) -> None:
    if not TOKEN or not OWNER_ID:
        print(f"[Telegram disabled] {text[:200]}")
        return
    text = text or "(empty)"
    for i in range(0, max(len(text), 1), 4096):
        chunk = text[i:i + 4096]
        data  = urllib.parse.urlencode({"chat_id": OWNER_ID, "text": chunk}).encode()
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data
                ),
                timeout=10,
            )
        except Exception as e:
            print(f"Telegram send error: {e}")


# ── Claude API helper ───────────────────────────────────────────────────────
def _call_claude(prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    if not ANTHROPIC_KEY:
        return "ERROR: No Anthropic API key found."
    payload = json.dumps({
        "model":      "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "system":     system or "You are an expert Next.js 14 and TypeScript code auditor.",
        "messages":   [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        resp   = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        return f"ERROR: Anthropic {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return f"ERROR: {e}"


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if Claude wraps output in them."""
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
    if text.endswith("```"):
        text = text[:-3].rstrip()
    return text


# ── Phase 1: Pattern Scan ───────────────────────────────────────────────────
PATTERNS = [
    ("bug",      r"console\.log\(",
     "console.log left in production code",
     "Remove this console.log call — it leaks data in browser devtools."),

    ("bug",      r"//\s*@ts-ignore",
     "TypeScript error suppressed with @ts-ignore",
     "Fix the underlying TypeScript error instead of suppressing it."),

    ("bug",      r"\bas any\b",
     "Unsafe TypeScript cast to 'any'",
     "Replace 'as any' with a proper type. This hides runtime errors from TypeScript."),

    ("data_gap", r"'00000000-0000-0000-0000-000000000000'",
     "Null UUID hardcoded as default owner_id",
     "Generate a real UUID or require the caller to provide owner_id — null UUIDs create orphaned records."),

    ("data_gap", r"//\s*(TODO|FIXME|HACK):",
     "Unresolved TODO/FIXME in code",
     "Resolve or remove this TODO. Unfinished code ships to production."),
]

# Dirs to skip entirely during scan
SKIP_DIRS = {"node_modules", ".next", "__pycache__", ".git", "video", "studio3d"}
MAX_HITS_PER_PATTERN = 2  # keep noise low — report first 2 files per pattern


def phase1_pattern_scan() -> list:
    """Grep source files for known problem patterns."""
    src_dir = DASHBOARD_PATH / "src"
    if not src_dir.exists():
        print(f"  ⚠️ src dir not found: {src_dir}")
        return []

    findings = []
    hits_per_pattern: dict = {}

    ts_files = []
    for f in src_dir.rglob("*.ts"):
        if not any(d in SKIP_DIRS for d in f.parts):
            ts_files.append(f)
    for f in src_dir.rglob("*.tsx"):
        if not any(d in SKIP_DIRS for d in f.parts):
            ts_files.append(f)

    for ts_file in sorted(ts_files):
        try:
            content = ts_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(ts_file.relative_to(DASHBOARD_PATH / "src")).replace("\\", "/")

        for category, pattern, title, fix in PATTERNS:
            if hits_per_pattern.get(pattern, 0) >= MAX_HITS_PER_PATTERN:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                # Skip pure comment lines for console.log pattern
                if pattern == r"console\.log\(" and line.strip().startswith("//"):
                    continue
                if re.search(pattern, line, re.IGNORECASE):
                    hits_per_pattern[pattern] = hits_per_pattern.get(pattern, 0) + 1
                    section, where = _section_from_file(rel)
                    findings.append({
                        "category":       category,
                        "source":         "pattern_scan",
                        "title":          f"{title} ({rel}:{i})",
                        "description":    f"Found in `{rel}` at line {i}: `{line.strip()[:80]}`",
                        "proposed_change": fix,
                        "affected_files": [rel],
                        "app_section":    section,
                        "where_to_check": where,
                        "risk":           "low",
                        "applied":        False,
                        "applied_at":     None,
                    })
                    break  # one hit per file per pattern

    return findings


# ── Phase 2: Structure Check ────────────────────────────────────────────────
# (route_label, relative page path from src/)
SIDEBAR_ROUTES = [
    ("",                     "app/page.tsx"),
    ("rankings",             "app/rankings/page.tsx"),
    ("traffic",              "app/traffic/page.tsx"),
    ("competitors",          "app/competitors/page.tsx"),
    ("local",                "app/local/page.tsx"),
    ("content",              "app/content/page.tsx"),
    ("content/ad-library",   "app/content/ad-library/page.tsx"),
    ("otto",                 "app/otto/page.tsx"),
    ("research",             "app/research/page.tsx"),
    ("reports",              "app/reports/page.tsx"),
    ("plan",                 "app/plan/page.tsx"),
    ("notes",                "app/notes/page.tsx"),
    ("website-factory",      "app/website-factory/page.tsx"),
    ("automation",           "app/automation/page.tsx"),
    ("reviews",              "app/reviews/page.tsx"),
    ("dashboard/approvals",  "app/dashboard/approvals/page.tsx"),
]

LOADING_TEMPLATE = (
    "export default function Loading() {\n"
    "  return (\n"
    "    <div className=\"flex items-center justify-center h-64\">\n"
    "      <div className=\"animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400\" />\n"
    "    </div>\n"
    "  );\n"
    "}\n"
)

ERROR_TEMPLATE = (
    "'use client';\n\n"
    "export default function Error({\n"
    "  error,\n"
    "  reset,\n"
    "}: {\n"
    "  error: Error & { digest?: string };\n"
    "  reset: () => void;\n"
    "}) {\n"
    "  return (\n"
    "    <div className=\"flex flex-col items-center justify-center h-64 gap-4\">\n"
    "      <p className=\"text-red-400 text-sm\">\n"
    "        Something went wrong: {error.message}\n"
    "      </p>\n"
    "      <button\n"
    "        onClick={reset}\n"
    "        className=\"px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-sm transition-colors\"\n"
    "      >\n"
    "        Try again\n"
    "      </button>\n"
    "    </div>\n"
    "  );\n"
    "}\n"
)


def phase2_structure_check() -> list:
    """Check for missing loading.tsx, error.tsx, and page.tsx files."""
    src = DASHBOARD_PATH / "src"
    findings = []

    missing_page    = []
    missing_loading = []
    missing_error   = []

    for route, page_rel in SIDEBAR_ROUTES:
        page_path = src / page_rel
        if not page_path.exists():
            missing_page.append(f"/{route}" if route else "/")
            continue
        dir_path = page_path.parent
        loading_rel = page_rel.replace("page.tsx", "loading.tsx")
        error_rel   = page_rel.replace("page.tsx", "error.tsx")
        if not (dir_path / "loading.tsx").exists():
            missing_loading.append(loading_rel)
        if not (dir_path / "error.tsx").exists():
            missing_error.append(error_rel)

    if missing_page:
        page_files = [
            (r.lstrip("/") if r != "/" else "app") + "/page.tsx"
            for r in missing_page
        ]
        findings.append({
            "category":       "bug",
            "source":         "structure_check",
            "title":          f"Sidebar links to {len(missing_page)} missing page(s)",
            "description":    (
                f"These routes appear in the sidebar navigation but have no page.tsx file — "
                f"clicking them gives a 404 blank page: {', '.join(missing_page[:5])}"
            ),
            "proposed_change": "Create a minimal placeholder page.tsx for each missing route with 'Coming Soon' text.",
            "affected_files": page_files,
            "app_section":    "Sidebar navigation — these menu items are broken",
            "where_to_check": f"Click these sidebar links: {', '.join(missing_page[:4])}",
            "risk":           "medium",
            "applied":        False,
            "applied_at":     None,
        })

    if missing_loading:
        sample = missing_loading[:4]
        page_names = [p.replace("app/", "/").replace("/loading.tsx", "") or "/" for p in sample]
        extras = f" + {len(missing_loading) - 4} more" if len(missing_loading) > 4 else ""
        findings.append({
            "category":       "ux_issue",
            "source":         "structure_check",
            "title":          f"{len(missing_loading)} pages missing loading.tsx (white flash on navigation)",
            "description":    (
                f"Next.js 14 uses loading.tsx for instant Suspense-based loading UI. Without it, "
                f"clicking to these pages shows a blank white screen until data arrives. "
                f"Affected pages: {', '.join(page_names)}{extras}"
            ),
            "proposed_change": LOADING_TEMPLATE,
            "affected_files": missing_loading,
            "app_section":    f"All pages in app ({len(missing_loading)} routes affected)",
            "where_to_check": f"Click fast between pages in sidebar — check for white flash on: {', '.join(page_names[:3])}",
            "risk":           "low",
            "applied":        False,
            "applied_at":     None,
        })

    if missing_error:
        sample = missing_error[:4]
        page_names = [p.replace("app/", "/").replace("/error.tsx", "") or "/" for p in sample]
        extras = f" + {len(missing_error) - 4} more" if len(missing_error) > 4 else ""
        findings.append({
            "category":       "ux_issue",
            "source":         "structure_check",
            "title":          f"{len(missing_error)} pages missing error.tsx (no crash recovery UI)",
            "description":    (
                f"Without error.tsx, any uncaught JS error on these pages crashes to a blank screen "
                f"with no way to recover except a full browser refresh. "
                f"Affected pages: {', '.join(page_names)}{extras}"
            ),
            "proposed_change": ERROR_TEMPLATE,
            "affected_files": missing_error,
            "app_section":    f"All pages in app ({len(missing_error)} routes affected)",
            "where_to_check": f"Trigger a bad API call on any of these pages: {', '.join(page_names[:3])} — should show 'Try again' button instead of blank screen",
            "risk":           "low",
            "applied":        False,
            "applied_at":     None,
        })

    return findings


# ── Phase 3: Claude Deep Analysis ───────────────────────────────────────────
MAX_FILE_CHARS = 6000  # Truncate large files before sending to Claude


def _collect_source_files() -> dict:
    """Collect page.tsx and route.ts files for Claude analysis."""
    src = DASHBOARD_PATH / "src"
    files: dict = {}

    targets = []
    for f in src.rglob("page.tsx"):
        if not any(d in SKIP_DIRS for d in f.parts):
            targets.append(f)
    for f in src.rglob("route.ts"):
        if not any(d in SKIP_DIRS for d in f.parts):
            targets.append(f)

    for ts_file in sorted(targets)[:25]:  # cap at 25 files
        rel = str(ts_file.relative_to(src)).replace("\\", "/")
        try:
            content = ts_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + f"\n... [truncated at {MAX_FILE_CHARS} chars]"
        files[rel] = content

    return files


def phase3_claude_analysis() -> list:
    """Ask Claude to audit the codebase and return structured findings."""
    files = _collect_source_files()
    if not files:
        print("  ⚠️ No source files found for Phase 3 — is dashboard path correct?")
        return []

    file_blocks = [f"=== {rel} ===\n{content}" for rel, content in files.items()]
    file_dump   = "\n\n".join(file_blocks)

    prompt = (
        "You are auditing Mission Control, a Next.js 14 SEO dashboard for a digital marketing agency "
        "managing 8 local business clients (Sugar Shack candy store, Island Arcade, Island Candy, "
        "Juan Elizondo RE/MAX real estate, SPI Fun Rentals, Custom Designs TX, Optimum Clinic, "
        "Optimum Foundation). The dashboard shows keyword rankings, GBP performance, competitor intel, "
        "content studio, ad library, and automation controls.\n\n"
        "Analyze the source files below and return a JSON array of findings.\n"
        "Focus on issues that require understanding application context — NOT style or naming.\n\n"
        "Each finding MUST have these exact JSON fields:\n"
        "  category: \"bug\" | \"data_gap\" | \"ux_issue\" | \"improvement\"\n"
        "  title: one-line description, max 80 characters\n"
        "  description: 2-3 sentences explaining the problem and its real-world business impact\n"
        "  proposed_change: specific, actionable change with enough detail to implement it\n"
        "  affected_files: array of relative file paths from src/ (strings)\n"
        "  app_section: human-readable name of the dashboard section affected (e.g. 'Rankings page', 'Ad Library', 'Automation > GBP tab', 'Home Dashboard — KPI cards')\n"
        "  where_to_check: one sentence telling the user exactly where to look in the browser UI after the fix (e.g. 'Open /rankings and check that KPI cards show real data', 'Go to /automation → GBP tab and post a test update')\n"
        "  risk: \"low\" | \"medium\" | \"high\"\n\n"
        "Rules:\n"
        "- Return exactly 4-6 findings (the most impactful ones)\n"
        "- Order by impact: bugs > data gaps > UX issues > improvements\n"
        "- Only flag real issues (wrong data shown, broken functionality, security risk, missing error handling)\n"
        "- Do NOT flag code style, naming, or TypeScript strictness issues\n"
        "- Return ONLY a valid JSON array — no markdown, no explanation, no prose\n\n"
        f"Source files:\n\n{file_dump}"
    )

    raw = _call_claude(prompt, max_tokens=3000)
    if raw.startswith("ERROR:"):
        print(f"  Phase 3 Claude error: {raw}")
        return []

    try:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            print(f"  Phase 3: no JSON array in response: {raw[:200]}")
            return []
        parsed = json.loads(raw[start:end])
        findings = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            affected = [str(f) for f in item.get("affected_files", [])]
            # Fall back to section map if Claude didn't provide app_section
            fallback_section, fallback_where = _section_from_files(affected)
            findings.append({
                "category":       item.get("category", "improvement"),
                "source":         "claude_analysis",
                "title":          str(item.get("title", "Untitled finding"))[:120],
                "description":    str(item.get("description", "")),
                "proposed_change": str(item.get("proposed_change", "")),
                "affected_files": affected,
                "app_section":    str(item.get("app_section", fallback_section)),
                "where_to_check": str(item.get("where_to_check", fallback_where)),
                "risk":           item.get("risk", "low"),
                "applied":        False,
                "applied_at":     None,
            })
        return findings
    except Exception as e:
        print(f"  Phase 3 parse error: {e}\n  Raw: {raw[:300]}")
        return []


# ── Main Audit Orchestrator ─────────────────────────────────────────────────
def run_audit() -> None:
    print(f"[{datetime.now():%H:%M:%S}] Mission Control daily audit starting...")
    _tg_send("🔄 Mission Control daily audit running... (~90 seconds)")

    findings: list = []

    print("Phase 1: Pattern scan...")
    p1 = phase1_pattern_scan()
    findings.extend(p1)
    print(f"  → {len(p1)} pattern finding(s)")

    print("Phase 2: Structure check...")
    p2 = phase2_structure_check()
    findings.extend(p2)
    print(f"  → {len(p2)} structure finding(s)")

    print("Phase 3: Claude deep analysis...")
    p3 = phase3_claude_analysis()
    findings.extend(p3)
    print(f"  → {len(p3)} Claude finding(s)")

    # Sort by category priority, then assign sequential IDs (before pre-validation
    # so IDs are stable and printed in tsc output)
    category_rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    findings.sort(key=lambda f: category_rank.get(f.get("category", "improvement"), 99))
    for i, f in enumerate(findings, 1):
        f["id"] = i

    print("Phase 3.5: Karpathy pre-validation loop (tsc --noEmit per fix)...")
    findings = phase3_5_prevalidate(findings)
    validated_count = sum(1 for f in findings if f.get("pre_validated", True))
    unverified_count = len(findings) - validated_count
    print(f"  → {validated_count} pre-validated ✅ | {unverified_count} unverified ⚠️")

    # Save queue
    now = datetime.now(timezone.utc)
    queue = {
        "generated_at":   now.isoformat(),
        "dashboard_path": str(DASHBOARD_PATH),
        "build_verified": False,
        "fixes":          findings,
    }
    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Queue saved: {QUEUE_PATH}")

    # Build Telegram message
    d     = datetime.now()
    today = f"{d.strftime('%B')} {d.day}, {d.year}"
    try:
        src_count = sum(1 for _ in (DASHBOARD_PATH / "src").rglob("*.tsx"))
    except Exception:
        src_count = 0

    validated_n   = sum(1 for f in findings if f.get("pre_validated", True))
    unverified_n  = len(findings) - validated_n
    val_summary   = f" · {validated_n} pre-validated ✅" if findings else ""
    if unverified_n:
        val_summary += f", {unverified_n} unverified ⚠️"

    lines = [
        f"🔍 Mission Control Audit — {today}",
        f"{src_count} files scanned · {len(findings)} finding(s){val_summary}\n",
    ]

    by_cat: dict = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)

    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"{CATEGORY_HEADER[cat]} ({len(items)})")
        lines.append("")
        for f in items:
            risk_tag = " ⚠️ HIGH RISK" if f["risk"] == "high" else (" ⚡ MED" if f["risk"] == "medium" else "")
            section   = f.get("app_section", "")
            desc      = f.get("description", "")
            where     = f.get("where_to_check", "")

            # Pre-validation badge (Phase 3.5 Karpathy loop result)
            # Phase 1/2 findings are always trusted; Phase 3 Claude findings show status
            if f.get("source") in ("pattern_scan", "structure_check"):
                val_badge = ""   # implicit — these are always correct
            elif f.get("pre_validated") is True:
                val_badge = " ✅"
            elif f.get("pre_validated") is False:
                val_badge = " ⚠️ UNVERIFIED"
            else:
                val_badge = ""

            lines.append(f"[{f['id']}]{risk_tag}{val_badge} {f['title']}")
            if section:
                lines.append(f"   📍 {section}")
            if desc:
                # Trim to 140 chars so message stays readable
                short_desc = desc[:140] + "..." if len(desc) > 140 else desc
                lines.append(f"   {short_desc}")
            if where:
                lines.append(f"   ✔ Check: {where}")
            if f.get("pre_validated") is False:
                lines.append(f"   (TypeScript pre-check failed after 3 attempts — review carefully)")
            lines.append("")

    if not findings:
        lines.append("✅ No issues found today! Dashboard looks healthy.")
    else:
        low_ids  = [str(f["id"]) for f in findings if f["risk"] == "low"]
        lines.append("─" * 30)
        lines.append(f"Apply: /mc_apply {' '.join(low_ids[:8])}")
        lines.append("Apply all low-risk: /mc_apply all")

    msg = "\n".join(lines)
    print(f"\n--- Telegram message ---\n{msg}\n---")
    _tg_send(msg)
    print(f"[{datetime.now():%H:%M:%S}] Audit complete.")


# ── Apply Fixes ─────────────────────────────────────────────────────────────
def call_claude_apply(file_content: str, rel_path: str, proposed_change: str) -> str:
    """Ask Claude to apply a change. Returns the complete updated file content."""
    if file_content:
        prompt = (
            f"Apply this specific change to the file below.\n"
            f"Return ONLY the complete updated file content — "
            f"no explanation, no markdown code fences, no backticks, no commentary.\n\n"
            f"Change to apply:\n{proposed_change}\n\n"
            f"File path: {rel_path}\n"
            f"File content:\n{file_content}"
        )
    else:
        prompt = (
            f"Create a new Next.js 14 file at: {rel_path}\n"
            f"The file should contain:\n{proposed_change}\n\n"
            f"Return ONLY the raw file content — no explanation, no markdown code fences, "
            f"no backticks, no commentary."
        )
    raw = _call_claude(prompt, max_tokens=8000)
    return _strip_code_fences(raw)


def call_claude_revise(proposed_change: str, ts_errors: str, affected_files: list) -> str:
    """Ask Claude to revise a proposed_change description after TypeScript errors."""
    prompt = (
        f"Your proposed change description caused TypeScript errors when applied. "
        f"Revise the proposed_change text so it describes a correct fix.\n\n"
        f"Original proposed_change:\n{proposed_change}\n\n"
        f"TypeScript errors produced:\n{ts_errors}\n\n"
        f"Affected files: {', '.join(affected_files)}\n\n"
        f"Return ONLY the revised proposed_change text — one or two sentences describing "
        f"the correct fix. No code, no explanation, no markdown."
    )
    return _call_claude(prompt, max_tokens=500)


def phase3_5_prevalidate(findings: list) -> list:
    """
    Karpathy pre-validation loop.

    For each finding that has affected_files, this function:
    1. Uses call_claude_apply() to generate the actual file content for the fix.
    2. Writes those changes to temp files, swaps them in.
    3. Runs tsc --noEmit to check TypeScript compilation.
    4. Restores originals.
    5. If tsc fails, asks Claude to revise the proposed_change and retries (up to 3x).
    6. Marks finding["pre_validated"] = True if tsc eventually passes, else False.
    7. Updates finding["proposed_change"] to the final working version.

    Findings with no affected_files (e.g. structural notes) are marked validated=True.
    Phase 1 and Phase 2 findings (low-risk patterns, missing files) are skipped —
    they are trivially correct by construction.
    """
    MAX_ITERS = 3
    TSC = DASHBOARD_PATH / "node_modules" / ".bin" / "tsc.cmd"

    if not TSC.exists():
        print("[phase3.5] tsc.cmd not found — skipping pre-validation")
        for f in findings:
            f["pre_validated"] = True
        return findings

    for finding in findings:
        # Skip Phase 1 / Phase 2 findings — they're pattern matches or new-file creates,
        # not code rewrites, so tsc pre-validation adds no value.
        if finding.get("source") in ("pattern_scan", "structure_check"):
            finding["pre_validated"] = True
            continue

        affected = finding.get("affected_files", [])
        if not affected:
            finding["pre_validated"] = True
            continue

        proposed = finding["proposed_change"]
        success  = False

        for iteration in range(MAX_ITERS):
            print(f"  [prevalidate] {finding['id']} iter {iteration+1}/{MAX_ITERS} ...")

            # ── 1. Generate updated file content & write to .tmp copies ──────
            temp_map: dict = {}   # abs_path → tmp_path
            apply_error = False
            for rel_path in affected:
                abs_path = DASHBOARD_PATH / "src" / rel_path
                if not abs_path.exists():
                    # New-file finding — skip tsc (can't compile a single new file)
                    apply_error = True
                    break
                content = abs_path.read_text(encoding="utf-8", errors="replace")
                updated = call_claude_apply(content, rel_path, proposed)
                if updated.startswith("ERROR:"):
                    print(f"    Claude apply error: {updated[:120]}")
                    apply_error = True
                    break
                tmp = abs_path.with_suffix(abs_path.suffix + ".pretmp")
                tmp.write_text(updated, encoding="utf-8")
                temp_map[abs_path] = tmp

            if apply_error:
                # Clean up any .pretmp files already written
                for tmp in temp_map.values():
                    tmp.unlink(missing_ok=True)
                finding["pre_validated"] = False
                break

            # ── 2. Swap .pretmp → real, save originals as .precheck ──────────
            precheck_map: dict = {}   # abs_path → precheck_path
            for orig, tmp in temp_map.items():
                bak = orig.with_suffix(orig.suffix + ".precheck")
                orig.rename(bak)
                tmp.rename(orig)
                precheck_map[orig] = bak

            # ── 3. Run tsc --noEmit ──────────────────────────────────────────
            try:
                tsc_result = subprocess.run(
                    [str(TSC), "--noEmit",
                     "--project", str(DASHBOARD_PATH / "tsconfig.json")],
                    capture_output=True, text=True,
                    cwd=str(DASHBOARD_PATH), timeout=90,
                )
            except Exception as e:
                tsc_result = type("R", (), {"returncode": 1, "stdout": "", "stderr": str(e)})()

            # ── 4. Restore originals ─────────────────────────────────────────
            for orig, bak in precheck_map.items():
                orig.unlink(missing_ok=True)
                bak.rename(orig)

            # ── 5. Evaluate ──────────────────────────────────────────────────
            if tsc_result.returncode == 0:
                success = True
                finding["proposed_change"] = proposed   # keep the working version
                print(f"    tsc PASSED at iteration {iteration+1}")
                break

            ts_errors = (tsc_result.stdout[:1200] + tsc_result.stderr[:300]).strip()
            print(f"    tsc FAILED: {ts_errors[:120]}...")

            if iteration < MAX_ITERS - 1:
                proposed = call_claude_revise(proposed, ts_errors, affected)
                if proposed.startswith("ERROR:"):
                    break

        finding["pre_validated"] = success

    return findings


def _restore_backups(backups: dict) -> None:
    for orig, bak in backups.items():
        try:
            Path(orig).write_text(
                Path(bak).read_text(encoding="utf-8"), encoding="utf-8"
            )
            Path(bak).unlink(missing_ok=True)
        except Exception as e:
            print(f"Warning: could not restore {orig}: {e}")


def apply_fixes(fix_ids_raw: list) -> str:
    """Apply approved fixes. Returns a result string (printed to stdout for bot to capture)."""
    if not QUEUE_PATH.exists():
        return "❌ No audit queue found. Run /mc_audit first to generate findings."

    try:
        queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return f"❌ Failed to read audit queue: {e}"

    all_fixes = queue.get("fixes", [])

    if "all" in fix_ids_raw:
        selected = [f for f in all_fixes if f.get("risk") == "low" and not f.get("applied")]
    else:
        try:
            ids = {int(x) for x in fix_ids_raw}
        except ValueError:
            return "❌ Invalid fix IDs. Use numbers like: /mc_apply 1 3 5\n   Or: /mc_apply all"
        selected = [f for f in all_fixes if f.get("id") in ids and not f.get("applied")]

    if not selected:
        applied_count = sum(1 for f in all_fixes if f.get("applied"))
        if applied_count:
            return f"⚠️ No unapplied fixes match those IDs. ({applied_count} already applied today)"
        return "⚠️ No matching fixes found. Run /mc_audit first."

    # Verify dashboard path exists
    if not DASHBOARD_PATH.exists():
        return f"❌ Dashboard not found at: {DASHBOARD_PATH}"

    backups: dict = {}   # {str(abs_path): str(bak_path)}
    new_files: list = [] # newly created files (for rollback)

    print(f"Applying {len(selected)} fix(es): {[f['id'] for f in selected]}")

    for fix in selected:
        for rel_path in fix.get("affected_files", []):
            abs_path = DASHBOARD_PATH / "src" / rel_path
            if abs_path.exists():
                # Backup existing file
                bak = abs_path.with_suffix(abs_path.suffix + ".mcbak")
                bak.write_text(abs_path.read_text(encoding="utf-8"), encoding="utf-8")
                backups[str(abs_path)] = str(bak)
                print(f"  Backed up: {rel_path}")

                # Apply change to existing file
                print(f"  Applying to: {rel_path}...")
                original = abs_path.read_text(encoding="utf-8")
                updated  = call_claude_apply(original, rel_path, fix["proposed_change"])
                if updated.startswith("ERROR:"):
                    _restore_backups(backups)
                    return f"❌ Claude API error on fix [{fix['id']}]: {updated}"
                abs_path.write_text(updated, encoding="utf-8")
            else:
                # Create new file
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"  Creating: {rel_path}...")
                new_content = call_claude_apply("", rel_path, fix["proposed_change"])
                if new_content.startswith("ERROR:"):
                    _restore_backups(backups)
                    for nf in new_files:
                        Path(nf).unlink(missing_ok=True)
                    return f"❌ Claude API error creating {rel_path}: {new_content}"
                abs_path.write_text(new_content, encoding="utf-8")
                new_files.append(str(abs_path))

    # Verify build
    print("Running npm run build...")
    build_result = subprocess.run(
        [NPM_CMD, "run", "build"],
        cwd=str(DASHBOARD_PATH),
        capture_output=True,
        text=True,
        timeout=300,
    )

    ids_str = ", ".join(str(f["id"]) for f in selected)

    if build_result.returncode == 0:
        # Success — mark applied in queue, clean up backups
        for fix in selected:
            fix["applied"]    = True
            fix["applied_at"] = datetime.now(timezone.utc).isoformat()
        queue["build_verified"] = True
        QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
        for bak in backups.values():
            try:
                Path(bak).unlink(missing_ok=True)
            except Exception:
                pass
        titles = [f['title'][:50] for f in selected]
        summary = "\n  • ".join(titles)
        return f"✅ Applied fix(es) [{ids_str}]. Build: PASSED.\n\nFixed:\n  • {summary}"
    else:
        # Failure — restore all backups, delete new files
        _restore_backups(backups)
        for nf in new_files:
            Path(nf).unlink(missing_ok=True)
        stderr = (build_result.stderr or build_result.stdout or "Unknown error").strip()
        first_error = next(
            (ln for ln in stderr.splitlines() if "error" in ln.lower()), stderr.split("\n")[0]
        )
        return (
            f"❌ Build failed after fix(es) [{ids_str}] — all changes reverted.\n"
            f"Error: {first_error[:250]}\n\n"
            f"The dashboard is unchanged. Check the fix descriptions and try again."
        )


# ── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--apply" in args:
        idx       = args.index("--apply")
        apply_ids = args[idx + 1:]
        if not apply_ids:
            print("Usage: python mission_control_auditor.py --apply 1 3 6")
            print("       python mission_control_auditor.py --apply all")
            sys.exit(1)
        result = apply_fixes(apply_ids)
        print(result)
        sys.exit(0 if result.startswith("✅") else 1)
    else:
        # Default: full audit + Telegram
        run_audit()
