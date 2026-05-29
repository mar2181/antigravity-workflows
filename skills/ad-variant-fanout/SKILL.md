---
name: ad-variant-fanout
version: 1.0.0
author: mario
category: content-creation
risk: medium
tags: [ugc, ads, higgsfield, marketing-studio, seedance, virality-predictor, batch, variation, mission-control, draft]
description: >
  Volume-variation UGC ad fan-out — "make 20, keep 3". Turns ONE client + ONE
  offer into 15-25 angle variants in a single run (varying avatar, setting,
  hook, energy, aspect while holding the product constant), generates them via
  the live Higgsfield Marketing Studio / Seedance, auto-ranks every variant
  with the live virality_predictor (brain_activity), and surfaces ONLY the top
  3 to the Mission Control Ad Library as status=draft. Resumable + dedup-safe
  via a creative-slate ledger. Nothing auto-posts. Trigger phrases: "fan out 20
  ad variants", "make 20 keep 3", "volume variation ads", "batch ad angles for
  sugar shack", "spin up ugc variants", "give me a slate of ad angles", "rank
  my ad variants".
---

# ad-variant-fanout

Replaces the "precious trickle" of a few hand-made ads with abundant, ranked
variety — then lets the data (not guesswork) pick the keepers. This is the
make-20-keep-3 posture validated across both Higgsfield videos in the content
review. It composes engines Mario already has (Marketing Studio + Seedance +
virality_predictor) into a batch orchestrator that didn't exist before.

## Architecture (who does what)

- **`ad_variant_fanout.py`** owns the deterministic, runnable bits:
  `build_matrix()`, `CreativeSlateLedger` (resume/dedup), `rank()/top()`,
  `lint_copy()` (enforces <=300 words / <=3 hashtags), `post_to_mc()` (draft).
  Location: `C:/Users/mario/.gemini/antigravity/tools/execution/ad_variant_fanout/ad_variant_fanout.py`
- **Claude (this skill)** executes the GENERATION + SCORING via Higgsfield MCP
  tool calls per the playbook below, writing each result back into the ledger.

## Validated dry-run (2026-05-29)

```bash
cd /c/Users/mario/.gemini/antigravity/tools/execution/ad_variant_fanout
python ad_variant_fanout.py --client sugar_shack --offer "Spring break candy run" --n 20 --dry-run
```

Confirmed: builds a 20-variant SPREAD matrix (avatars varied, not all combo #0),
dedups, simulates virality scores deterministically, prints the top-3. Vehicle
clients (`spi_fun_rentals`, `juan`) auto-inject the **left-hand-drive** note on
every variant.

## Live run — the playbook Claude follows

1. **Build the matrix.** Run `build_matrix(client, offer, n)` (or
   `python ad_variant_fanout.py --client ... --offer ... --n 20` to print it).
   Axes per client come from `AXES` (seeded) — extend from that client's FB
   SKILL.md (e.g. `sugar-shack-facebook`) for richer, on-brand personas/hooks.
2. **Load the ledger** for this client (`ledgers/<client>.json`) and compute
   `pending` = variants not yet `complete`. The batch is resumable: killing it
   mid-run and re-running NEVER regenerates a completed angle.
3. **Generate each pending variant** via the **live Higgsfield MCP**:
   - `mcp__claude_ai_higgsfield__generate_video` (Seedance 2.0 for native
     lip-synced talking-head UGC; Kling/Veo for cinematic), or Marketing Studio
     for avatar + product + hook ads.
   - Async pattern: capture the job, poll `mcp__claude_ai_higgsfield__job_status`
     / `job_display` (**NOT** `wait_for_job` — that tool does not exist here),
     retry once on failure, log the asset path. Watch credits with `balance`.
4. **Score every finished variant** with
   `mcp__claude_ai_higgsfield__virality_predictor` (brain_activity: hook
   strength, attention, retention, distraction, creative score). Write
   `ledger.upsert(variant, status="complete", score=..., asset_url=...)` and
   `ledger.save()`.
5. **Keep the top 3** (`top(ledger.complete_rows(), 3)`). For each, write the
   post copy (run `lint_copy()` — must pass <=300 words / <=3 hashtags),
   then `post_to_mc(variant)` → lands as `status=draft`. Mark the rest complete
   in the ledger but DO NOT promote them.
6. **Telegram-notify** Mario with the 3 drafts + their scores. He approves which
   to keep. **Nothing auto-posts to Facebook.**

## Hard rules (enforced)

- **DRAFT only, never auto-post.** `post_to_mc` writes `status=draft`; Facebook
  publishing stays manual via Graph API after Mario's approval.
- **<= 3 hashtags, <= 300 words** — `lint_copy()` blocks violations.
- **No text baked into image-gen prompts.** Hooks/copy are post-layer text.
- **Left-hand-drive** auto-injected for vehicle clients.
- **Real testimonials only** — this module fabricates none; any testimonial in
  copy must be a real, verified review (first-name only).
- **optimum_clinic excluded** (CLOSED 2026-05-22) — not in `CLIENT_DB_ID`.

## Production upgrade (when Mario approves the MC schema change)

Swap the JSON `CreativeSlateLedger` for a Mission Control Supabase table with
the same columns (key, client, axes, status, score, asset_url) so the slate is
shared with `content-calendar-scheduler` and visible in the dashboard. Ask
before pushing the schema change to GitHub/VPS (MC = GitHub + VPS, NO Vercel).

## QC checklist

1. Dry-run: matrix spreads across avatars, dedups, ranks top-3.
2. Kill a live run mid-batch; re-run and confirm the ledger resumes without
   regenerating completed angles (zero double-spend).
3. Confirm `virality_predictor` scored all variants and exactly the top 3 hit
   MC as draft with scores attached.
4. Confirm `lint_copy()` blocked any >300-word / >3-hashtag copy.
5. Zero-auto-post audit: confirm nothing was published to Facebook.
6. Mario confirms the top-3 ranking matches his taste on one full run.
