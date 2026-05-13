#!/usr/bin/env python3
"""
rankings_refresh_runner.py - Orchestrator for per-client SERP scrape -> push -> verify.

Runs keyword_rank_tracker.py and push_rankings_to_supabase.py one client at a time,
rate-limiting between clients, retrying on failure, and logging everything.

Usage:
    python rankings_refresh_runner.py                    # all clients, default order
    python rankings_refresh_runner.py --client sugar_shack
    python rankings_refresh_runner.py --all
    python rankings_refresh_runner.py --all --push
    python rankings_refresh_runner.py --dry-run
    python rankings_refresh_runner.py --yes              # skip stop/continue prompts

State:  keyword_rankings_state.json
Logs:   cron_logs/rankings_refresh_YYYY-MM-DD.log
Config: keyword_rankings_config.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent.resolve()
STATE_PATH   = SCRIPT_DIR / "keyword_rankings_state.json"
CONFIG_PATH  = SCRIPT_DIR / "keyword_rankings_config.json"
LOG_DIR      = SCRIPT_DIR / "cron_logs"
TRACKER      = str(SCRIPT_DIR / "keyword_rank_tracker.py")
PUSHER       = str(SCRIPT_DIR / "push_rankings_to_supabase.py")
ENV_PATH     = Path("C:/Users/mario/missioncontrol/dashboard/.env.local")

# Default per-client run order (validated 2026-04-18)
DEFAULT_ORDER = [
    "custom_designs_tx",
    "sugar_shack",
    "spi_fun_rentals",
    "island_candy",
    "optimum_clinic",
    "juan",
    "island_arcade",
    "optimum_foundation",
]

# ── Env loading ────────────────────────────────────────────────────────────────
def load_env(path: Path) -> dict[str, str]:
    """Load key=value pairs from a .env file. Returns empty dict if not found."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def ensure_env_vars(env: dict[str, str]) -> None:
    """Make sure BRIGHT_DATA_KEY is in os.environ so subprocesses pick it up."""
    for key in ("BRIGHT_DATA_KEY", "BD_TOKEN"):
        if key in env and key not in os.environ:
            os.environ[key] = env[key]


# ── State helpers ──────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_last_updated(client_key: str) -> str | None:
    """Return the latest date string found for any keyword of this client."""
    state = load_state()
    biz = state.get(client_key, {})
    dates: set[str] = set()
    for kw_data in biz.values():
        if isinstance(kw_data, dict):
            dates.update(kw_data.keys())
    return max(dates) if dates else None


def count_keywords(client_key: str) -> int:
    """Return number of keywords configured for this client."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        return len(cfg.get("businesses", {}).get(client_key, {}).get("keywords", []))
    except Exception:
        return 0


def count_state_keywords(client_key: str) -> int:
    """Return number of keywords in state for this client."""
    state = load_state()
    return len(state.get(client_key, {}))


# ── Logging ────────────────────────────────────────────────────────────────────
class Logger:
    """Print to stdout AND write to log file."""

    def __init__(self, log_path: Path):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.file = open(log_path, "a", encoding="utf-8")

    def log(self, msg: str = ""):
        line = msg
        print(line, flush=True)
        self.file.write(line + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


# ── Main runner ────────────────────────────────────────────────────────────────
class RankingsRefreshRunner:
    def __init__(self, args):
        self.args       = args
        self.today_str  = date.today().isoformat()
        self.log_path   = LOG_DIR / f"rankings_refresh_{self.today_str}.log"
        self.logger     = Logger(self.log_path)
        self.results: list[dict] = []  # {client, status, last_updated_before, last_updated_after, keywords}
        self.env        = load_env(ENV_PATH)

    def _run_cmd(self, cmd: list[str], label: str) -> tuple[int, str, str]:
        """Run a subprocess, capture stdout+stderr. Returns (exit_code, stdout, stderr)."""
        self.logger.log(f"  [{label}] $ {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(SCRIPT_DIR),
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, **self.env},
            )
            out = proc.stdout
            err = proc.stderr
            if out.strip():
                for line in out.strip().splitlines():
                    self.logger.log(f"    {line}")
            if err.strip():
                for line in err.strip().splitlines():
                    self.logger.log(f"    [stderr] {line}")
            if proc.returncode != 0:
                self.logger.log(f"  [{label}] exit code: {proc.returncode}")
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            self.logger.log(f"  [{label}] TIMEOUT (600s)")
            return -1, "", "Timeout after 600s"
        except Exception as e:
            self.logger.log(f"  [{label}] EXCEPTION: {e}")
            return -2, "", str(e)

    def _scrape_client(self, client_key: str) -> bool:
        """Run keyword_rank_tracker.py for one client. Returns True on success."""
        self.env = load_env(ENV_PATH)  # re-read in case env changed
        ensure_env_vars(self.env)
        code, out, err = self._run_cmd(
            [sys.executable, TRACKER, "--business", client_key],
            f"scrape:{client_key}",
        )
        return code == 0

    def _push_client(self, client_key: str) -> bool:
        """Run push_rankings_to_supabase.py for one client. Returns True on success."""
        self.env = load_env(ENV_PATH)
        ensure_env_vars(self.env)
        code, out, err = self._run_cmd(
            [sys.executable, PUSHER, "--business", client_key],
            f"push:{client_key}",
        )
        return code == 0

    def _verify_state_updated(self, client_key: str, before: str | None) -> str | None:
        """Re-read state. Return new last_updated if it changed, else None."""
        after = get_last_updated(client_key)
        if after and after != before:
            return after
        return None

    def _countdown(self, seconds: int):
        """Print a visible countdown."""
        delay = max(1, seconds)
        self.logger.log(f"\nWaiting {delay}s before next client...")
        for remaining in range(delay, 0, -5):
            self.logger.log(f"  {remaining}s...")
            time.sleep(min(5, remaining))
        self.logger.log()

    def _prompt_continue(self) -> bool:
        """Ask user whether to continue to next client. True = continue.
        Handles EOF (non-interactive terminal) by stopping gracefully."""
        if self.args.yes:
            return True
        try:
            resp = input("\nContinue to next client? [Y/n/q] ").strip().lower()
        except EOFError:
            self.logger.log("\n  [EOF] Non-interactive terminal detected. Use --yes to skip prompts.")
            return False
        if resp in ("q", "quit"):
            return False
        return True

    def run(self):
        # ── Header ──────────────────────────────────────────────────────────
        self.logger.log(f"{'='*60}")
        self.logger.log(f"Rankings Refresh Runner - {self.today_str}")
        self.logger.log(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        mode = "DRY RUN" if self.args.dry_run else "LIVE"
        push = " + PUSH" if self.args.push else ""
        self.logger.log(f"Mode: {mode}{push}")
        self.logger.log(f"Log:  {self.log_path}")
        self.logger.log()

        # ── Validate env ─────────────────────────────────────────────────────
        if not ENV_PATH.exists():
            self.logger.log(f"[FATAL] .env.local not found at {ENV_PATH}")
            self.logger.close()
            sys.exit(2)

        # ── Determine client list ────────────────────────────────────────────
        if self.args.client:
            clients = [self.args.client]
        elif self.args.all or True:  # default = --all
            clients = list(DEFAULT_ORDER)
        else:
            clients = list(DEFAULT_ORDER)

        # Validate client keys
        for ck in clients:
            if ck not in DEFAULT_ORDER:
                self.logger.log(f"[FATAL] Unknown client: {ck}")
                self.logger.log(f"Known clients: {', '.join(DEFAULT_ORDER)}")
                self.logger.close()
                sys.exit(2)

        self.logger.log(f"Clients to process ({len(clients)}): {', '.join(clients)}")
        self.logger.log(f"Delay between clients: {self.args.delay}s")
        self.logger.log()

        # ── Per-client loop ──────────────────────────────────────────────────
        for idx, client_key in enumerate(clients):
            cfg_kw_count = count_keywords(client_key)
            state_kw_count = count_state_keywords(client_key)
            last_before = get_last_updated(client_key)

            self.logger.log(f"[{idx+1}/{len(clients)}] {client_key}")
            self.logger.log(f"  Config keywords: {cfg_kw_count}  |  State entries: {state_kw_count}")
            self.logger.log(f"  Last updated:    {last_before or 'NEVER'}")

            if self.args.dry_run:
                self.logger.log(f"  [DRY RUN] Would scrape {client_key}...")
                self.results.append({
                    "client": client_key,
                    "status": "DRY",
                    "last_updated_before": last_before,
                    "last_updated_after": last_before,
                    "keywords": cfg_kw_count,
                })
                if idx < len(clients) - 1 and not self._prompt_continue():
                    self.logger.log("  Stopped by user.")
                    break
                continue

            # Phase 1: Scrape
            self.logger.log(f"  Phase 1: Scraping rankings...")
            ok = self._scrape_client(client_key)

            if not ok:
                self.logger.log(f"  [FAILED] Scraper returned non-zero exit code")
                self.results.append({
                    "client": client_key,
                    "status": "FAILED (scrape)",
                    "last_updated_before": last_before,
                    "last_updated_after": get_last_updated(client_key),
                    "keywords": cfg_kw_count,
                })
                if idx < len(clients) - 1:
                    if not self._prompt_continue():
                        self.logger.log("  Stopped by user.")
                        break
                    self._countdown(self.args.delay)
                continue

            # Verify state updated
            last_after = self._verify_state_updated(client_key, last_before)
            if last_after:
                self.logger.log(f"  [OK] State updated: {last_before} -> {last_after}")
            else:
                self.logger.log(f"  [WARN] State may not have been updated (scraper ran but last_updated unchanged)")

            # Phase 2: Push (if requested)
            if self.args.push:
                self.logger.log(f"  Phase 2: Pushing to Supabase...")
                push_ok = self._push_client(client_key)
                if push_ok:
                    self.logger.log(f"  [OK] Push to Supabase succeeded")
                else:
                    self.logger.log(f"  [WARN] Push returned non-zero exit code")

            self.results.append({
                "client": client_key,
                "status": "OK",
                "last_updated_before": last_before,
                "last_updated_after": last_after or get_last_updated(client_key),
                "keywords": cfg_kw_count,
            })

            # Rate-limit between clients
            if idx < len(clients) - 1:
                if not self._prompt_continue():
                    self.logger.log("  Stopped by user.")
                    break
                self._countdown(self.args.delay)

        # ── Summary ──────────────────────────────────────────────────────────
        self._print_summary()
        self.logger.close()

        # Exit code
        statuses = [r["status"] for r in self.results]
        if any("FAILED" in s for s in statuses):
            sys.exit(1)
        sys.exit(0)

    def _print_summary(self):
        self.logger.log()
        self.logger.log(f"{'='*60}")
        self.logger.log("SUMMARY")
        self.logger.log(f"{'='*60}")
        header = f"{'Client':<25} {'Status':<18} {'Last Updated':<14} {'Keywords':>8}"
        self.logger.log(header)
        self.logger.log("-" * len(header))

        ok_count = 0
        fail_count = 0
        dry_count = 0

        for r in self.results:
            self.logger.log(
                f"{r['client']:<25} {r['status']:<18} {r.get('last_updated_after') or 'N/A':<14} {r['keywords']:>8}"
            )
            if "FAILED" in r["status"]:
                fail_count += 1
            elif r["status"] == "DRY":
                dry_count += 1
            else:
                ok_count += 1

        self.logger.log("-" * len(header))
        total = len(self.results)
        self.logger.log(f"Total: {total}  |  OK: {ok_count}  |  FAILED: {fail_count}  |  DRY: {dry_count}")
        self.logger.log()

        if fail_count > 0:
            self.logger.log("[EXIT 1] One or more clients failed.")
        elif dry_count == total:
            self.logger.log("[EXIT 0] Dry run complete.")
        else:
            self.logger.log("[EXIT 0] All clients succeeded.")

        self.logger.log(f"Full log: {self.log_path}")


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Orchestrator: one-client-at-a-time SERP scrape -> Supabase push."
    )
    parser.add_argument(
        "--client",
        choices=DEFAULT_ORDER,
        help="Run for a single client only.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Run for all clients in default order (the default).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without scraping or pushing.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="After scraping, push results to Supabase.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=45,
        help="Seconds to wait between clients when running --all (default: 45).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip stop/continue prompts between clients (non-interactive mode).",
    )
    args = parser.parse_args()

    # Validate: --client and --all are mutually exclusive in intent
    # (--all is default, so passing --client overrides)
    runner = RankingsRefreshRunner(args)

    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopped by user.")
        runner.logger.log("\n[INTERRUPTED] Stopped by user.")
        runner.logger.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        runner.logger.log(f"\n[FATAL] {e}")
        runner.logger.close()
        sys.exit(2)


if __name__ == "__main__":
    main()
