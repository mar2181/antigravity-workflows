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


# ── Failed-check detection ─────────────────────────────────────────────────────
# Evidence keys, ALL of them. The organic pair was added 2026-07-21; snapshots
# older than that legitimately carry only map evidence, so an organic-only test
# would discard real ranking history — measured: 662 April/May snapshots, several
# holding a confirmed map_pack_position with is_ours=True.
_EVIDENCE_KEYS = ("top3_organic", "full_organic",
                  "top3_map_pack", "top3_maps_entries", "full_maps")
_POSITION_KEYS = ("map_pack_position", "maps_position", "organic_position")


def snapshot_failed(snap):
    """
    True if this snapshot is a FAILED CHECK rather than a real "ranks nowhere".
    Returns (failed: bool, reason: str).

    ⛔ THE DISCRIMINATOR IS NOT `position is None`. A business genuinely can rank
    for nothing, and saying so plainly is the whole job of this tracker —
    suppressing it would be the same lie reversed. A real Google fetch ALWAYS
    brings competitors back, so the tell is a snapshot carrying NO SERP evidence
    at all AND no measured position.

    Both tests are required, and that is measured, not assumed. Against the live
    state file (13,211 snapshots, 2026-08-06):

        error set + no evidence ......  7,522   agree -> failed
        error set + evidence .........      0   the flag NEVER fires on real data
        no error  + no evidence/pos ..     41   SILENT failures the flag MISSES
        no error  + evidence .........  5,648   agree -> good

    So `error` is perfectly SPECIFIC (no false positives) but not SUFFICIENT:
    41 snapshots have no error recorded and no data either — a parse that came
    back empty from a 200 body, which is exactly how a Google layout change or a
    provider returning a stub page presents. Those are the rows that would reach
    a client dashboard as "stopped ranking for everything".

    A snapshot with an actual POSITION but empty evidence lists still counts as a
    real measurement (3 in the state file) — the scraper plainly saw results.
    Verified safe in the other direction too: ZERO errored snapshots carry a
    position, so this rescue can never resurrect a failed check.
    """
    if not isinstance(snap, dict):
        return True, "not a dict"
    err = snap.get("error")
    if err:
        return True, f"error: {str(err)[:60]}"
    if any(snap.get(k) for k in _EVIDENCE_KEYS):
        return False, ""
    if any(snap.get(k) is not None for k in _POSITION_KEYS):
        return False, ""
    return True, "no SERP evidence and no position (silent failure)"


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


# ── Schema compatibility ──────────────────────────────────────────────────────
# Columns the pusher will SEND ONLY IF THE TABLE HAS THEM. These carry competitor
# intel; the client's own ranking is in the core columns and must never be held
# hostage to them.
#
# ⛔ THIS EXISTS BECAUSE IT ALREADY HAPPENED, AND IT COST 16 DAYS OF CLIENT DATA.
# 2026-07-21, commit e23d97b added `full_organic` and `full_maps` to build_row()
# for competitor intel. The Supabase migration was never applied. PostgREST
# rejects the WHOLE batch on an unknown column:
#     400 PGRST204 "Could not find the 'full_maps' column of 'keyword_rankings'"
# so every push failed 529/529 from that day. The newest row in the table was
# 2026-07-20 -- the last day before the commit.
#
# ⛔ AND THE SECOND FAILURE HID THE FIRST. On 2026-07-26 Bright Data died, so the
# gate in run_rank_tracker.bat began refusing to push at all -- which meant the
# 400 STOPPED APPEARING IN THE LOGS. From then on the only visible symptom was
# "the scraper is failing", a complete and plausible explanation that was wrong.
# Fixing the scraper would have restored nothing.
#
# So: probe the schema once, drop what the table cannot store, push the rankings
# anyway, and SAY SO LOUDLY. Silence here would be the same class of bug -- the
# intel would quietly stop being collected. The moment the migration lands, the
# probe sees the columns and they start flowing again with no code change.
OPTIONAL_COLUMNS = ("full_organic", "full_maps")


def detect_missing_columns(supabase_url, headers):
    """
    Return the subset of OPTIONAL_COLUMNS the live table does NOT have.

    Probes one real row rather than trusting a migration file on disk -- the
    file being present says nothing about whether it was ever applied, which is
    exactly the gap that caused this. On any probe failure returns () so a
    transient network blip degrades to "send everything" (today's behaviour)
    rather than silently stripping columns that do exist.
    """
    url = f"{supabase_url}/rest/v1/keyword_rankings?select=*&limit=1"
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[WARN] Could not probe table schema ({exc}) -- sending all columns.")
        return ()
    if not rows:
        return ()          # empty table tells us nothing; send everything
    present = set(rows[0].keys())
    return tuple(c for c in OPTIONAL_COLUMNS if c not in present)


def strip_columns(rows, cols):
    """Remove `cols` from every row. No-op when cols is empty."""
    if not cols:
        return rows
    return [{k: v for k, v in r.items() if k not in cols} for r in rows]


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

    # Probe the live schema ONCE, before any write. See OPTIONAL_COLUMNS.
    missing_cols = detect_missing_columns(supabase_url, headers)
    if missing_cols:
        print(f"[SCHEMA] This table has no {', '.join(missing_cols)} column(s). "
              f"Rankings WILL be pushed; competitor-intel payload will NOT be stored.")
        print(f"[SCHEMA] To store it, apply:  ALTER TABLE keyword_rankings")
        for c in missing_cols:
            print(f"[SCHEMA]     ADD COLUMN IF NOT EXISTS {c} jsonb;")

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
    frozen     = []   # (client, keyword, newest_date, why) — every snapshot failed
    stale      = []   # (client, keyword, pushed_date, newest_date) — fell back

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
            # ⛔ NEVER push a failed check. This used to be an unconditional
            # `max(valid_dates)`, so the newest snapshot won even when it was a
            # provider outage — landing null positions and empty top3 as the most
            # recent row, which every consumer reads as "this business stopped
            # ranking for everything". Nothing downstream can tell that apart
            # from a true zero.
            #
            # The run-level gate in run_rank_tracker.bat (exit 3 at >=50% errors)
            # is real and has held Supabase clean for 11 days — but it is
            # ALL-OR-NOTHING and cannot help a PARTIAL failure. Measured:
            # 2026-07-25 failed 117/239 = 49.0%, i.e. it passes that gate and
            # writes 117 fake zeros. Bright Data's measured blip rate is ~1-in-3,
            # which sits squarely in that unprotected band. Per-keyword is the
            # only layer where a partial failure can be made safe.
            usable = [d for d in sorted(valid_dates)
                      if not snapshot_failed(date_data[d])[0]]
            if not usable:
                # Every snapshot for this keyword is a failed check. Push NOTHING
                # and leave the last good row in Supabase standing. ⛔ Do not
                # re-stamp an old snapshot with today's date: that fabricates a
                # measurement nobody took. A stale `checked_at` is honest; a
                # fresh date on old data is not.
                newest = max(valid_dates)
                frozen.append((client_key, keyword, newest,
                               snapshot_failed(date_data[newest])[1]))
                continue
            dates_to_push = usable if args.all_dates else [usable[-1]]
            for date_str in dates_to_push:
                if date_str != max(valid_dates):
                    stale.append((client_key, keyword, date_str, max(valid_dates)))
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

            result = upsert_batch(supabase_url, headers,
                                  strip_columns(rows, missing_cols))
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

    # ── Frozen / stale reporting ───────────────────────────────────────────────
    # A frozen keyword is the pusher working CORRECTLY, not an error — but it
    # must never be silent. "Rankings did not update today" and "rankings updated
    # and everything is fine" are the two readings that have to stay
    # distinguishable, and only this block distinguishes them.
    if frozen:
        by_client = {}
        for ck, kw, dt, why in frozen:
            by_client.setdefault(ck, []).append((kw, dt, why))
        print(f"\n[FROZEN] {len(frozen)} keyword(s) had NO usable snapshot -- "
              f"nothing pushed, last good row left standing in Supabase:")
        for ck in sorted(by_client):
            items = by_client[ck]
            newest = max(d for _, d, _ in items)
            print(f"  - {ck}: {len(items)} keyword(s), newest failed snapshot {newest}")
            print(f"      e.g. {items[0][0]!r} -> {items[0][2]}")
    if stale:
        print(f"\n[STALE] {len(stale)} keyword(s) fell back to an older good "
              f"snapshot because the newest one was a failed check.")

    total_kw = pushed_ok + len(frozen)
    frozen_share = (len(frozen) / total_kw) if total_kw else 0.0

    # Heartbeat — only on real runs that pushed something successfully.
    # ⛔ The frozen count travels in the payload and a majority-frozen run does
    # NOT get a clean heartbeat. A monitor that sees "keyword_rank_tracker ran"
    # while 90% of keywords were skipped is the same dead-API-reports-success
    # class this whole guard exists to close.
    if not args.dry_run and pushed_ok > 0 and pushed_err == 0 and frozen_share < 0.5:
        hb = write_heartbeat(supabase_url, headers, "keyword_rank_tracker",
                             {"pushed": pushed_ok, "clients": len(clients_to_push),
                              "frozen": len(frozen), "stale": len(stale)})
        if hb.get("ok"):
            print("[heartbeat] keyword_rank_tracker updated")
    elif not args.dry_run and frozen_share >= 0.5:
        print(f"[heartbeat] SUPPRESSED -- {frozen_share:.0%} of keywords frozen; "
              f"this was not a healthy run.")

    label = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{label}Done -- {pushed_ok} pushed OK, {pushed_err} errors, "
          f"{len(frozen)} frozen, {len(stale)} stale")
    if mismatches:
        print(f"\n[MISMATCH SUMMARY] {len(mismatches)} (client,date) tuples below expected count:")
        for m in mismatches:
            print(f"  - {m}")
    if pushed_err > 0 or mismatches:
        sys.exit(1)
    # Nothing pushed at all, and only because every snapshot was a failed check:
    # the run genuinely accomplished nothing and must not read as success.
    if frozen and pushed_ok == 0:
        print("\n[FATAL] Every keyword was a failed check -- nothing pushed. Exit 4.")
        sys.exit(4)


if __name__ == "__main__":
    main()
