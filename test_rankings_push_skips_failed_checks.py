#!/usr/bin/env python3
"""
Guard: push_rankings_to_supabase.py must never push a FAILED CHECK as a ranking,
and must never suppress a TRUE ZERO.

    python test_rankings_push_skips_failed_checks.py

Why this exists
---------------
2026-07-26 -> 2026-08-03: every keyword scrape errored for 11 straight days. The
pusher selected `max(valid_dates)` unconditionally, so the newest snapshot won
even when it was a provider outage — null positions, empty top3. Measured
against the real state file, that rule would have pushed 529 rows of which
**472 (89%) were fake zeros**: six clients reading "stopped ranking for
everything" on the dashboard, indistinguishable from a real collapse.

The run-level gate in run_rank_tracker.bat (exit 3 at >=50% errors) is real and
held Supabase clean through the total outage — but it is ALL-OR-NOTHING. On
2026-07-25 the failure rate was 117/239 = 49.0%, which PASSES that gate and
writes 117 fake zeros. Bright Data's measured blip rate is ~1-in-3, squarely in
that unprotected band. Per-keyword filtering is the only layer where a partial
failure can be made safe.

THE TRAP THIS GUARD PROTECTS BOTH WAYS
--------------------------------------
Suppressing a true zero is the SAME LIE REVERSED. A business genuinely can rank
for nothing and the owner must be told so, with today's date. The discriminator
is therefore NOT `position is None` — it is the absence of SERP EVIDENCE. A real
Google fetch always brings competitors back; a failed one brings nothing.
Case C below is the one that keeps this honest, and it must never be "fixed" by
loosening it.
"""
import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).parent


def load_module():
    spec = importlib.util.spec_from_file_location(
        "pusher", HERE / "push_rankings_to_supabase.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail and not cond else ""))


# ── Fixtures: one snapshot of each real-world shape ────────────────────────────
COMPETITORS = [{"title": "Some Rival", "url": "https://rival.com", "is_ours": False}]

SNAP_ERRORED = {                      # provider died — the 11-day outage shape
    "map_pack_position": None, "maps_position": None, "organic_position": None,
    "top3_map_pack": [], "top3_maps_entries": [], "top3_organic": [],
    "full_organic": [], "full_maps": [], "error": "serper HTTP 400",
}
SNAP_SILENT = {                       # 200 body, empty parse — NO error recorded
    "map_pack_position": None, "maps_position": None, "organic_position": None,
    "top3_map_pack": [], "top3_maps_entries": [], "top3_organic": [],
    "full_organic": [], "full_maps": [], "error": None,
}
SNAP_TRUE_ZERO = {                    # real check, we genuinely rank nowhere
    "map_pack_position": None, "maps_position": None, "organic_position": None,
    "top3_map_pack": [], "top3_maps_entries": [], "top3_organic": COMPETITORS,
    "full_organic": COMPETITORS, "full_maps": [], "error": None,
}
SNAP_GOOD = {                         # real check, we rank
    "map_pack_position": 2, "maps_position": 2, "organic_position": 5,
    "top3_map_pack": [{"name": "Us", "is_ours": True}], "top3_maps_entries": [],
    "top3_organic": COMPETITORS, "full_organic": COMPETITORS, "full_maps": [],
    "error": None,
}
SNAP_LEGACY_MAP = {                   # pre-2026-07-21 schema: map evidence only
    "map_pack_position": 3, "maps_position": 3, "organic_position": None,
    "top3_map_pack": [{"name": "Us", "is_ours": True}], "error": None,
}
SNAP_POS_NO_LISTS = {                 # a measured position, lists empty
    "map_pack_position": None, "maps_position": 9, "organic_position": None,
    "top3_map_pack": [], "error": None,
}


def test_classifier(m):
    print("\n[1] snapshot_failed() classifies each real-world shape")
    check("errored snapshot -> failed", m.snapshot_failed(SNAP_ERRORED)[0])
    check("silent empty parse -> failed (error flag MISSES this)",
          m.snapshot_failed(SNAP_SILENT)[0])
    check("TRUE ZERO (competitors present, we rank nowhere) -> NOT failed, must be pushed",
          not m.snapshot_failed(SNAP_TRUE_ZERO)[0])
    check("good ranking -> not failed", not m.snapshot_failed(SNAP_GOOD)[0])
    check("legacy map-only snapshot -> not failed (organic-only test would discard it)",
          not m.snapshot_failed(SNAP_LEGACY_MAP)[0])
    check("position but empty lists -> not failed (rescue)",
          not m.snapshot_failed(SNAP_POS_NO_LISTS)[0])
    check("non-dict -> failed", m.snapshot_failed(None)[0])
    check("failure reason is non-empty", bool(m.snapshot_failed(SNAP_ERRORED)[1]))


def run_dry(m, state):
    """Drive the REAL main() selection logic over a fixture state file."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "state.json"
        p.write_text(json.dumps(state), encoding="utf-8")
        old_state, old_argv = m.STATE_FILE, sys.argv
        m.STATE_FILE = p
        sys.argv = ["push", "--dry-run"]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                m.main()
        except SystemExit:
            pass
        finally:
            m.STATE_FILE, sys.argv = old_state, old_argv
        return buf.getvalue()


def test_selection(m):
    print("\n[2] selection: newest-failed falls back, all-failed freezes")
    out = run_dry(m, {"acme": {
        # newest is a failed check, an older good one exists -> push the OLD one
        "kw_fallback": {"2026-07-20": SNAP_GOOD, "2026-08-03": SNAP_ERRORED},
        # every snapshot failed -> push NOTHING, leave Supabase standing
        "kw_frozen":   {"2026-07-20": SNAP_ERRORED, "2026-08-03": SNAP_SILENT},
        # a genuine zero must still go out, dated today
        "kw_truezero": {"2026-08-03": SNAP_TRUE_ZERO},
    }})
    # ⛔ Parse the UPSERT LINES, never scan the whole output. The first draft of
    # this check counted occurrences of the date string across all stdout and
    # went red on correct code, because the FROZEN diagnostic *names* the failed
    # date ("newest failed snapshot 2026-08-03"). A guard that reads the message
    # explaining the fix as evidence of the bug will be "fixed" by deleting the
    # message — which removes the only thing making the freeze visible.
    ups = {}
    for line in out.splitlines():
        if "Upsert:" in line:
            parts = [p.strip() for p in line.split("|")]
            ups[parts[1]] = int(parts[2].split()[0])
    check("falls back to the older good date (2026-07-20 pushed)",
          ups.get("2026-07-20") == 1, str(ups))
    check("does NOT push the failed newest date for the fallback keyword "
          "(2026-08-03 carries the true zero ONLY, so exactly 1 row)",
          ups.get("2026-08-03") == 1, str(ups))
    check("exactly two upsert dates, nothing else leaked in", len(ups) == 2, str(ups))
    check("reports 1 frozen keyword", "1 frozen" in out, out)
    check("reports the frozen keyword by name", "kw_frozen" in out, out)
    check("names WHY it froze", "silent failure" in out or "error:" in out, out)
    check("reports the stale fallback", "1 stale" in out, out)
    check("TRUE ZERO still pushed (2 rows total, not 1)",
          "2 pushed OK" in out, out)


def test_all_frozen_exits_nonzero(m):
    print("\n[3] a run where everything failed must not read as success")
    state = {"acme": {"kw": {"2026-08-03": SNAP_ERRORED}}}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.json"
        p.write_text(json.dumps(state), encoding="utf-8")
        old_state, old_argv = m.STATE_FILE, sys.argv
        m.STATE_FILE, sys.argv = p, ["push", "--dry-run"]
        code = 0
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                m.main()
        except SystemExit as e:
            code = e.code or 0
        finally:
            m.STATE_FILE, sys.argv = old_state, old_argv
    check("exits non-zero when every keyword was a failed check", code != 0, f"exit={code}")
    check("says nothing was pushed", "0 pushed OK" in buf.getvalue(), buf.getvalue())


def test_red_proof(m):
    """The old rule on the same fixture. If this does not fail, the guard is vacuous."""
    print("\n[4] RED PROOF -- the old `max(valid_dates)` rule on the same data")
    state = {"acme": {"kw_fallback": {"2026-07-20": SNAP_GOOD, "2026-08-03": SNAP_ERRORED}}}
    dd = state["acme"]["kw_fallback"]
    old_row = m.build_row("acme", "kw_fallback", max(dd), dd[max(dd)])
    is_fake = (old_row["map_pack_position"] is None and old_row["organic_position"] is None
               and not old_row["top3"] and not old_row["top3_organic"])
    check("old rule WOULD have pushed a fake zero (proves this guard can fail)", is_fake)
    usable = [d for d in sorted(dd) if not m.snapshot_failed(dd[d])[0]]
    new_row = m.build_row("acme", "kw_fallback", usable[-1], dd[usable[-1]])
    check("new rule pushes the real ranking instead",
          new_row["map_pack_position"] == 2)


def test_against_live_state(m):
    """The real file is the only fixture that cannot be accused of being convenient."""
    print("\n[5] against the LIVE state file")
    sf = HERE / "keyword_rankings_state.json"
    if not sf.exists():
        print("  SKIP  live state file not present")
        return
    state = json.loads(sf.read_text(encoding="utf-8"))
    old_fake = new_fake = 0
    for ck, kws in state.items():
        for kw, dd in kws.items():
            if not isinstance(dd, dict):
                continue
            vd = [k for k, v in dd.items()
                  if isinstance(k, str) and len(k) == 10 and k[4] == "-" and isinstance(v, dict)]
            if not vd:
                continue
            def fake(r):
                return (r["map_pack_position"] is None and r["maps_position"] is None
                        and r["organic_position"] is None and not r["top3"]
                        and not r["top3_organic"])
            if fake(m.build_row(ck, kw, max(vd), dd[max(vd)])):
                old_fake += 1
            usable = [d for d in sorted(vd) if not m.snapshot_failed(dd[d])[0]]
            if usable and fake(m.build_row(ck, kw, usable[-1], dd[usable[-1]])):
                new_fake += 1
    print(f"        old rule fake zeros: {old_fake}   new rule: {new_fake}")
    # ⛔ THE ONLY HARD ASSERTION HERE IS `new_fake == 0`. That is the invariant.
    #
    # The first draft also asserted `old_fake > 100` as a not-vacuous proof, and
    # it went RED four hours later on completely correct code — not because
    # anything broke, but because sweeps kept succeeding and the count fell
    # 472 -> 415 -> 66. The live state file is a MOVING system; pinning a magic
    # number to it makes the guard flaky by construction, and the tempting fix
    # is to keep lowering the number until it stops complaining, which retires
    # the check without anyone noticing.
    #
    # Non-vacuity is proved by test_red_proof() on FIXTURES, which is
    # deterministic and always available. Here, old_fake is reported as
    # information: >0 means the live data still demonstrates the bug; ==0 means
    # every keyword currently has a good newest snapshot, so today's data simply
    # cannot demonstrate it. That is a SKIP with its reason stated -- never a
    # silent pass, and never a failure.
    check("new rule pushes ZERO fake zeros on the real data", new_fake == 0, f"got {new_fake}")
    if old_fake > 0:
        check(f"live data still demonstrates the bug ({old_fake} fake zeros under the old rule)",
              old_fake > new_fake, f"old={old_fake} new={new_fake}")
    else:
        print("  SKIP  live state is currently healthy -- it cannot demonstrate the "
              "old bug today; test_red_proof() carries that proof on fixtures")


def main():
    m = load_module()
    print("Guard: the rankings pusher never writes a failed check as a ranking")
    test_classifier(m)
    test_selection(m)
    test_all_frozen_exits_nonzero(m)
    test_red_proof(m)
    test_against_live_state(m)
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"  FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
