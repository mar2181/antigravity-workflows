#!/usr/bin/env python3
"""
push_rankings_to_supabase.py - Sync keyword_rankings_state.json to Supabase

Reads the local SERP check results written by keyword_rank_tracker.py and
upserts them into the Supabase keyword_rankings table.

Usage:
    python push_rankings_to_supabase.py                  # push ALL clients
    python push_rankings_to_supabase.py --business X     # push one client only
    python push_rankings_to_supabase.py --all-dates      # push every date (not just latest)
    python push_rankings_to_supabase.py --dry-run        # show what would be pushed, no writes
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXECUTION_DIR = Path(__file__).parent
STATE_FILE    = EXECUTION_DIR / "keyword_rankings_state.json"
ENV_PATH      = Path("C:/Users/mario/missioncontrol/dashboard/.env.local")


def load_env(path):
    env = {}
    if not path.exists():
        print(f"[WARN] .env.local not found at {path}", file=sys.stderr)
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def supabase_request(method, url, headers, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "body": json.loads(raw) if raw else []}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return {"ok": False, "status": e.code, "body": raw}
    except Exception as exc:
        return {"ok": False, "status": 0, "body": str(exc)}


def build_headers(service_key):
    return {
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal,resolution=merge-duplicates",
    }


def build_row(client_key, keyword, date_str, data):
    map_pack_pos = data.get("map_pack_position")
    maps_pos     = data.get("maps_position")
    organic_pos  = data.get("organic_position")
    top3_raw     = data.get("top3_map_pack") or data.get("top3_maps_entries") or []
    top3_organic = data.get("top3_organic") or []
    full_organic = data.get("full_organic") or []   # top-10 organic — competitor intel
    full_maps    = data.get("full_maps") or []       # top-20 maps — competitor intel

    # checked_at is a DATE column in Supabase — emit a plain YYYY-MM-DD string
    # so PostgREST stores/compares the value without an implicit timestamp cast.
    try:
        checked_at = datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
    except ValueError:
        checked_at = date_str

    # NOTE: pass top3/top3_organic as native Python lists (not json.dumps strings).
    # The whole request body is already json.dumps'd in supabase_request(), so calling
    # json.dumps here would double-encode the value and Postgres would store the
    # column as a JSON string instead of a JSON array — breaking jsonb_array_length
    # and the UI's Array.isArray() guard.
    return {
        "client_key":        client_key,
        "keyword":           keyword,
        "map_pack_position": map_pack_pos,
        "maps_position":     maps_pos,
        "organic_position":  organic_pos,
        "top3":              top3_raw,
        "top3_organic":      top3_organic,
        "full_organic":      full_organic,
        "full_maps":         full_maps,
        "checked_at":        checked_at,
    }


def write_heartbeat(supabase_url, headers, source, payload):
    """Upsert cron_heartbeats — fire-and-forget; never raise."""
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        row = {"source": source, "last_run_at": now_iso, "payload": payload, "updated_at": now_iso}
        url = f"{supabase_url}/rest/v1/cron_heartbeats?on_conflict=source"
        hb_headers = {**headers, "Prefer": "return=minimal,resolution=merge-duplicates"}
        return supabase_request("POST", url, hb_headers, [row])
    except Exception as exc:
        return {"ok": False, "status": 0, "body": str(exc)}


def upsert_batch(supabase_url, headers, rows):
    """
    Atomic batch UPSERT via Supabase REST. Requires the UNIQUE index on
    (client_key, keyword, checked_at) created in migration 016. The
    resolution=merge-duplicates header (set in build_headers) instructs PostgREST
    to ON CONFLICT UPDATE rather than fail.
    """
    if not rows:
        return {"ok": True, "status": 200, "body": []}
    url = (
        f"{supabase_url}/rest/v1/keyword_rankings"
        f"?on_conflict=client_key,keyword,checked_at"
    )
    return supabase_request("POST", url, headers, rows)


def count_remote_rows(supabase_url, headers, client_key, checked_at):
    """Return the row count for one (client_key, checked_at) tuple, or None on failure."""
    url = (
        f"{supabase_url}/rest/v1/keyword_rankings"
        f"?client_key=eq.{urllib.parse.quote(client_key)}"
        f"&checked_at=eq.{urllib.parse.quote(checked_at)}"
        f"&select=keyword"
    )
    count_headers = {**headers, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"}
    req = urllib.request.Request(url, headers=count_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            cr = resp.headers.get("Content-Range", "")
            if "/" in cr:
                return int(cr.split("/")[-1])
    except Exception as exc:
        print(f"    [WARN] Count check failed: {exc}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Push keyword rankings to Supabase")
    parser.add_argument("--business", help="Only push this client_key (e.g. sugar_shack)")
    parser.add_argument("--all-dates", action="store_true",
                        help="Push every date in state (default: latest date per keyword only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be pushed without writing to Supabase")
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    service_key  = env.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[ERROR] Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local")
        sys.exit(1)

    if not STATE_FILE.exists():
        print(f"[ERROR] State file not found: {STATE_FILE}")
        sys.exit(1)

    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)

    headers = build_headers(service_key)

    clients_to_push = list(state.keys())
    if args.business:
        slug = args.business.lower().replace(" ", "_").replace("-", "_")
        if slug not in state:
            matches = [k for k in state if slug in k]
            if not matches:
                print(f"[ERROR] Client '{args.business}' not found. Available: {list(state.keys())}")
                sys.exit(1)
            slug = matches[0]
            print(f"[INFO] Matched '{args.business}' -> '{slug}'")
        clients_to_push = [slug]

    pushed_ok  = 0
    pushed_err = 0
    mismatches = []

    for client_key in clients_to_push:
        kw_data = state[client_key]
        print(f"\n-- {client_key} ({len(kw_data)} keywords) --")

        # Group rows by date so we can do one batch UPSERT per (client, date) and
        # validate the post-push count against what we expected to push.
        rows_by_date: dict[str, list[dict]] = {}
        expected_keywords_by_date: dict[str, set[str]] = {}

        for keyword, date_data in kw_data.items():
            if not isinstance(date_data, dict):
                # Defensive: some legacy state files carry aggregate keys like
                # "rankings" -> {kw: int} at the keyword level. Skip — those
                # aren't per-date keyword entries.
                print(f"  [SKIP] {keyword!r} -- not a dict (legacy aggregate key)")
                continue
            if not date_data:
                print(f"  [SKIP] {keyword!r} -- no date entries")
                continue
            # Only consider real ISO-date keys (YYYY-MM-DD); other strings are
            # historical pollution from earlier schema versions.
            valid_dates = [k for k, v in date_data.items()
                           if isinstance(k, str) and len(k) == 10 and k[4] == '-' and k[7] == '-'
                           and isinstance(v, dict)]
            if not valid_dates:
                print(f"  [SKIP] {keyword!r} -- no valid date entries")
                continue
            dates_to_push = sorted(valid_dates) if args.all_dates else [max(valid_dates)]
            for date_str in dates_to_push:
                row = build_row(client_key, keyword, date_str, date_data[date_str])
                rows_by_date.setdefault(date_str, []).append(row)
                expected_keywords_by_date.setdefault(date_str, set()).add(keyword)

        for date_str in sorted(rows_by_date.keys()):
            rows = rows_by_date[date_str]
            label = "[DRY RUN] " if args.dry_run else ""
            print(f"  {label}Upsert: {client_key} | {date_str} | {len(rows)} rows")

            if args.dry_run:
                pushed_ok += len(rows)
                continue

            result = upsert_batch(supabase_url, headers, rows)
            if not result["ok"]:
                print(f"    [ERROR] UPSERT failed ({result['status']}): {result['body']}")
                pushed_err += len(rows)
                continue

            pushed_ok += len(rows)

            # Post-push validation: confirm Supabase actually has the rows we
            # expected. Catches silent partial loss (e.g. RLS, constraint
            # rejects). Uses checked_at from the first row's normalized form.
            checked_at_iso = rows[0]["checked_at"]
            remote_count = count_remote_rows(supabase_url, headers, client_key, checked_at_iso)
            expected = len(expected_keywords_by_date[date_str])
            if remote_count is None:
                print(f"    [WARN] Could not verify row count for {client_key} @ {date_str}")
            elif remote_count < expected:
                msg = f"{client_key} @ {date_str}: remote={remote_count} expected>={expected}"
                print(f"    [MISMATCH] {msg}")
                mismatches.append(msg)
            else:
                print(f"    [OK] verified {remote_count} rows in Supabase (>= expected {expected})")

    # Heartbeat — only on real runs that pushed something successfully
    if not args.dry_run and pushed_ok > 0 and pushed_err == 0:
        hb = write_heartbeat(supabase_url, headers, "keyword_rank_tracker",
                             {"pushed": pushed_ok, "clients": len(clients_to_push)})
        if hb.get("ok"):
            print("[heartbeat] keyword_rank_tracker updated")

    label = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{label}Done -- {pushed_ok} pushed OK, {pushed_err} errors")
    if mismatches:
        print(f"\n[MISMATCH SUMMARY] {len(mismatches)} (client,date) tuples below expected count:")
        for m in mismatches:
            print(f"  - {m}")
    if pushed_err > 0 or mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
