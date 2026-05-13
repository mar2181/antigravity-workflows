"""Check 3 — Mission Control dev server on http://localhost:3001/war-room."""

import socket
import urllib.error
import urllib.request

from . import Finding

CHECK_ID = "mc_dev_server"
TARGET_URL = "http://localhost:3001/war-room"
PROPOSED_FIX = (
    "cd C:/Users/mario/Projects/missioncontrol/dashboard && npm run dev"
)


def run() -> Finding:
    try:
        req = urllib.request.Request(TARGET_URL, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if 200 <= resp.status < 300:
                return Finding.now(
                    id=f"{CHECK_ID}_ok",
                    severity="info",
                    problem=f"MC dev server responded {resp.status} on /war-room",
                    root_cause_guess="",
                    proposed_fix="",
                )
            return Finding.now(
                id=f"{CHECK_ID}_bad_status",
                severity="error",
                problem=f"MC dev server returned HTTP {resp.status} on /war-room",
                root_cause_guess="Dev server up but the route is failing — check build logs",
                proposed_fix="Open the dev server console; check the Next.js terminal for the failing render",
            )
    except urllib.error.HTTPError as exc:
        return Finding.now(
            id=f"{CHECK_ID}_http_error",
            severity="error",
            problem=f"MC dev server returned HTTP {exc.code} on /war-room",
            root_cause_guess=f"Route compiled with errors: {exc.reason}",
            proposed_fix="Open the dev server terminal; investigate the failing route compile",
        )
    except (urllib.error.URLError, socket.timeout, ConnectionError) as exc:
        return Finding.now(
            id=f"{CHECK_ID}_unreachable",
            severity="error",
            problem="MC dev server unreachable on localhost:3001",
            root_cause_guess=f"npm run dev not running. Error: {type(exc).__name__}: {exc}",
            proposed_fix=PROPOSED_FIX,
        )
