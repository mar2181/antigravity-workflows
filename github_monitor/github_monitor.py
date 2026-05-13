"""
GitHub Morning Monitor — runs daily at 9 AM via Windows Task Scheduler.

For each repo in config.json:
  - Lists open PRs (ready-to-merge work)
  - Finds branches >= N commits behind default branch (stale, needs rebase/delete)
  - Finds branches ahead of default with no open PR (forgotten work)

Builds an actionable Telegram summary and sends it via the gravity-claw bot.

Run manually:
    python github_monitor.py                # full run, sends Telegram
    python github_monitor.py --dry-run      # prints to stdout, no Telegram
    python github_monitor.py --repo mar2181/missioncontrol   # single repo

Requires: `gh` CLI authenticated as mar2181.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ---------- gh CLI helpers --------------------------------------------------

def gh(*args: str) -> str:
    """Run `gh` and return stdout. Raises on non-zero exit."""
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return proc.stdout


def gh_json(*args: str):
    out = gh(*args).strip()
    return json.loads(out) if out else None


def get_default_branch(repo: str) -> str:
    return gh("api", f"repos/{repo}", "--jq", ".default_branch").strip()


def list_open_prs(repo: str) -> list[dict]:
    return gh_json(
        "pr", "list",
        "--repo", repo,
        "--state", "open",
        "--json", "number,title,author,createdAt,updatedAt,isDraft,headRefName,baseRefName,url",
        "--limit", "100",
    ) or []


def list_branches(repo: str) -> list[dict]:
    """All branches with their head SHA.

    --paginate concatenates JSON outputs across pages, so we emit one object
    per line via jq and parse line-by-line instead of trying to parse the
    whole blob as a single JSON document.
    """
    out = gh(
        "api", f"repos/{repo}/branches",
        "--paginate",
        "--jq", ".[] | {name, sha: .commit.sha} | @json",
    )
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def compare_branch(repo: str, base: str, head: str) -> dict:
    """Returns {ahead_by, behind_by, status} or {} on error (e.g. unrelated histories)."""
    try:
        data = gh_json(
            "api",
            f"repos/{repo}/compare/{urllib.parse.quote(base, safe='')}...{urllib.parse.quote(head, safe='')}",
            "--jq", "{ahead_by, behind_by, status}",
        )
        return data or {}
    except RuntimeError:
        return {}


# ---------- Per-repo audit --------------------------------------------------

def audit_repo(repo: str, label: str, threshold: int) -> dict:
    result = {
        "label": label,
        "repo": repo,
        "ok": True,
        "error": None,
        "default_branch": None,
        "open_prs": [],
        "stale_branches": [],
        "ahead_no_pr": [],
    }

    try:
        default = get_default_branch(repo)
        result["default_branch"] = default

        prs = list_open_prs(repo)
        result["open_prs"] = prs
        pr_branches = {pr["headRefName"] for pr in prs}

        branches = list_branches(repo)
        for b in branches:
            name = b["name"]
            if name == default:
                continue
            cmp_ = compare_branch(repo, default, name)
            if not cmp_:
                continue
            behind = cmp_.get("behind_by", 0) or 0
            ahead = cmp_.get("ahead_by", 0) or 0

            if behind >= threshold:
                result["stale_branches"].append({
                    "name": name, "behind": behind, "ahead": ahead,
                })

            if ahead > 0 and name not in pr_branches:
                result["ahead_no_pr"].append({
                    "name": name, "ahead": ahead, "behind": behind,
                })

    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)

    return result


# ---------- Report formatting -----------------------------------------------

def fmt_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days <= 0:
            return "today"
        if days == 1:
            return "1d old"
        return f"{days}d old"
    except Exception:
        return iso


def build_summary(results: list[dict], threshold: int) -> tuple[str, bool]:
    """Returns (message, has_anything_to_report)."""
    needs = [
        r for r in results
        if r["ok"] and (r["open_prs"] or r["stale_branches"] or r["ahead_no_pr"])
    ]
    errors = [r for r in results if not r["ok"]]
    clear = [
        r for r in results
        if r["ok"] and not r["open_prs"] and not r["stale_branches"] and not r["ahead_no_pr"]
    ]

    date_str = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [f"GitHub Morning Report — {date_str}", ""]

    if needs:
        lines.append(f"{len(needs)} repo{'s' if len(needs) != 1 else ''} need updates:")
        lines.append("")
        for r in needs:
            bits = []
            if r["open_prs"]:
                bits.append(f"{len(r['open_prs'])} open PR{'s' if len(r['open_prs']) != 1 else ''}")
            if r["stale_branches"]:
                bits.append(f"{len(r['stale_branches'])} stale branch{'es' if len(r['stale_branches']) != 1 else ''}")
            if r["ahead_no_pr"]:
                bits.append(f"{len(r['ahead_no_pr'])} unmerged branch{'es' if len(r['ahead_no_pr']) != 1 else ''}")
            lines.append(f"• {r['label']} ({r['repo']}): {', '.join(bits)}")

            for pr in r["open_prs"]:
                draft = " [DRAFT]" if pr.get("isDraft") else ""
                author = (pr.get("author") or {}).get("login", "?")
                lines.append(
                    f"   PR #{pr['number']} \"{pr['title']}\" — @{author}, {fmt_age(pr['updatedAt'])}{draft}"
                )
                lines.append(f"      {pr['url']}")

            for sb in r["stale_branches"]:
                lines.append(
                    f"   STALE: {sb['name']} — {sb['behind']} behind {r['default_branch']}"
                    + (f", {sb['ahead']} ahead" if sb["ahead"] else "")
                )

            for ab in r["ahead_no_pr"]:
                lines.append(
                    f"   UNMERGED: {ab['name']} — {ab['ahead']} commits ahead of {r['default_branch']}, no open PR"
                )
            lines.append("")
    else:
        lines.append("All clear — no open PRs, no stale branches.")
        lines.append("")

    if errors:
        lines.append(f"Errors checking {len(errors)} repo(s):")
        for r in errors:
            lines.append(f"  • {r['label']} ({r['repo']}): {r['error']}")
        lines.append("")

    if clear and needs:
        clear_labels = ", ".join(r["label"] for r in clear)
        lines.append(f"All clear: {clear_labels}")

    lines.append(f"\n(Threshold: {threshold}+ commits behind = stale)")

    return "\n".join(lines), bool(needs or errors)


# ---------- Telegram --------------------------------------------------------

def load_telegram_env(env_path: Path) -> tuple[str, str]:
    token = chat_id = ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if k.strip() == "TELEGRAM_BOT_TOKEN":
            token = v
        elif k.strip() == "TELEGRAM_USER_ID":
            chat_id = v
    return token, chat_id


def send_telegram(text: str, env_path: Path) -> bool:
    token, chat_id = load_telegram_env(env_path)
    if not token or not chat_id:
        print("Telegram env missing TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ok = True
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode()
        try:
            resp = urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
            payload = json.loads(resp.read())
            if not payload.get("ok"):
                print(f"Telegram error: {payload}", file=sys.stderr)
                ok = False
        except Exception as e:
            print(f"Telegram send failed: {e}", file=sys.stderr)
            ok = False
    return ok


# ---------- Main ------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print report, skip Telegram.")
    ap.add_argument("--repo", help="Audit only this repo (owner/name).")
    ap.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = ap.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    threshold = int(config.get("stale_threshold_commits", 3))
    repos = config["repos"]
    if args.repo:
        repos = [r for r in repos if r["repo"] == args.repo]
        if not repos:
            print(f"No matching repo in config: {args.repo}", file=sys.stderr)
            return 1

    # Dedupe by repo — multiple labels pointing at the same repo get merged.
    by_repo: dict[str, list[str]] = {}
    for entry in repos:
        if entry.get("skip"):
            continue
        repo = entry["repo"]
        label = entry.get("label", repo)
        by_repo.setdefault(repo, []).append(label)

    results: list[dict] = []
    for repo, labels in by_repo.items():
        label = " / ".join(labels)
        print(f"Auditing {label} ({repo}) ...", file=sys.stderr)
        results.append(audit_repo(repo, label, threshold))

    message, has_signal = build_summary(results, threshold)
    print(message)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    (REPORTS_DIR / f"{stamp}.txt").write_text(message, encoding="utf-8")
    (REPORTS_DIR / f"{stamp}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (REPORTS_DIR / "latest.txt").write_text(message, encoding="utf-8")

    if args.dry_run:
        print("\n[dry-run] Telegram skipped.", file=sys.stderr)
        return 0

    env_path = Path(config.get("telegram", {}).get("env_file", ""))
    if not env_path.exists():
        print(f"Telegram env file not found: {env_path}", file=sys.stderr)
        return 2

    sent = send_telegram(message, env_path)
    return 0 if sent else 3


if __name__ == "__main__":
    sys.exit(main())
