---
name: content-loop-vision-reprompt
version: 1.0.0
author: mario
category: content-creation
risk: low
tags: [content-loop, kling, image-to-video, vision, motion-prompt, claude-vision, openrouter, cinematic]
description: >
  Optional vision-grounded motion stage for Content Loop. Before each Kling
  image-to-video call, route the generated still through a vision model
  (Claude Haiku 4.5, cascading to OpenRouter) to author a per-shot motion
  prompt grounded in THAT frame's composition, subject, and lighting — instead
  of animating every clip with the same fixed per-client preset. Fixes the
  "every clip moves the same boring way" half of the content-sameness problem
  at near-zero cost. Fail-safe: any error falls back to the static preset, so
  enabling it can never harm a run. Trigger phrases: "vary the motion per clip",
  "vision reprompt", "per-shot motion prompt", "stop every clip moving the
  same", "cinematic motion variety", "ground the motion in the image".
---

# content-loop-vision-reprompt

A small, high-leverage upgrade to Content Loop. Today Content Loop animates
every shot from a single fixed `MOTION_PROMPTS[client]` entry, so a 6-clip ad
gets the same camera move six times. This stage feeds each still to a vision
model and gets back a motion prompt grounded in THAT frame — a 6-clip ad now
gets 6 distinct, composition-appropriate moves.

> Verified technique (n8n template #6918 "Video Prompts1" node). The single
> sharpest reusable craft idea from the n8n video; cheapest item on the whole
> content roadmap.

## Where it lives

```
C:/Users/mario/.gemini/antigravity/tools/execution/content_loop/vision_motion.py
```

> **Note (2026-05-29):** the historical `content_loop.py` entry point is NOT on
> disk (only `runs/` + `tmp_extra/` survive). So this ships as a **standalone,
> importable, independently-testable module**, not a patch. When
> `content_loop.py` is restored, wire it in (one line — see below).

## Runtime requirement

Set at least one key (cascade: Anthropic first, then OpenRouter):

```bash
$env:ANTHROPIC_API_KEY="sk-ant-..."     # Haiku 4.5 — preferred (needs API credits)
$env:OPENROUTER_API_KEY="sk-or-v1-..."  # fallback — gpt-4o-mini vision
```

Keys live in `memory/api_keys_verified_may5_2026.md`. No third-party packages
(stdlib `urllib` only, matching the Content Loop toolchain).

## Use it (CLI)

```bash
cd /c/Users/mario/.gemini/antigravity/tools/execution/content_loop
python vision_motion.py --image path/to/still.png --client spi_fun_rentals --json
python vision_motion.py --image still.png --client juan --provider openrouter
```

Returns `{motion_prompt, source, provider, model}` where `source` is `vision`
on success or `fallback` (static preset) on any failure.

## Validated test (2026-05-29, via OpenRouter gpt-4o-mini)

Same client (spi_fun_rentals), 3 different real stills → 3 DISTINCT prompts,
vs the one static preset that would have applied to all:

| Still | Static preset | Vision-grounded result |
|---|---|---|
| slingshot street | "slow tracking shot on coastal road" | dolly **left** past vehicle, **tilt up** to drivers + palms |
| slingshot closeup | (same) | dolly in from **right**, glint off body, **pan left** to steering wheel |
| beach cruisers | (same) | dolly past **front wheels**, reveal **left-side steering wheel** behind |

The per-client **left-hand-drive rule propagated into the AI output**
("left-side steering wheel"). The Anthropic-credit error path also confirmed
the fail-safe fallback + provider cascade work.

## Integration (when content_loop.py is restored)

Behind an opt-in `--vision-motion` flag, replace the static lookup at the
Kling i2v call site:

```python
from vision_motion import vision_motion_prompt

motion = (
    vision_motion_prompt(still_path, client, aspect=video_format)["motion_prompt"]
    if args.vision_motion
    else MOTION_PROMPTS[client]
)
# ...pass `motion` to the Kling image-to-video call for THIS clip.
```

Everything downstream (ffmpeg stitch, ElevenLabs VO, music mix, FAL word-level
ASS captions, ffmpeg drawtext brand overlay, MC Ad Library draft) is unchanged.
Keep `--vision-motion` OFF by default until Mario approves the look.

## Hard rules

- This stage authors **motion** prompts, not image-gen prompts — inherently
  compliant with "no text in image prompts."
- Per-client rules are injected into the vision instruction
  (`CLIENT_RULES`): left-hand-drive for spi_fun_rentals/juan; brand energy.
- Never let a motion prompt break a run — the module always returns a usable
  string (fallback on any error).
- Cost: ~1 cheap vision call per still (Haiku 4.5 / gpt-4o-mini). Negligible.

## Full A/B (gated — costs FAL credits)

The mechanism is proven (static vs 3 distinct vision prompts above). A full
visual A/B = build the SAME photo set twice through Content Loop, once with the
fixed dict and once with `--vision-motion`, and compare. That spends ~2x Kling
render cost (~$0.50-1.00) + ~6 min. Run it only on Mario's go.

## QC checklist

1. Run the module on 3+ stills of one client; confirm 3 DISTINCT prompts.
2. Confirm vehicle-client prompts respect left-hand-drive.
3. Kill the API key and confirm it falls back to the static preset cleanly.
4. (Full A/B, gated) Confirm the vision-version ad looks more cinematic than
   the fixed-preset version before defaulting `--vision-motion` on.
