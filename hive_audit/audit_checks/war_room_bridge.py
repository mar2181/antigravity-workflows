"""Check 2 — War Room bridge health on http://127.0.0.1:8787."""

import socket
import urllib.error
import urllib.request

from . import Finding

CHECK_ID = "war_room_bridge"
BRIDGE_URLS = [
    "http://127.0.0.1:8787/health",
    "http://127.0.0.1:8787/",
]
PROPOSED_FIX = (
    "cd C:/Users/mario/.claude-worktrees/claudeclaw && python bridge.py  "
    "# adjust to the actual bridge launch command"
)


def run() -> Finding:
    last_err = ""
    for url in BRIDGE_URLS:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if 200 <= resp.status < 300:
                    return Finding.now(
                        id=f"{CHECK_ID}_ok",
                        severity="info",
                        problem=f"War Room bridge responded {resp.status} on {url}",
                        root_cause_guess="",
                        proposed_fix="",
                    )
                last_err = f"HTTP {resp.status} on {url}"
        except urllib.error.HTTPError as exc:
            # A 404 on /health but a running server is still useful info
            if url.endswith("/health") and exc.code == 404:
                last_err = f"HTTP 404 on {url} (server up, no /health endpoint)"
                continue
            last_err = f"HTTPError {exc.code} on {url}"
        except (urllib.error.URLError, socket.timeout, ConnectionError) as exc:
            last_err = f"{type(exc).__name__} on {url}: {exc}"

    return Finding.now(
        id=f"{CHECK_ID}_unreachable",
        severity="error",
        problem="War Room bridge unreachable on http://127.0.0.1:8787",
        root_cause_guess=f"Bridge process not running. Last error: {last_err}",
        proposed_fix=PROPOSED_FIX,
    )
