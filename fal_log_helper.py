"""
fal_log_helper.py — Fire-and-forget Supabase logger for fal.ai generations.

Inserts a row into the `fal_generations` table for every fal generation
performed by Mario's automation scripts. Used by the Mission Control
multi-tenant dashboard's fal panel to display generation history.

Spec: dashboard/CONTRACT.md §2 (Wave 1, Agent C).

Usage:
    from fal_log_helper import log_fal
    try:
        log_fal(model='fal-ai/flux-pro/v1.1-ultra',
                prompt=prompt_text,
                output_url=result['images'][0]['url'],
                source='blog_writer')
    except Exception:
        pass  # logging must never break the caller

Behavior:
    - Silent on failure (prints to stderr only).
    - NEVER raises. Caller code is unaffected by Supabase outages.
    - Loads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from
      C:/Users/mario/Projects/missioncontrol/dashboard/.env.local
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Resolve .env.local once at module load
_ENV_PATH = Path(r"C:\Users\mario\Projects\missioncontrol\dashboard\.env.local")
_SUPABASE_URL: str | None = None
_SUPABASE_SERVICE_KEY: str | None = None


def _load_env() -> None:
    """Load SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env.local.

    Falls back to actual os.environ if .env.local is missing.
    Sets module-level globals. Silent on failure.
    """
    global _SUPABASE_URL, _SUPABASE_SERVICE_KEY

    # Prefer values already in os.environ
    _SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    _SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if _SUPABASE_URL and _SUPABASE_SERVICE_KEY:
        return

    # Parse .env.local manually (no python-dotenv dependency requirement)
    if not _ENV_PATH.exists():
        return

    try:
        for raw in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL") and not _SUPABASE_URL:
                _SUPABASE_URL = value
            elif key == "SUPABASE_SERVICE_ROLE_KEY" and not _SUPABASE_SERVICE_KEY:
                _SUPABASE_SERVICE_KEY = value
    except Exception as e:
        print(f"[fal_log_helper] env load failed: {e}", file=sys.stderr)


_load_env()


def log_fal(
    model: str,
    *,
    prompt: str = "",
    output_url: str = "",
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    source: str = "",
    tenant_id: str = "mario_personal",
) -> None:
    """Insert one row into Supabase `fal_generations`. Silent on failure.

    Args:
        model: fal model identifier (e.g. 'fal-ai/flux-pro/v1.1-ultra').
        prompt: text prompt sent to the model.
        output_url: URL of the generated asset.
        cost_usd: known cost in USD (defaults to 0.0).
        duration_ms: wall-clock duration in milliseconds.
        source: short tag identifying the caller (e.g. 'blog_writer').
        tenant_id: tenant identifier (default 'mario_personal').

    Returns:
        None. Never raises.
    """
    try:
        if not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY:
            print(
                "[fal_log_helper] missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY; skipping",
                file=sys.stderr,
            )
            return

        # Truncate prompt to keep payload reasonable
        safe_prompt = (prompt or "")[:4000]
        safe_output = (output_url or "")[:1000]

        row = {
            "tenant_id": tenant_id,
            "model": model,
            "prompt": safe_prompt,
            "output_url": safe_output,
            "cost_usd": float(cost_usd) if cost_usd else 0.0,
            "duration_ms": int(duration_ms) if duration_ms else 0,
            "source": source,
        }

        url = f"{_SUPABASE_URL.rstrip('/')}/rest/v1/fal_generations"
        body = json.dumps(row).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "apikey": _SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
                "Prefer": "return=minimal",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            # 201 Created on success; any 2xx is fine
            if not (200 <= resp.status < 300):
                print(
                    f"[fal_log_helper] insert returned HTTP {resp.status}",
                    file=sys.stderr,
                )
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            detail = ""
        print(
            f"[fal_log_helper] HTTP {e.code} inserting fal_generations: {detail}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[fal_log_helper] insert failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Manual smoke test
    log_fal(model="test/smoke", source="fal_log_helper_main", prompt="smoke test")
    print("smoke test invoked")
