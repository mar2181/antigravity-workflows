"""Check 7 — Mission Control dashboard `npm run build` exit code + tail."""

import os
import subprocess
from pathlib import Path

from . import Finding

CHECK_ID = "dashboard_build"
DASHBOARD_DIR = Path("C:/Users/mario/Projects/missioncontrol/dashboard")
BUILD_TIMEOUT_SEC = 300


def _categorize(tail: str) -> tuple[str, str]:
    """Return (root_cause_guess, proposed_fix) heuristically."""
    low = tail.lower()
    if "type error" in low or "typescript error" in low or "ts(" in low:
        return (
            "TypeScript type error in build output",
            f"cd {DASHBOARD_DIR} && npx tsc --noEmit  # locate the failing file:line",
        )
    if "eslint" in low and "error" in low:
        return (
            "ESLint failure during build",
            f"cd {DASHBOARD_DIR} && npm run lint",
        )
    if "module not found" in low or "cannot find module" in low:
        return (
            "Missing module import",
            f"cd {DASHBOARD_DIR} && npm install",
        )
    if "out of memory" in low or "heap" in low:
        return (
            "Node heap exhaustion during build",
            f"cd {DASHBOARD_DIR} && NODE_OPTIONS=--max-old-space-size=8192 npm run build",
        )
    return (
        "Build failure — see tail above",
        f"cd {DASHBOARD_DIR} && npm run build  # reproduce interactively",
    )


def run() -> Finding:
    if not DASHBOARD_DIR.exists():
        return Finding.now(
            id=f"{CHECK_ID}_dir_missing",
            severity="error",
            problem=f"Dashboard dir not found: {DASHBOARD_DIR}",
            root_cause_guess="Working copy moved or never cloned on this machine",
            proposed_fix="git clone Mission Control to C:/Users/mario/Projects/missioncontrol",
        )

    env = os.environ.copy()
    env.setdefault("CI", "1")
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(DASHBOARD_DIR),
            capture_output=True,
            text=True,
            timeout=BUILD_TIMEOUT_SEC,
            shell=True,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return Finding.now(
            id=f"{CHECK_ID}_timeout",
            severity="error",
            problem=f"`npm run build` exceeded {BUILD_TIMEOUT_SEC}s",
            root_cause_guess="Build is hung or genuinely slow",
            proposed_fix=f"cd {DASHBOARD_DIR} && npm run build  # observe interactively",
        )
    except FileNotFoundError:
        return Finding.now(
            id=f"{CHECK_ID}_npm_missing",
            severity="warn",
            problem="`npm` not on PATH — build check skipped",
            root_cause_guess="Node.js not installed or PATH not inherited",
            proposed_fix="Install Node LTS or add npm to PATH",
        )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tail_lines = [ln for ln in combined.splitlines() if ln.strip()][-20:]
    tail = "\n".join(tail_lines)

    if proc.returncode == 0:
        return Finding.now(
            id=f"{CHECK_ID}_ok",
            severity="info",
            problem="Dashboard `npm run build` exited 0",
            root_cause_guess="",
            proposed_fix="",
        )

    last5 = "\n".join(tail_lines[-5:])
    guess, fix = _categorize(tail)
    return Finding.now(
        id=f"{CHECK_ID}_failed",
        severity="error",
        problem=f"Dashboard build failed (exit {proc.returncode})",
        root_cause_guess=f"{guess}. Last lines: {last5}",
        proposed_fix=fix,
    )
