#!/usr/bin/env python3
"""
gbp_auth_setup.py — One-time Google Business Profile OAuth setup

Run ONCE per account to generate tokens with business.manage scope.
Tokens auto-refresh forever after that.

Usage:
    python gbp_auth_setup.py --account mario    → saves token_mario_gbp.json
    python gbp_auth_setup.py --account yehuda   → saves token_yehuda_gbp.json
    python gbp_auth_setup.py --verify           → test both tokens, list accounts + locations
"""

import argparse
import sys
from pathlib import Path

EXECUTION_DIR = Path(__file__).parent
CREDENTIALS_FILE = Path.home() / ".config" / "gws" / "client_secret_desktop.json"
SCOPES = ["https://www.googleapis.com/auth/business.manage"]

ACCOUNTS = {
    "mario":  {"token_file": EXECUTION_DIR / "token_mario_gbp.json",  "hint": "marioelizondo81@gmail.com"},
    "yehuda": {"token_file": EXECUTION_DIR / "token_yehuda_gbp.json", "hint": "quepadre@live.com"},
}


def get_credentials(account: str):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    cfg = ACCOUNTS[account]
    token_path = cfg["token_file"]
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"[{account}] Refreshing expired token...")
            creds.refresh(Request())
        else:
            print(f"\n[{account}] Starting OAuth flow for {cfg['hint']}...")
            print(f"Browser will open — log in as {cfg['hint']}\n")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                scopes=SCOPES,
            )
            creds = flow.run_local_server(port=0, prompt="consent")

        token_path.write_text(creds.to_json())
        print(f"[{account}] Token saved -> {token_path.name}")

    return creds


def build_service(creds):
    import googleapiclient.discovery
    # Suppress noisy cache warning
    import logging
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    return googleapiclient.discovery.build(
        "mybusiness", "v4",
        credentials=creds,
        discoveryServiceUrl="https://mybusiness.googleapis.com/$discovery/rest?version=v4",
        static_discovery=False,
    )


def verify_account(account: str) -> dict:
    """Fetch account list and location names — returns {accountId: [locationName, ...]}"""
    import requests

    cfg = ACCOUNTS[account]
    token_path = cfg["token_file"]

    if not token_path.exists():
        print(f"[{account}] No token found — run: python gbp_auth_setup.py --account {account}")
        return {}

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())

    headers = {"Authorization": f"Bearer {creds.token}"}

    # List accounts
    r = requests.get("https://mybusinessaccountmanagement.googleapis.com/v1/accounts", headers=headers)
    if r.status_code != 200:
        print(f"[{account}] accounts.list failed: {r.status_code} {r.text[:200]}")
        return {}

    accounts_data = r.json().get("accounts", [])
    result = {}
    for acct in accounts_data:
        acct_name = acct["name"]  # e.g. accounts/12345678
        acct_id   = acct_name.split("/")[-1]
        print(f"  [Account] {acct.get('accountName', '?')} — {acct_name}")

        # List locations
        loc_url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{acct_name}/locations?readMask=name,title,storeCode"
        lr = requests.get(loc_url, headers=headers)
        locations = []
        if lr.status_code == 200:
            for loc in lr.json().get("locations", []):
                loc_name = loc["name"]  # accounts/.../locations/...
                title    = loc.get("title", "?")
                print(f"    [Location] {title} — {loc_name}")
                locations.append({"name": loc_name, "title": title})
        else:
            print(f"    locations.list failed: {lr.status_code} {lr.text[:100]}")

        result[acct_id] = {"account_name": acct_name, "locations": locations}

    return result


def setup_account(account: str) -> None:
    if not CREDENTIALS_FILE.exists():
        sys.exit(f"ERROR: client_secret.json not found at {CREDENTIALS_FILE}")

    print(f"\n=== Setting up GBP OAuth for: {account} ===")
    get_credentials(account)
    print(f"\n[{account}] Auth successful! Testing connection...")
    data = verify_account(account)
    if data:
        print(f"\n[{account}] Connected to {len(data)} Google Account(s).")
        print(f"\n✅ {account} setup complete. Token saved at: {ACCOUNTS[account]['token_file'].name}")
        print("\nAuto-running --setup-locations to map GBP location IDs...")
        try:
            import importlib.util
            watcher_path = EXECUTION_DIR / "gbp_review_watcher.py"
            if watcher_path.exists():
                spec = importlib.util.spec_from_file_location("gbp_review_watcher", str(watcher_path))
                watcher = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(watcher)
                state = watcher.load_state()
                watcher.setup_locations(state)
                watcher.save_state(state)
                print("Location IDs saved to gbp_review_state.json")
        except Exception as e:
            print(f"Note: setup-locations skipped ({e}). Run manually: python gbp_review_watcher.py --setup-locations")
    else:
        print(f"\n⚠️  Auth succeeded but could not list accounts. Check API access.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GBP OAuth Setup")
    parser.add_argument("--account", choices=["mario", "yehuda"], help="Account to set up")
    parser.add_argument("--verify", action="store_true", help="Verify existing tokens and list locations")
    args = parser.parse_args()

    if args.verify:
        for acct_name in ["mario", "yehuda"]:
            print(f"\n=== Verifying: {acct_name} ===")
            verify_account(acct_name)
    elif args.account:
        setup_account(args.account)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python gbp_auth_setup.py --account mario")
        print("  python gbp_auth_setup.py --account yehuda")
        print("  python gbp_auth_setup.py --verify")
