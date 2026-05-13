#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Search Console Re-Authentication
========================================
Refreshes the expired GSC OAuth token and saves it to gsc_token.json.
Uses the existing client_id/secret stored in gsc_token.json.

Usage:
  python reauth_gsc.py

Opens a browser tab → log in as the Google account that owns customdesignstx.com →
approve → token saved automatically.

Run this whenever gsc_token.json expires (every ~30 days unless you use a service account).
"""

import json
import os
import sys
import webbrowser
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
EXECUTION_DIR = Path(__file__).parent
TOKEN_FILE    = EXECUTION_DIR / "gsc_token.json"
SCOPES        = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ── Dependency check ────────────────────────────────────────────────────────────
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except ImportError:
    print("[ERROR] Missing dependencies. Run:")
    print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


def load_existing_token() -> dict:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return {}


def save_token(creds: Credentials, account: str = "") -> None:
    token_data = {
        "token":          creds.token,
        "refresh_token":  creds.refresh_token,
        "token_uri":      creds.token_uri,
        "client_id":      creds.client_id,
        "client_secret":  creds.client_secret,
        "scopes":         list(creds.scopes) if creds.scopes else SCOPES,
        "universe_domain": "googleapis.com",
        "account":        account,
        "expiry":         creds.expiry.isoformat() + "Z" if creds.expiry else "",
    }
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"\n[OK] Token saved to: {TOKEN_FILE}")
    print(f"     Account : {account or '(not recorded)'}")
    print(f"     Expiry  : {token_data['expiry']}")


def try_refresh(existing: dict) -> bool:
    """Attempt silent refresh using the existing refresh_token."""
    rt = existing.get("refresh_token")
    if not rt:
        return False
    try:
        creds = Credentials(
            token=existing.get("token"),
            refresh_token=rt,
            token_uri=existing.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=existing.get("client_id"),
            client_secret=existing.get("client_secret"),
            scopes=existing.get("scopes", SCOPES),
        )
        creds.refresh(Request())
        if creds.valid:
            print("[OK] Existing refresh token still valid — token refreshed silently.")
            save_token(creds, existing.get("account", ""))
            return True
    except Exception as e:
        print(f"[INFO] Silent refresh failed ({e}). Full OAuth flow required.")
    return False


def run_full_oauth(existing: dict) -> None:
    """Run the full OAuth browser flow using the known client credentials."""
    client_id     = existing.get("client_id")
    client_secret = existing.get("client_secret")

    if not client_id or not client_secret:
        print("[ERROR] client_id/client_secret not found in gsc_token.json.")
        print("  Add them manually and re-run, or run gsc_auth.py with --client-id and --client-secret.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id":      client_id,
            "client_secret":  client_secret,
            "auth_uri":       "https://accounts.google.com/o/oauth2/auth",
            "token_uri":      "https://oauth2.googleapis.com/token",
            "redirect_uris":  ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
        }
    }

    print("\n" + "=" * 60)
    print("  Google Search Console — Full Re-Authentication")
    print("=" * 60)
    print()
    print("  A browser will open. Log in as the Google account that")
    print("  OWNS the customdesignstx.com Search Console property.")
    print()
    print("  After approving, the token will be saved automatically.")
    print("=" * 60)
    print("\n  Opening browser now...")

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # Try ports until one is free — open_browser=False so URL is printed clearly
    creds = None
    for port in [8090, 8091, 8092, 8093, 8094]:
        try:
            creds = flow.run_local_server(
                port=port,
                prompt="consent",
                open_browser=True,
                success_message="Authentication successful! You can close this tab and return to the terminal."
            )
            break
        except OSError:
            print(f"  [INFO] Port {port} in use, trying next...")
        except Exception as e:
            print(f"  [WARN] Port {port} failed: {e}")

    if creds is None:
        print("[ERROR] Could not bind to any port. Kill any process using ports 8090-8094 and retry.")
        sys.exit(1)

    print("\n[OK] Authentication successful!")

    # Try to get the account email from the token itself, fall back to Mario's known account
    account = getattr(creds, "id_token", {}) or {}
    if isinstance(account, dict):
        account = account.get("email", "marioelizondo81@gmail.com")
    else:
        account = "marioelizondo81@gmail.com"
    save_token(creds, account)

    print()
    print("[NEXT STEPS]")
    print("  1. Open https://search.google.com/search-console")
    print("  2. Verify customdesignstx.com property is confirmed")
    print("  3. Check Coverage report → should show 404s and canonical errors")
    print("  4. Submit sitemap: https://www.customdesignstx.com/sitemap.xml")
    print("  5. Request indexing on the 4 blog posts once they are deployed")


def main():
    print("\n[GSC Re-Auth] Checking existing token...")
    existing = load_existing_token()

    expiry = existing.get("expiry", "")
    print(f"  Token file  : {TOKEN_FILE}")
    print(f"  Expiry      : {expiry or '(unknown)'}")
    print(f"  Account     : {existing.get('account') or '(blank — needs to be set)'}")

    # Try silent refresh first
    if try_refresh(existing):
        print("\n[DONE] Token refreshed. GSC is back online.")
        return

    # Full OAuth flow
    run_full_oauth(existing)


if __name__ == "__main__":
    main()
