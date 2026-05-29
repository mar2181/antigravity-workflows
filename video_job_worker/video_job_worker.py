#!/usr/bin/env python3
"""
Mission Control — Video Maker · Phase-2 Generation Worker
=========================================================

A LOCAL poller that turns queued Video Maker jobs (rows in the Supabase
`media_library` table, enqueued by MC PR #120) into actual rendered videos.

Runs on THIS Windows machine because Remotion + Higgsfield work here and the
VPS is too small to render. NO Vercel. NO auto-post. NO credit spend.

Job-row contract (media_library) for a queued job:
    status     = "queued"
    type       = "video-skill:<slug>"   (branded-template | ad-fanout |
                                          animate-photo | content-calendar)
    model      = the skill name
    request_id = the jobId (uuid)
    url        = the example URL or "pending://queued"
    media_type = "video" | "image"
    prompt     = JSON string of the full jobSpec:
                 { jobId, slug, skill, cost, inputs:{...},
                   enqueuedBy, enqueuedAt }

The `inputs` object holds the client's form values keyed by the skill's input
schema (see dashboard/src/config/video-templates.ts in the missioncontrol repo).
For `branded-template` we expect:
    business     : client slug (sugar_shack | island_arcade | ... )
    photos       : list[str]  (image-multi → remote URLs)   [aliases below]
    headline/hook: the slam-in hook text
    captions     : list[str]  per-beat captions
    brandColor   : optional hex override (informational; brand palette drives it)
    music        : bool — include the client jingle / music bed

Dispatch by slug
----------------
    branded-template  FREE   -> auto-render via Remotion, upload, status=completed
    ad-fanout         CREDIT -> GATED. status=awaiting_approval. NO spend.
    animate-photo     CREDIT -> GATED. status=awaiting_approval. NO spend.
    content-calendar  PLAN   -> status=scheduled. No video.

Run modes
---------
    python video_job_worker.py --once               process queued jobs, exit
    python video_job_worker.py --watch [--interval 30]   poll every N seconds
    python video_job_worker.py --dry-run             log intent; no render/upload/PATCH
    python video_job_worker.py --insert-test-job     insert a Sugar Shack test job
    python video_job_worker.py --delete-job <id>     delete a media_library row by request_id

Standard-library only (urllib) — no pip deps. Reads Supabase creds from MC's
dashboard/.env.local (falls back to the api keys vault), or env vars.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from shutil import which
from urllib import error as urlerror
from urllib import request as urlrequest

# ──────────────────────────── Configuration ────────────────────────────

REMOTION_PROJECT = Path(r"C:\Users\mario\remotion-branded-templates")
REMOTION_ENTRY = "src/index.ts"
REMOTION_COMP_ID = "BrandedListicle"

MEDIA_BUCKET = "mission-control-media"
VIDEO_OUTPUT_PREFIX = "video-outputs"  # storage path: video-outputs/<jobId>.mp4

# Where rendered MP4s land locally before upload.
OUT_DIR = Path(__file__).resolve().parent / "out"

MC_ENV_LOCAL = Path(r"C:\Users\mario\Projects\missioncontrol\dashboard\.env.local")
API_KEYS_VAULT = Path(
    r"C:\Users\mario\.claude\projects\C--Users-mario\memory\api_keys_vault.md"
)

# Skills that cost credits → GATED. We NEVER generate these; just flag for
# Mario's approval. (NOTE: when credit-gen is later enabled, Higgsfield caps at
# 2 CONCURRENT jobs on the Ultra plan — submit generation calls in PAIRS, poll
# each pair to completion before the next. See memory
# feedback_higgsfield_2_concurrent_jobs.md.)
CREDIT_GATED_SLUGS = {"ad-fanout", "animate-photo"}

# Known MC client slugs that map cleanly to the Remotion BRANDS palette.
# (Remotion uses "juan"; MC sometimes uses "juan" or "juan_elizondo".)
BRAND_SLUGS = {
    "sugar_shack",
    "island_arcade",
    "island_candy",
    "juan",
    "spi_fun_rentals",
    "custom_designs_tx",
    "optimum_clinic",
    "optimum_foundation",
}
BRAND_ALIASES = {
    "juan_elizondo": "juan",
    "juanelizondo": "juan",
    "custom_designs": "custom_designs_tx",
    "customdesigns": "custom_designs_tx",
    "spi_fun": "spi_fun_rentals",
}
# Per-client default avatar initials for the CTA end-card.
BRAND_INITIALS = {
    "sugar_shack": "SS",
    "island_arcade": "IA",
    "island_candy": "IC",
    "juan": "JE",
    "spi_fun_rentals": "SF",
    "custom_designs_tx": "CD",
    "optimum_clinic": "OC",
    "optimum_foundation": "OF",
}
# Per-client default jingle / music bed (public/ path inside the Remotion project).
BRAND_AUDIO = {
    "sugar_shack": ("sugar_shack/jingle.m4a", 0.33),
}


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def resolve_exe(name: str) -> str:
    """Resolve an executable, preferring the Windows .cmd/.exe shim. Returns the
    full path so subprocess can run with shell=False (robust with spaces in
    arg paths). Falls back to the bare name if not found on PATH."""
    for cand in (name, f"{name}.cmd", f"{name}.exe", f"{name}.bat"):
        found = which(cand)
        if found:
            return found
    return name


# ──────────────────────────── Credentials ────────────────────────────


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def load_supabase_creds() -> tuple[str, str]:
    """Return (SUPABASE_URL, SERVICE_ROLE_KEY). Env > MC .env.local > vault."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not (url and key):
        env = _parse_env_file(MC_ENV_LOCAL)
        url = url or env.get("NEXT_PUBLIC_SUPABASE_URL")
        key = key or env.get("SUPABASE_SERVICE_ROLE_KEY")

    if not (url and key) and API_KEYS_VAULT.exists():
        text = API_KEYS_VAULT.read_text(encoding="utf-8", errors="ignore")
        if not url:
            m = re.search(r"(https://[a-z0-9]+\.supabase\.co)", text)
            url = m.group(1) if m else None
        if not key:
            m = re.search(r"(eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)", text)
            key = m.group(1) if m else None

    if not (url and key):
        raise RuntimeError(
            "Could not resolve Supabase URL + SERVICE_ROLE_KEY. Set "
            "NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY env vars, or "
            f"ensure {MC_ENV_LOCAL} exists."
        )
    return url.rstrip("/"), key


# ──────────────────────────── Supabase REST ────────────────────────────


class Supabase:
    """Thin PostgREST + Storage client over urllib (no external deps)."""

    def __init__(self, url: str, service_key: str):
        self.url = url
        self.key = service_key

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
        }
        if extra:
            h.update(extra)
        return h

    # ---- PostgREST table ops ----

    def select_queued(self) -> list[dict]:
        """Fetch all queued Video Maker jobs (type like 'video-skill:%')."""
        q = (
            f"{self.url}/rest/v1/media_library"
            "?status=eq.queued"
            "&type=like.video-skill:*"
            "&select=*"
            "&order=created_at.asc"
        )
        req = urlrequest.Request(q, headers=self._headers(), method="GET")
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_by_request_id(self, request_id: str) -> list[dict]:
        q = (
            f"{self.url}/rest/v1/media_library"
            f"?request_id=eq.{request_id}&select=*"
        )
        req = urlrequest.Request(q, headers=self._headers(), method="GET")
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def patch_by_request_id(self, request_id: str, patch: dict) -> list[dict]:
        q = f"{self.url}/rest/v1/media_library?request_id=eq.{request_id}"
        body = json.dumps(patch).encode("utf-8")
        req = urlrequest.Request(
            q,
            data=body,
            headers=self._headers(
                {"Content-Type": "application/json", "Prefer": "return=representation"}
            ),
            method="PATCH",
        )
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def insert(self, row: dict) -> list[dict]:
        q = f"{self.url}/rest/v1/media_library"
        body = json.dumps(row).encode("utf-8")
        req = urlrequest.Request(
            q,
            data=body,
            headers=self._headers(
                {"Content-Type": "application/json", "Prefer": "return=representation"}
            ),
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def delete_by_request_id(self, request_id: str) -> None:
        q = f"{self.url}/rest/v1/media_library?request_id=eq.{request_id}"
        req = urlrequest.Request(q, headers=self._headers(), method="DELETE")
        with urlrequest.urlopen(req, timeout=30) as resp:
            resp.read()

    # ---- Storage ops ----

    def upload_object(self, storage_path: str, data: bytes, content_type: str) -> str:
        """Upload bytes to mission-control-media/<storage_path>; return public URL."""
        endpoint = f"{self.url}/storage/v1/object/{MEDIA_BUCKET}/{storage_path}"
        req = urlrequest.Request(
            endpoint,
            data=data,
            headers=self._headers(
                {
                    "Content-Type": content_type,
                    # upsert so re-runs of the same jobId overwrite cleanly
                    "x-upsert": "true",
                }
            ),
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=300) as resp:
                resp.read()
        except urlerror.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Storage upload failed ({e.code}): {detail}")
        return self.public_url(storage_path)

    def public_url(self, storage_path: str) -> str:
        return f"{self.url}/storage/v1/object/public/{MEDIA_BUCKET}/{storage_path}"


# ──────────────────────────── Input mapping ────────────────────────────


def normalize_client(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = BRAND_ALIASES.get(s, s)
    if s in BRAND_SLUGS:
        return s
    # Best-effort: collapse spaces/dashes
    s2 = re.sub(r"[\s\-]+", "_", s)
    s2 = BRAND_ALIASES.get(s2, s2)
    return s2 if s2 in BRAND_SLUGS else "sugar_shack"


def _first(inputs: dict, *keys: str, default=None):
    for k in keys:
        if k in inputs and inputs[k] not in (None, "", []):
            return inputs[k]
    return default


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        # tolerate comma- or newline-separated strings
        parts = re.split(r"[\n,]+", value)
        return [p.strip() for p in parts if p.strip()]
    return [value]


def build_branded_props(inputs: dict) -> dict:
    """Map the MC branded-template `inputs` payload → BrandedListicle props."""
    client = normalize_client(
        _first(inputs, "business", "client", "clientSlug", "brand", default="sugar_shack")
    )

    photos = _as_list(
        _first(
            inputs,
            "photos",
            "photoUrls",
            "images",
            "imageUrls",
            "photo",
            default=[],
        )
    )
    captions = _as_list(_first(inputs, "captions", "beatCaptions", "beats", default=[]))
    subs = _as_list(_first(inputs, "subs", "subcaptions", default=[]))

    # Build beats: pair each photo with its caption (fall back to a generic).
    beats = []
    for i, photo in enumerate(photos):
        cap = captions[i] if i < len(captions) else f"REASON {i + 1}"
        beat = {"imageUrl": str(photo), "caption": str(cap).upper()}
        if i < len(subs):
            beat["sub"] = str(subs[i])
        beats.append(beat)

    if not beats:
        raise ValueError("branded-template job has no photos in inputs")

    hook = _first(inputs, "headline", "hook", "hookText", "title", default="")
    hook_words = _as_list(hook) if isinstance(hook, list) else str(hook).split()
    if not hook_words:
        hook_words = ["WATCH", "THIS"]

    kicker = str(_first(inputs, "kicker", "subhead", "tagline", default="") or "")
    cta_primary = str(
        _first(inputs, "ctaPrimary", "cta", "callToAction", default="Learn more")
    )
    cta_secondary = _first(inputs, "ctaSecondary", "ctaEs", default=None)

    # Music toggle → attach the client jingle if we have one.
    music_on = bool(_first(inputs, "music", "includeMusic", "musicEnabled", default=False))
    audio_src = None
    audio_volume = None
    if music_on and client in BRAND_AUDIO:
        audio_src, audio_volume = BRAND_AUDIO[client]

    props: dict[str, Any] = {
        "client": client,
        "brandInitials": str(
            _first(inputs, "brandInitials", "initials", default=BRAND_INITIALS.get(client, "MC"))
        ),
        "kicker": kicker,
        "hookWords": [str(w) for w in hook_words],
        "hookAccentIndexes": [max(0, len(hook_words) - 1)] if len(hook_words) > 1 else [],
        "beats": beats,
        "ctaPrimary": cta_primary,
    }
    if cta_secondary:
        props["ctaSecondary"] = str(cta_secondary)
    if audio_src:
        props["audioSrc"] = audio_src
        props["audioVolume"] = audio_volume
    # NOTE: brandColor from inputs is intentionally informational only — the
    # Remotion BRANDS palette is the source of truth for on-brand color so we
    # never ship an off-palette spot. (Recorded but not forwarded.)
    return props


# ──────────────────────────── Remotion render ────────────────────────────


def render_remotion(props: dict, out_path: Path) -> None:
    """Render the BrandedListicle comp headless via the local Remotion project."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write props to a temp .json file to avoid shell-quoting hell.
    props_fd, props_file = tempfile.mkstemp(suffix=".props.json", prefix="branded_")
    os.close(props_fd)
    Path(props_file).write_text(json.dumps(props), encoding="utf-8")

    # Resolve npx.cmd to a full path so we run shell=False — robust even when
    # the props/out paths contain spaces (Windows shell=True + list mangles them).
    npx = resolve_exe("npx")
    cmd = [
        npx,
        "remotion",
        "render",
        REMOTION_ENTRY,
        REMOTION_COMP_ID,
        str(out_path),
        f"--props={props_file}",
        "--log=info",
    ]
    log(f"  render: npx remotion render {REMOTION_COMP_ID} -> {out_path.name}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REMOTION_PROJECT),
            capture_output=True,
            text=True,
            timeout=900,
        )
    finally:
        try:
            os.remove(props_file)
        except OSError:
            pass

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-2000:]
        raise RuntimeError(f"Remotion render failed (exit {proc.returncode}):\n{tail}")
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("Remotion reported success but produced no output file")


def ffprobe_validate(path: Path) -> dict:
    """ffprobe the MP4. Raise if it isn't a real h264 clip (>0s, sane bitrate)."""
    cmd = [
        resolve_exe("ffprobe"),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr[-500:]}")
    meta = json.loads(proc.stdout)

    fmt = meta.get("format", {})
    vstreams = [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]
    if not vstreams:
        raise RuntimeError("ffprobe: no video stream in output")

    v = vstreams[0]
    codec = v.get("codec_name", "")
    duration = float(fmt.get("duration") or v.get("duration") or 0)
    bit_rate = int(fmt.get("bit_rate") or 0)
    width = v.get("width")
    height = v.get("height")
    size = int(fmt.get("size") or path.stat().st_size)

    # The ~17 kbps blank-frame signature: reject anything pathologically low.
    if codec not in ("h264", "hevc", "av1"):
        raise RuntimeError(f"ffprobe: unexpected video codec {codec!r} (want h264)")
    if duration <= 0.5:
        raise RuntimeError(f"ffprobe: duration too short ({duration:.2f}s) — invalid render")
    if bit_rate and bit_rate < 50_000:
        raise RuntimeError(
            f"ffprobe: bitrate {bit_rate} bps is the blank-frame signature — invalid render"
        )

    summary = {
        "codec": codec,
        "width": width,
        "height": height,
        "duration_s": round(duration, 2),
        "bit_rate": bit_rate,
        "size_bytes": size,
        "fps": v.get("r_frame_rate"),
    }
    return summary


# ──────────────────────────── Job processing ────────────────────────────


def parse_job_spec(row: dict) -> dict:
    """Parse the prompt JSON jobSpec; tolerate missing/garbled prompts."""
    raw = row.get("prompt") or "{}"
    try:
        spec = json.loads(raw)
        if not isinstance(spec, dict):
            spec = {}
    except (json.JSONDecodeError, TypeError):
        spec = {}
    return spec


def slug_from_row(row: dict, spec: dict) -> str:
    slug = spec.get("slug")
    if slug:
        return str(slug)
    t = str(row.get("type") or "")
    if t.startswith("video-skill:"):
        return t.split(":", 1)[1]
    return ""


def process_branded_template(
    sb: Supabase, row: dict, spec: dict, dry_run: bool
) -> str:
    job_id = row.get("request_id") or spec.get("jobId") or str(uuid.uuid4())
    inputs = spec.get("inputs") or {}
    props = build_branded_props(inputs)

    log(f"  branded-template job {job_id}: client={props['client']} "
        f"beats={len(props['beats'])} music={'audioSrc' in props}")

    if dry_run:
        log(f"  [DRY-RUN] would render BrandedListicle with props: "
            f"{json.dumps(props)[:400]}...")
        log(f"  [DRY-RUN] would upload -> {VIDEO_OUTPUT_PREFIX}/{job_id}.mp4")
        log(f"  [DRY-RUN] would PATCH status=completed, url=<public url>")
        return "dry-run"

    out_path = OUT_DIR / f"{job_id}.mp4"
    render_remotion(props, out_path)

    summary = ffprobe_validate(out_path)
    log(f"  ffprobe OK: {json.dumps(summary)}")

    storage_path = f"{VIDEO_OUTPUT_PREFIX}/{job_id}.mp4"
    data = out_path.read_bytes()
    public_url = sb.upload_object(storage_path, data, "video/mp4")
    log(f"  uploaded -> {public_url}")

    # Fold the ffprobe summary back into the prompt JSON for traceability.
    spec.setdefault("render", {})
    spec["render"] = {
        "ffprobe": summary,
        "storage_path": storage_path,
        "renderedAt": datetime.now(timezone.utc).isoformat(),
        "comp": REMOTION_COMP_ID,
    }

    sb.patch_by_request_id(
        job_id,
        {
            "status": "completed",
            "url": public_url,
            "storage_path": storage_path,
            "media_type": "video",
            "error": None,
            "prompt": json.dumps(spec),
        },
    )
    log(f"  row {job_id} -> status=completed")
    return public_url


def process_credit_gated(
    sb: Supabase, row: dict, spec: dict, slug: str, dry_run: bool
) -> str:
    """ad-fanout / animate-photo: GATE for approval. NEVER generate. NO spend."""
    job_id = row.get("request_id") or spec.get("jobId") or str(uuid.uuid4())
    cost = spec.get("cost")
    note = (
        f"[GATED] '{slug}' is a credit skill — held for Mario's approval. "
        f"No Higgsfield call, no credit spend. "
        f"Estimated cost: {cost if cost is not None else 'unknown'} credits. "
        f"Approve in MC to release for generation. "
        f"(When enabled: Higgsfield caps at 2 concurrent jobs on Ultra — submit in pairs.)"
    )
    log(f"  {slug} job {job_id}: GATED — {note}")

    if dry_run:
        log(f"  [DRY-RUN] would PATCH status=awaiting_approval (+note). NO spend.")
        return "dry-run"

    spec.setdefault("gate", {})
    spec["gate"] = {
        "reason": "credit-skill-requires-approval",
        "note": note,
        "cost_estimate": cost,
        "gatedAt": datetime.now(timezone.utc).isoformat(),
    }
    sb.patch_by_request_id(
        job_id,
        {
            "status": "awaiting_approval",
            "error": note,
            "prompt": json.dumps(spec),
        },
    )
    log(f"  row {job_id} -> status=awaiting_approval (no spend)")
    return "awaiting_approval"


def process_content_calendar(
    sb: Supabase, row: dict, spec: dict, dry_run: bool
) -> str:
    """content-calendar: planner only. No render. status=scheduled."""
    job_id = row.get("request_id") or spec.get("jobId") or str(uuid.uuid4())
    log(f"  content-calendar job {job_id}: planner — no video, status=scheduled")
    if dry_run:
        log(f"  [DRY-RUN] would PATCH status=scheduled")
        return "dry-run"
    spec.setdefault("plan", {})
    spec["plan"]["scheduledAt"] = datetime.now(timezone.utc).isoformat()
    sb.patch_by_request_id(
        job_id,
        {"status": "scheduled", "prompt": json.dumps(spec)},
    )
    log(f"  row {job_id} -> status=scheduled")
    return "scheduled"


def process_job(sb: Supabase, row: dict, dry_run: bool) -> None:
    spec = parse_job_spec(row)
    slug = slug_from_row(row, spec)
    job_id = row.get("request_id") or spec.get("jobId") or "<no-id>"
    log(f"JOB {job_id} · slug={slug or '<unknown>'}")

    try:
        if slug == "branded-template":
            process_branded_template(sb, row, spec, dry_run)
        elif slug in CREDIT_GATED_SLUGS:
            process_credit_gated(sb, row, spec, slug, dry_run)
        elif slug == "content-calendar":
            process_content_calendar(sb, row, spec, dry_run)
        else:
            msg = f"Unknown / unsupported video-skill slug: {slug!r}"
            log(f"  {msg}")
            if not dry_run and job_id != "<no-id>":
                sb.patch_by_request_id(job_id, {"status": "error", "error": msg})
    except Exception as e:  # noqa: BLE001 — one bad job must not kill the loop
        err = f"{type(e).__name__}: {e}"
        log(f"  ERROR processing {job_id}: {err}")
        if not dry_run and job_id != "<no-id>":
            try:
                sb.patch_by_request_id(job_id, {"status": "error", "error": err[:1000]})
            except Exception as e2:  # noqa: BLE001
                log(f"  (failed to write error status: {e2})")


def run_once(sb: Supabase, dry_run: bool) -> int:
    jobs = sb.select_queued()
    if not jobs:
        log("No queued Video Maker jobs.")
        return 0
    log(f"Found {len(jobs)} queued job(s).")
    for row in jobs:
        process_job(sb, row, dry_run)
    return len(jobs)


def run_watch(sb: Supabase, dry_run: bool, interval: int) -> None:
    log(f"Watch mode — polling every {interval}s. Ctrl-C to stop.")
    while True:
        try:
            run_once(sb, dry_run)
        except Exception as e:  # noqa: BLE001
            log(f"poll error: {type(e).__name__}: {e}")
        time.sleep(max(5, interval))


# ──────────────────────────── Test helpers ────────────────────────────

# Reachable Sugar Shack photo URLs hosted in the MC media bucket. These mirror
# the local public/sugar_shack/*.jpg assets. Used by --insert-test-job.
TEST_PHOTO_URLS = [
    "https://svgsbaahxiaeljmfykzp.supabase.co/storage/v1/object/public/"
    "mission-control-media/sugar_shack/bulk_bins.jpg",
    "https://svgsbaahxiaeljmfykzp.supabase.co/storage/v1/object/public/"
    "mission-control-media/sugar_shack/cone_seats.jpg",
    "https://svgsbaahxiaeljmfykzp.supabase.co/storage/v1/object/public/"
    "mission-control-media/sugar_shack/spaceship_mural.jpg",
    "https://svgsbaahxiaeljmfykzp.supabase.co/storage/v1/object/public/"
    "mission-control-media/sugar_shack/choc_case.jpg",
]


def insert_test_job(sb: Supabase, photo_urls: Optional[list[str]] = None) -> str:
    """Insert a realistic branded-template test job; return its jobId."""
    job_id = str(uuid.uuid4())
    photos = photo_urls or TEST_PHOTO_URLS
    inputs = {
        "business": "sugar_shack",
        "photos": photos,
        "headline": "BEACH DAY ISN'T DONE…",
        "captions": [
            "CANDY BY THE POUND",
            "FRESH ICE CREAM",
            "GALAXY SELFIE WALL",
            "WALL OF CHOCOLATE",
        ],
        "subs": [
            "Fill a bag from the bulk wall",
            "Cones, shakes & sundaes",
            "The island's most Instagrammable stop",
            "Fudge, truffles & fresh-dipped treats",
        ],
        "kicker": "South Padre Island · Summer's Here",
        "ctaPrimary": "Open all summer · the-sugar-shack.com",
        "ctaSecondary": "Tu parada más dulce en la isla",
        "brandColor": "#FF3D8D",
        "music": True,
    }
    spec = {
        "jobId": job_id,
        "slug": "branded-template",
        "skill": "branded-template",
        "cost": 0,
        "inputs": inputs,
        "enqueuedBy": "video_job_worker.test",
        "enqueuedAt": datetime.now(timezone.utc).isoformat(),
    }
    row = {
        "status": "queued",
        "type": "video-skill:branded-template",
        "model": "branded-template",
        "request_id": job_id,
        "url": "pending://queued",
        "media_type": "video",
        "prompt": json.dumps(spec),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.insert(row)
    log(f"Inserted test job {job_id} (status=queued, branded-template).")
    return job_id


# ──────────────────────────── CLI ────────────────────────────


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Mission Control Video Maker — generation worker")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Process queued jobs then exit")
    mode.add_argument("--watch", action="store_true", help="Poll continuously")
    p.add_argument("--interval", type=int, default=30, help="Watch poll interval (seconds)")
    p.add_argument("--dry-run", action="store_true", help="Log intent; no render/upload/PATCH")
    p.add_argument("--insert-test-job", action="store_true", help="Insert a Sugar Shack test job")
    p.add_argument("--delete-job", metavar="REQUEST_ID", help="Delete a media_library row by request_id")
    args = p.parse_args(argv)

    url, key = load_supabase_creds()
    sb = Supabase(url, key)
    log(f"Supabase: {url}")

    if args.delete_job:
        sb.delete_by_request_id(args.delete_job)
        log(f"Deleted media_library row(s) with request_id={args.delete_job}")
        return 0

    if args.insert_test_job:
        job_id = insert_test_job(sb)
        print(f"TEST_JOB_ID={job_id}")
        return 0

    if args.watch:
        run_watch(sb, args.dry_run, args.interval)
        return 0

    # default + --once both run a single pass
    run_once(sb, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
