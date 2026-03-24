"""
insta360_asset_extractor.py
----------------------------
Extract high-quality perspective shots from Insta360 equirectangular
360° video (.mp4, .insv) or still images (.jpg, .png).

Usage:
  python insta360_asset_extractor.py <input_file> [options]

Options:
  --presets all|front|sides|zoom|angles   Preset group (default: all)
  --output <folder>                        Output directory (default: ./insta360_exports/<filename>)
  --quality <1-31>                         JPEG quality (default: 2 = highest)
  --frame <seconds>                        Video: timestamp to extract frame from (default: 3)
  --no-gallery                             Skip HTML gallery generation

Examples:
  python insta360_asset_extractor.py "business.jpg" --presets all
  python insta360_asset_extractor.py "tour.mp4" --frame 5 --output ./assets/
"""

import argparse
import subprocess
import sys
import io
import shutil
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows so arrow/check chars don't crash
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Shot preset library ─────────────────────────────────────────────────────

PRESETS = {
    # Group: front
    "front_wide":       dict(yaw=0,    pitch=0,   fov=110, group="front",  label="Front — Wide Angle"),
    "front_standard":   dict(yaw=0,    pitch=0,   fov=80,  group="front",  label="Front — Standard"),
    "front_zoom":       dict(yaw=0,    pitch=0,   fov=45,  group="zoom",   label="Front — Telephoto Zoom"),
    # Group: sides
    "right_side":       dict(yaw=90,   pitch=0,   fov=80,  group="sides",  label="Right Side"),
    "left_side":        dict(yaw=-90,  pitch=0,   fov=80,  group="sides",  label="Left Side"),
    "rear":             dict(yaw=180,  pitch=0,   fov=80,  group="sides",  label="Rear View"),
    # Group: angles (diagonals)
    "corner_FL":        dict(yaw=-45,  pitch=0,   fov=80,  group="angles", label="Corner — Front Left"),
    "corner_FR":        dict(yaw=45,   pitch=0,   fov=80,  group="angles", label="Corner — Front Right"),
    "corner_RL":        dict(yaw=-135, pitch=0,   fov=80,  group="angles", label="Corner — Rear Left"),
    "corner_RR":        dict(yaw=135,  pitch=0,   fov=80,  group="angles", label="Corner — Rear Right"),
    # Group: vertical
    "overhead_tilt":    dict(yaw=0,    pitch=-45, fov=90,  group="angles", label="Overhead Tilt (Up)"),
    "low_angle":        dict(yaw=0,    pitch=30,  fov=80,  group="angles", label="Low Angle (Down)"),
    # Group: cinematic
    "cinematic_zoom":   dict(yaw=0,    pitch=-15, fov=55,  group="zoom",   label="Cinematic — Vertical Pull"),
    "cinematic_right":  dict(yaw=60,   pitch=-10, fov=65,  group="zoom",   label="Cinematic — Right Pan"),
    "cinematic_left":   dict(yaw=-60,  pitch=-10, fov=65,  group="zoom",   label="Cinematic — Left Pan"),
}

GROUP_KEYS = {
    "all":    list(PRESETS.keys()),
    "front":  [k for k, v in PRESETS.items() if v["group"] == "front"],
    "sides":  [k for k, v in PRESETS.items() if v["group"] == "sides"],
    "zoom":   [k for k, v in PRESETS.items() if v["group"] == "zoom"],
    "angles": [k for k, v in PRESETS.items() if v["group"] == "angles"],
}

# ── FFmpeg helpers ───────────────────────────────────────────────────────────

def ffmpeg_path():
    ff = shutil.which("ffmpeg")
    if not ff:
        sys.exit("ERROR: ffmpeg not found in PATH. Install it or check your environment.")
    return ff

def extract_frame_from_video(input_path: Path, frame_path: Path, timestamp: float):
    """Extract a single equirectangular frame from a 360 video."""
    cmd = [
        ffmpeg_path(), "-y",
        "-ss", str(timestamp),
        "-i", str(input_path),
        "-frames:v", "1",
        "-q:v", "1",
        str(frame_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ffmpeg stderr]: {result.stderr[-500:]}")
        sys.exit("ERROR: Failed to extract frame from video.")

def extract_perspective_ffmpeg(input_path: Path, output_path: Path, yaw: int, pitch: int, fov: int, quality: int = 2):
    """Use FFmpeg v360 filter to extract a perspective view from equirectangular input."""
    v360_filter = (
        f"v360=e:rectilinear"
        f":yaw={yaw}:pitch={pitch}:roll=0"
        f":h_fov={fov}:v_fov={int(fov * 0.5625)}"   # 16:9 ratio
        f":w=1920:h=1080"
        f":interp=lanczos"
    )
    cmd = [
        ffmpeg_path(), "-y",
        "-i", str(input_path),
        "-frames:v", "1",
        "-vf", v360_filter,
        "-q:v", str(quality),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [warn] ffmpeg failed for {output_path.name}: {result.stderr[-300:]}")
        return False
    return True

# ── Still image extraction via py360convert ──────────────────────────────────

def extract_perspective_py360(input_path: Path, output_path: Path, yaw: int, pitch: int, fov: int):
    """
    Use py360convert for high-quality still image perspective extraction.
    py360convert uses bicubic interpolation — better for hero/ad images.
    """
    try:
        import py360convert
        import numpy as np
        from PIL import Image
    except ImportError:
        return False  # Fall back to ffmpeg

    try:
        img = np.array(Image.open(str(input_path)).convert("RGB"))
        out = py360convert.e2p(
            img,
            fov_deg=(fov, int(fov * 0.5625)),   # (h_fov, v_fov) → 16:9
            u_deg=yaw,
            v_deg=-pitch,                         # py360convert: positive = up
            out_hw=(1080, 1920),
            in_rot_deg=0,
            mode="bilinear",
        )
        Image.fromarray(out.astype("uint8")).save(str(output_path), quality=95)
        return True
    except Exception as e:
        print(f"  [warn] py360convert failed: {e}")
        return False

# ── HTML gallery generator ───────────────────────────────────────────────────

def generate_gallery(output_dir: Path, results: list, source_name: str):
    cards = ""
    for item in results:
        rel = Path(item["path"]).name
        status_badge = (
            '<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;">✓ OK</span>'
            if item["ok"] else
            '<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;">✗ Failed</span>'
        )
        img_tag = f'<img src="{rel}" style="width:100%;border-radius:8px;display:block;" loading="lazy">' if item["ok"] else '<div style="height:200px;background:#1e293b;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#64748b">No output</div>'
        cards += f"""
        <div style="background:#1e293b;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.4);">
          {img_tag}
          <div style="padding:12px;">
            <div style="font-weight:600;color:#f1f5f9;margin-bottom:4px;">{item['label']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">
              yaw={item['yaw']}° &nbsp;|&nbsp; pitch={item['pitch']}° &nbsp;|&nbsp; fov={item['fov']}°
            </div>
            {status_badge}
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>360° Asset Gallery — {source_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0f172a; color: #f1f5f9; font-family: system-ui, sans-serif; padding: 32px; }}
    h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 4px; }}
    .sub {{ color: #64748b; font-size: 13px; margin-bottom: 32px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
  </style>
</head>
<body>
  <h1>360° Asset Extractor — {source_name}</h1>
  <div class="sub">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; {len([r for r in results if r['ok']])} of {len(results)} shots exported</div>
  <div class="grid">{cards}</div>
</body>
</html>"""

    gallery_path = output_dir / "gallery.html"
    gallery_path.write_text(html, encoding="utf-8")
    return gallery_path

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract perspective shots from Insta360 360° media")
    parser.add_argument("input", help="Path to equirectangular .jpg/.png/.mp4/.insv file")
    parser.add_argument("--presets", default="all", choices=["all", "front", "sides", "zoom", "angles"],
                        help="Preset group to export (default: all)")
    parser.add_argument("--output", default=None, help="Output folder path")
    parser.add_argument("--quality", type=int, default=2, help="JPEG quality 1-31 (1=best, default=2)")
    parser.add_argument("--frame", type=float, default=3.0,
                        help="Video only: timestamp in seconds to extract frame (default: 3)")
    parser.add_argument("--no-gallery", action="store_true", help="Skip HTML gallery generation")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        sys.exit(f"ERROR: File not found: {input_path}")

    # Output directory
    stem = input_path.stem
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = Path(__file__).parent / "insta360_exports" / stem
    output_dir.mkdir(parents=True, exist_ok=True)

    is_video = input_path.suffix.lower() in {".mp4", ".mov", ".insv", ".avi"}
    is_image = input_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}

    # For video: extract source frame first
    if is_video:
        print(f"[>] Video detected. Extracting frame at {args.frame}s ...")
        source_frame = output_dir / "_source_frame.jpg"
        extract_frame_from_video(input_path, source_frame, args.frame)
        working_input = source_frame
    elif is_image:
        working_input = input_path
    else:
        sys.exit(f"ERROR: Unsupported file type: {input_path.suffix}")

    # Select preset keys
    keys = GROUP_KEYS.get(args.presets, GROUP_KEYS["all"])
    print(f"[>] Extracting {len(keys)} shots from: {input_path.name}")
    print(f"[>] Output folder: {output_dir}\n")

    results = []
    for key in keys:
        p = PRESETS[key]
        out_file = output_dir / f"{key}.jpg"
        print(f"  [{key}] {p['label']} (yaw={p['yaw']}° pitch={p['pitch']}° fov={p['fov']}°) ...", end=" ", flush=True)

        ok = False
        # Try py360convert first for still images (higher quality)
        if is_image or (is_video):
            ok = extract_perspective_py360(working_input, out_file, p["yaw"], p["pitch"], p["fov"])
        # Fallback: FFmpeg v360
        if not ok:
            ok = extract_perspective_ffmpeg(working_input, out_file, p["yaw"], p["pitch"], p["fov"], args.quality)

        size_kb = f"{out_file.stat().st_size // 1024} KB" if ok and out_file.exists() else "—"
        print(f"{'✓' if ok else '✗'} {size_kb}")

        results.append({
            "key": key,
            "label": p["label"],
            "path": str(out_file),
            "yaw": p["yaw"],
            "pitch": p["pitch"],
            "fov": p["fov"],
            "ok": ok and out_file.exists(),
        })

    success = sum(1 for r in results if r["ok"])
    print(f"\n[✓] Done — {success}/{len(keys)} shots exported to: {output_dir}")

    if not args.no_gallery:
        gallery = generate_gallery(output_dir, results, stem)
        print(f"[→] Gallery: file:///{str(gallery).replace(chr(92), '/')}")
        print(f"\n    Drag this into your browser or copy-paste the path above.")

if __name__ == "__main__":
    main()
