# Video Job Worker — Mission Control Video Maker (Phase 2)

LOCAL poller that turns queued Video Maker jobs (rows in the Supabase
`media_library` table, enqueued by MC PR #120) into rendered videos.

Runs on **this Windows machine** — Remotion + Higgsfield work here; the VPS is
too small to render and the Remotion project isn't deployed there.

- **NO Vercel. NO auto-post. NO credit spend.** Credit skills are gated for Mario.
- Reads Supabase creds from `C:\Users\mario\Projects\missioncontrol\dashboard\.env.local`
  (or env vars `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`).
- Bucket: `mission-control-media`. Outputs land at `video-outputs/<jobId>.mp4`.
- Standard-library only (`urllib`) — no `pip install` needed.

## Run

```powershell
$py = "C:/Users/mario/AppData/Local/Programs/Python/Python310/python.exe"

# Process all currently-queued jobs, then exit
& $py video_job_worker.py --once

# Poll forever (default 30s)
& $py video_job_worker.py --watch --interval 30

# Log what it WOULD do — no render, no upload, no PATCH
& $py video_job_worker.py --once --dry-run
```

> Do **not** register a Windows scheduled task / cron without Mario's go.

## Dispatch table

| slug | cost | action |
|------|------|--------|
| `branded-template` | FREE | auto-render via Remotion → ffprobe-validate → upload → PATCH `status=completed`, `url=<public>` |
| `ad-fanout` | CREDIT | **GATED** — PATCH `status=awaiting_approval` + note. No Higgsfield call, no spend. |
| `animate-photo` | CREDIT | **GATED** — PATCH `status=awaiting_approval` + note. No Higgsfield call, no spend. |
| `content-calendar` | planner | PATCH `status=scheduled`. No video. |

When credit-gen is later enabled: **Higgsfield caps at 2 concurrent jobs on
Ultra** — submit generation calls in pairs, poll each pair to completion before
the next (memory `feedback_higgsfield_2_concurrent_jobs.md`).

## Rendering

- Comp: `BrandedListicle` in `C:\Users\mario\remotion-branded-templates`
  (a generic adapter over the proven `SugarShackBeachStop` kinetic-listicle).
- Props mapped from MC `inputs`: business → brand palette/initials, photos →
  remote `<Img>` beats, headline → slam-in hook, captions → per-beat titles,
  music toggle → client jingle bed. Duration scales with beat count
  (`calculateMetadata`).
- Render: `npx remotion render src/index.ts BrandedListicle <out>.mp4 --props=<tempfile.json>`.
- Validation: `ffprobe` confirms h264, duration > 0.5s, bitrate ≥ 50 kbps
  (rejects the ~17 kbps blank-frame signature) **before** upload.

## End-to-end test (branded-template)

```powershell
$py = "C:/Users/mario/AppData/Local/Programs/Python/Python310/python.exe"

# 1. Insert a realistic Sugar Shack test job (4 hosted pool photos)
& $py video_job_worker.py --insert-test-job   # prints TEST_JOB_ID=<uuid>

# 2. Render it
& $py video_job_worker.py --once

# 3. Verify: out/<jobId>.mp4 exists, the public URL returns 200 video/mp4,
#    and the row flipped to status=completed (see worker log).

# 4. Clean up the test row
& $py video_job_worker.py --delete-job <jobId>
```

## Prereqs

- Node + `npx` on PATH; Remotion project has `node_modules` installed.
- `ffprobe` on PATH (ships with ffmpeg).
- Python 3.10 (`C:/Users/mario/AppData/Local/Programs/Python/Python310/python.exe`).
