#!/usr/bin/env python
"""
vision_motion.py — Vision Re-Prompt Motion Stage for Content Loop
=================================================================

Drop-in module that grounds each clip's Kling image-to-video motion prompt in
the ACTUAL PIXELS of the still, instead of animating every shot with the same
fixed per-client preset. Attacks the "every clip moves the same boring way"
half of the content-sameness problem at near-zero cost.

WHY STANDALONE: as of 2026-05-29 the historical `content_loop.py` entry point
is not present on disk (only runs/ + tmp_extra/ survive under content_loop/).
So this ships as an importable, independently-testable module. When
content_loop.py is restored, wire it in behind a `--vision-motion` flag:

    from vision_motion import vision_motion_prompt
    motion = (vision_motion_prompt(still_path, client, aspect=fmt)["motion_prompt"]
              if args.vision_motion else MOTION_PROMPTS[client])
    # ...feed `motion` to the Kling i2v call for THIS clip.

The function is fail-safe: any API/parse error falls back to the static
per-client preset, so enabling it can never harm a run.

PROVIDER CASCADE (provider="auto", the default): try Anthropic Claude vision
(ANTHROPIC_API_KEY, Haiku 4.5) first; on any failure cascade to OpenRouter
(OPENROUTER_API_KEY, a vision model); if both unavailable, return the static
per-client preset. Stdlib urllib only — no third-party packages, matching the
rest of the Content Loop toolchain.

CLI:
    $env:ANTHROPIC_API_KEY="sk-ant-..."   # and/or  $env:OPENROUTER_API_KEY="sk-or-..."
    python vision_motion.py --image path/to/still.png --client spi_fun_rentals --json
    python vision_motion.py --image still.png --client juan --provider openrouter
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# --- Static fallbacks: mirror of Content Loop §8 MOTION_PROMPTS -------------
MOTION_PROMPTS = {
    "sugar_shack": "Cinematic slow zoom-in on colorful candy, warm bright lighting, gentle camera drift",
    "island_arcade": "Cinematic slow push-in, vibrant neon glow, smooth hand-held motion",
    "island_candy": "Cinematic slow zoom on ice cream texture, bright airy light, subtle swirl motion",
    "juan": "Cinematic slow push-in on property, golden-hour light, smooth steadicam drift",
    "spi_fun_rentals": "Cinematic slow tracking shot on paved coastal road, golden light, confident motion",
    "custom_designs_tx": "Cinematic slow push-in, luxe dark aesthetic, gentle camera drift, premium finish",
    "optimum_foundation": "Cinematic slow pan, warm community light, hopeful gentle motion",
    # optimum_clinic intentionally omitted — CLOSED 2026-05-22 (not a generation target).
}

# --- Per-client hard rules carried into the Vision instruction --------------
CLIENT_RULES = {
    "spi_fun_rentals": (
        "This is a rental vehicle (golf cart / slingshot / scooter). The steering "
        "wheel MUST stay on the LEFT — never suggest a camera move that orbits to "
        "imply a right-hand-drive cabin. Energy: fun, coastal, confident."
    ),
    "juan": (
        "Real-estate / property or vehicle. If a vehicle is present keep it "
        "left-hand drive. Energy: premium, trustworthy, golden-hour."
    ),
    "sugar_shack": "Candy store. Energy: bright, playful, appetizing.",
    "island_candy": "Ice cream / sweets. Energy: bright, airy, mouth-watering.",
    "island_arcade": "Arcade. Energy: neon, kinetic, fun.",
    "custom_designs_tx": "Security / AV install. Energy: premium, crisp, reassuring.",
    "optimum_foundation": "Community nonprofit. Energy: warm, hopeful, human.",
}

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"      # vision-capable, cheap, fast
OPENROUTER_MODEL = "openai/gpt-4o-mini"            # vision-capable, cheap

_MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".webp": "image/webp", ".gif": "image/gif"}


def _media_type(path: Path) -> str:
    return _MEDIA.get(path.suffix.lower(), "image/jpeg")


def _b64(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("ascii")


def _build_instruction(client: str, aspect: str) -> str:
    rule = CLIENT_RULES.get(client, "Match the brand's energy.")
    return (
        "You are a cinematic director writing a SINGLE motion prompt for a Kling "
        "image-to-video generation. The still below will be animated. Describe the "
        "ONE most cinematic camera move grounded in THIS exact frame — its "
        "composition, the main subject's position, depth, and lighting. Prefer "
        "moves that exploit what is actually in the image (e.g. low orbit around a "
        "foreground subject, rear-tracking dolly down a road, parallax push past a "
        "sign, tilt revealing a ceiling). Avoid generic 'slow zoom' unless the "
        f"frame truly calls for it. Target aspect ratio: {aspect}. "
        f"Client rules: {rule} "
        "Output ONLY the motion prompt, max 40 words, no preamble, no quotes, no "
        "labels. End with 'no text, no new people' to keep Kling clean."
    )


def _post(url: str, body: bytes, headers: dict, timeout: int):
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _call_anthropic(instruction: str, path: Path, model: str, key: str, timeout: int):
    body = json.dumps({
        "model": model,
        "max_tokens": 120,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": _media_type(path), "data": _b64(path)}},
            {"type": "text", "text": instruction},
        ]}],
    }).encode("utf-8")
    payload = _post(ANTHROPIC_URL, body, {
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, timeout)
    text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text").strip()
    return text, payload


def _call_openrouter(instruction: str, path: Path, model: str, key: str, timeout: int):
    data_url = f"data:{_media_type(path)};base64,{_b64(path)}"
    body = json.dumps({
        "model": model,
        "max_tokens": 120,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": instruction},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
    }).encode("utf-8")
    payload = _post(OPENROUTER_URL, body, {
        "Authorization": f"Bearer {key}", "content-type": "application/json",
        "HTTP-Referer": "https://antigravity.digital", "X-Title": "Content Loop Vision Motion",
    }, timeout)
    text = (payload.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()
    return text, payload


def vision_motion_prompt(
    image: str | Path,
    client: str,
    aspect: str = "9:16",
    provider: str = "auto",
    model: str | None = None,
    timeout: int = 60,
) -> dict:
    """Return {'motion_prompt', 'source', 'provider', 'model', 'raw'}.

    source = 'vision' on success, 'fallback' if no provider succeeded.
    provider: 'auto' (anthropic -> openrouter -> static), 'anthropic', 'openrouter'.
    Never raises for API/parse problems — always returns a usable prompt.
    """
    path = Path(image)
    fallback = MOTION_PROMPTS.get(client, "Cinematic slow push-in, gentle camera drift")
    if not path.exists():
        return {"motion_prompt": fallback, "source": "fallback", "provider": None,
                "model": None, "raw": f"image not found: {path}"}

    instruction = _build_instruction(client, aspect)
    ak = os.environ.get("ANTHROPIC_API_KEY")
    ok = os.environ.get("OPENROUTER_API_KEY")

    chain = []
    if provider in ("auto", "anthropic") and ak:
        chain.append(("anthropic", _call_anthropic, model or ANTHROPIC_MODEL, ak))
    if provider in ("auto", "openrouter") and ok:
        chain.append(("openrouter", _call_openrouter, model or OPENROUTER_MODEL, ok))

    errors = []
    for name, fn, mdl, key in chain:
        try:
            text, raw = fn(instruction, path, mdl, key, timeout)
            if text:
                return {"motion_prompt": text, "source": "vision", "provider": name,
                        "model": mdl, "raw": raw}
            errors.append(f"{name}: empty response")
        except urllib.error.HTTPError as e:
            errors.append(f"{name} HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")
        except Exception as e:  # noqa: BLE001 — never let a motion prompt break a run
            errors.append(f"{name} {type(e).__name__}: {e}")

    if not chain:
        errors.append("no API key set (ANTHROPIC_API_KEY / OPENROUTER_API_KEY)")
    return {"motion_prompt": fallback, "source": "fallback", "provider": None,
            "model": None, "raw": " | ".join(errors)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Vision-grounded per-shot motion prompt for Kling i2v")
    ap.add_argument("--image", required=True)
    ap.add_argument("--client", required=True, choices=sorted(MOTION_PROMPTS.keys()))
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--provider", default="auto", choices=["auto", "anthropic", "openrouter"])
    ap.add_argument("--model", default=None, help="override the active provider's model")
    ap.add_argument("--json", action="store_true", help="print full JSON result")
    args = ap.parse_args()

    result = vision_motion_prompt(args.image, args.client, args.aspect, args.provider, args.model)
    if args.json:
        printable = {k: v for k, v in result.items() if k != "raw"}
        if result["source"] == "fallback":
            printable["error"] = str(result["raw"])[:300]
        print(json.dumps(printable, indent=2))
    else:
        print(f"[{result['source']}/{result.get('provider')}] {result['motion_prompt']}")
    print(f"  (static preset was: {MOTION_PROMPTS.get(args.client)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
