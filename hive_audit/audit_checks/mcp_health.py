"""Check 1 — MCP health. Invokes `claude mcp list` and flags failed/error MCPs."""

import re
import subprocess

from . import Finding

CHECK_ID = "mcp_health"


def run() -> Finding:
    try:
        proc = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=True,
        )
    except FileNotFoundError:
        return Finding.now(
            id=f"{CHECK_ID}_cli_missing",
            severity="warn",
            problem="`claude` CLI not on PATH — cannot enumerate MCP servers",
            root_cause_guess="Claude Code CLI not installed or not in shell PATH",
            proposed_fix="Install Claude Code or add it to PATH; re-run audit",
        )
    except subprocess.TimeoutExpired:
        return Finding.now(
            id=f"{CHECK_ID}_timeout",
            severity="warn",
            problem="`claude mcp list` timed out after 30s",
            root_cause_guess="MCP enumeration is hung — possibly waiting on a slow MCP server",
            proposed_fix="claude mcp list  # run interactively to inspect",
        )

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0 and not output.strip():
        return Finding.now(
            id=f"{CHECK_ID}_cli_error",
            severity="warn",
            problem=f"`claude mcp list` returned exit {proc.returncode} with no output",
            root_cause_guess="CLI subcommand changed or auth issue",
            proposed_fix="claude mcp list  # run interactively to inspect",
        )

    failing = []
    for line in output.splitlines():
        low = line.lower()
        if "failed" in low or "error" in low or "✗" in line or "✘" in line:
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned:
                failing.append(cleaned)

    if failing:
        sample = "; ".join(failing[:3])
        return Finding.now(
            id=f"{CHECK_ID}_failed_servers",
            severity="error",
            problem=f"{len(failing)} MCP server(s) in failed/error state",
            root_cause_guess=f"Lines flagged: {sample}",
            proposed_fix="claude mcp list  # inspect; then re-add or restart the failing server",
        )

    return Finding.now(
        id=f"{CHECK_ID}_ok",
        severity="info",
        problem="All MCP servers reporting healthy",
        root_cause_guess="",
        proposed_fix="",
    )
