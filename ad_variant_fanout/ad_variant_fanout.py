#!/usr/bin/env python
"""
ad_variant_fanout.py — Volume-Variation UGC Ad Fan-Out (make 20, keep 3)
========================================================================

Deterministic orchestration scaffold for the `ad-variant-fanout` skill. Turns
ONE client + ONE offer into 15-25 angle variants in a single run, then keeps
only the top 3 ranked by the LIVE Higgsfield virality_predictor.

ARCHITECTURE (read this — it explains the division of labor):
  * This module owns the DETERMINISTIC bits and is fully runnable today:
      - build_matrix(): combinatorial avatar x setting x hook x energy x aspect
      - CreativeSlateLedger: resumable, dedup-safe cross-run state (JSON now;
        swap for a Mission Control Supabase table later — same shape)
      - rank()/top(): sort finished variants by virality score
      - post_to_mc(): POST a kept variant to the MC Ad Library as status=draft
  * The GENERATION + SCORING calls are MCP tool calls made by CLAUDE per the
    SKILL.md playbook (Higgsfield Marketing Studio / generate_video / Seedance,
    poll job_status / job_display — NOT the nonexistent wait_for_job — then
    virality_predictor brain_activity). Claude writes each result back into the
    ledger via this module, then calls top()/post_to_mc() for the winners.

NON-NEGOTIABLES enforced here: nothing auto-posts (post_to_mc writes a DRAFT
only); copy stays <=300 words / <=3 hashtags (validated in lint_copy());
left-hand-drive note injected for vehicle clients; real-testimonials-only
(no testimonial text is fabricated by this module).

DRY-RUN (no API spend, runnable right now):
  python ad_variant_fanout.py --client sugar_shack --offer "Spring break candy run" --n 20 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import urllib.request
from pathlib import Path

# --- Mission Control client UUIDs (mirror of Content Loop §4) ---------------
CLIENT_DB_ID = {
    "sugar_shack": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
    "island_arcade": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
    "island_candy": "d865037b-2552-4024-9db3-10e61e1419b4",
    "juan": "a1000001-0000-0000-0000-000000000001",
    "spi_fun_rentals": "f8693268-6abf-4401-8b2e-3795e326252b",
    "custom_designs_tx": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
    "optimum_foundation": "a1000003-0000-0000-0000-000000000003",
    # optimum_clinic intentionally omitted — CLOSED 2026-05-22.
}

VEHICLE_CLIENTS = {"spi_fun_rentals", "juan"}

# --- Per-client variation axes (seed; extend from each client's FB SKILL.md) -
AXES = {
    "sugar_shack": {
        "avatar": ["college spring-breaker", "mom with two kids", "abuela with grandkids", "content-creator influencer"],
        "setting": ["SPI beach boardwalk", "inside the candy wall", "convertible road-trip"],
        "hook": ["SPI candy run before the beach", "POV: you found the candy wall",
                 "Road-trip fuel, Padre edition", "Mi dulce favorito en la isla"],
        "energy": ["hype", "cozy", "ASMR-unwrap"],
    },
    "spi_fun_rentals": {
        "avatar": ["young couple", "friend group of 4", "family with teens", "solo creator"],
        "setting": ["SPI causeway at golden hour", "beach access road", "downtown SPI strip"],
        "hook": ["Island mode: activated", "Skip the parking, just ride",
                 "Three wheels, zero roof", "El mejor paseo en la isla"],
        "energy": ["hype", "cinematic", "fun"],
    },
    "island_candy": {
        "avatar": ["kid with a dipped cone", "teen couple", "mom + toddler", "creator"],
        "setting": ["arcade neon interior", "boardwalk window", "sunny patio"],
        "hook": ["The cone that melts the algorithm", "POV: SPI's sweetest stop",
                 "Cool down the island way", "El helado mas cremoso de la isla"],
        "energy": ["bright", "ASMR", "playful"],
    },
}
# Reasonable defaults for clients not yet detailed above.
DEFAULT_AXES = {
    "avatar": ["happy customer", "young creator", "local family", "first-time visitor"],
    "setting": ["on location", "lifestyle context", "product hero close-up"],
    "hook": ["You have to see this", "POV: you found it", "The one everyone's talking about", "Lo mejor de la zona"],
    "energy": ["hype", "cinematic", "cozy"],
}

ASPECTS = ["9:16", "16:9"]


def _axes(client: str) -> dict:
    return AXES.get(client, DEFAULT_AXES)


def variation_key(v: dict) -> str:
    raw = "|".join(str(v[k]) for k in ("avatar", "setting", "hook", "energy", "aspect"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def build_matrix(client: str, offer: str, n: int = 20, aspects: list[str] | None = None) -> list[dict]:
    """Deterministic, spread-out combinatorial matrix of N variants."""
    a = _axes(client)
    aspects = aspects or ASPECTS
    combos = list(itertools.product(a["avatar"], a["setting"], a["hook"], a["energy"], aspects))
    # Deterministic spread: stride through the product so we don't take only the
    # first N (which would all share avatar #0).
    total = len(combos)
    step = max(1, total // n)
    picked = [combos[(i * step) % total] for i in range(min(n, total))]
    seen, variants = set(), []
    for avatar, setting, hook, energy, aspect in picked:
        v = {"client": client, "offer": offer, "avatar": avatar, "setting": setting,
             "hook": hook, "energy": energy, "aspect": aspect}
        if client in VEHICLE_CLIENTS:
            v["constraint"] = "steering wheel on the LEFT (left-hand drive)"
        v["key"] = variation_key(v)
        if v["key"] in seen:
            continue
        seen.add(v["key"])
        variants.append(v)
    return variants


def lint_copy(copy_text: str, hashtags: list[str]) -> list[str]:
    """Enforce the global ad rules. Returns a list of violations ([] = clean)."""
    issues = []
    words = len(re.findall(r"\b\w+\b", copy_text))
    if words > 300:
        issues.append(f"copy is {words} words (max 300)")
    if len(hashtags) > 3:
        issues.append(f"{len(hashtags)} hashtags (max 3)")
    return issues


class CreativeSlateLedger:
    """Resumable, dedup-safe state. Blank/missing row = generate; complete = skip.

    JSON now; the production skill swaps this for a Mission Control Supabase
    table with the SAME columns (key, client, axes, status, score, asset_url).
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.rows: dict[str, dict] = {}
        if self.path.exists():
            self.rows = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.rows, indent=2), encoding="utf-8")

    def pending(self, variants: list[dict]) -> list[dict]:
        return [v for v in variants if self.rows.get(v["key"], {}).get("status") != "complete"]

    def upsert(self, v: dict, status: str, score: float | None = None, asset_url: str | None = None) -> None:
        row = self.rows.get(v["key"], dict(v))
        row.update({"status": status})
        if score is not None:
            row["score"] = score
        if asset_url is not None:
            row["asset_url"] = asset_url
        self.rows[v["key"]] = row

    def complete_rows(self) -> list[dict]:
        return [r for r in self.rows.values() if r.get("status") == "complete"]


def rank(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: r.get("score", 0), reverse=True)


def top(rows: list[dict], k: int = 3) -> list[dict]:
    return rank(rows)[:k]


def post_to_mc(variant: dict, server: str = "http://localhost:3001", timeout: int = 30) -> dict:
    """POST a kept variant to the MC Ad Library as status=draft. Never auto-posts to Facebook."""
    cid = CLIENT_DB_ID.get(variant["client"])
    if not cid:
        return {"ok": False, "error": f"no UUID for client {variant['client']}"}
    payload = {
        "client_id": cid,
        "name": f"{variant['client']} — {variant['hook'][:48]} ({variant['key']})",
        "fal_url": variant.get("asset_url", ""),
        "media_type": "video",
        "copy_headline": variant.get("hook", ""),
        "copy_body": variant.get("copy_body", ""),
        "ad_angle": f"{variant['avatar']} / {variant['setting']} / {variant['energy']}",
        "platform": "facebook",
        "status": "draft",
        "generation_model": "higgsfield marketing-studio + virality_predictor",
        "generation_prompt": json.dumps({k: variant[k] for k in ("avatar", "setting", "hook", "energy", "aspect")}),
    }
    try:
        req = urllib.request.Request(f"{server}/api/ad-creatives",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json; charset=utf-8"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "response": json.loads(resp.read())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _mock_score(key: str) -> float:
    """Deterministic stand-in for virality_predictor in --dry-run (no randomness)."""
    return round(int(hashlib.sha1(key.encode()).hexdigest()[:6], 16) / 0xFFFFFF * 100, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Volume-variation UGC ad fan-out (make N, keep top-K)")
    ap.add_argument("--client", required=True, choices=sorted(CLIENT_DB_ID.keys()))
    ap.add_argument("--offer", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--ledger", default=None, help="ledger JSON path (default: ./ledgers/<client>.json)")
    ap.add_argument("--dry-run", action="store_true", help="print the matrix + simulated ranking; spend nothing")
    args = ap.parse_args()

    ledger_path = args.ledger or f"ledgers/{args.client}.json"
    matrix = build_matrix(args.client, args.offer, args.n)
    ledger = CreativeSlateLedger(ledger_path)
    pending = ledger.pending(matrix)

    print(f"Client: {args.client}  Offer: {args.offer!r}")
    print(f"Matrix: {len(matrix)} variants  |  pending (not yet complete): {len(pending)}  |  ledger: {ledger_path}")
    print("-" * 78)
    for i, v in enumerate(matrix, 1):
        note = f"  <{v['constraint']}>" if "constraint" in v else ""
        print(f"{i:>2}. [{v['aspect']}] {v['avatar']} @ {v['setting']} - \"{v['hook']}\" ({v['energy']}){note}")

    if args.dry_run:
        print("-" * 78)
        print("DRY-RUN: simulating virality_predictor scores (deterministic mock) and ranking...")
        for v in pending:
            ledger.upsert(v, status="complete", score=_mock_score(v["key"]),
                          asset_url=f"https://example/{v['key']}.mp4")
        winners = top(ledger.complete_rows(), args.top)
        print(f"\nTOP {args.top} (would land in MC Ad Library as DRAFT - never auto-posted):")
        for r in winners:
            print(f"  score {r['score']:>5}  [{r['aspect']}] {r['avatar']} - \"{r['hook']}\"")
        print("\n(no ledger written in dry-run preview; real runs persist + resume)")
        return 0

    print("\nThis is the orchestration scaffold. For a LIVE run, Claude executes the")
    print("SKILL.md playbook: generate each pending variant via Higgsfield MCP, poll")
    print("job_status, score with virality_predictor, ledger.upsert(), then post_to_mc()")
    print("the top-%d. Re-run with --dry-run to preview without spending." % args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
