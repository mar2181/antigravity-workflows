"""
shutdown_capture.py — Capture all monitors + active-window context on shutdown.

Triggered manually by Claude when Mario announces he's turning off his computer.
Saves screenshots to ~/.claude/shutdown_screenshots/YYYY-MM-DD_HHMMSS/ along with
a context.md describing what was open. The next session's start hook picks the
most recent capture and surfaces it to the new Claude instance.

Usage:
    python shutdown_capture.py              # capture all monitors
    python shutdown_capture.py --note "X"   # capture + custom note in context.md
    python shutdown_capture.py --latest     # print path to most-recent capture
"""

from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

CAPTURE_ROOT = Path.home() / ".claude" / "shutdown_screenshots"

PS_CAPTURE = r"""
$outdir = "{outdir}"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screens = [System.Windows.Forms.Screen]::AllScreens
for ($i = 0; $i -lt $screens.Length; $i++) {{
    $screen = $screens[$i]
    $bounds = $screen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $primary = if ($screen.Primary) {{ "_primary" }} else {{ "" }}
    $path = Join-Path $outdir ("monitor_" + ($i + 1) + $primary + ".png")
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    Write-Output $path
}}
Get-Process | Where-Object {{ $_.MainWindowTitle -ne "" }} |
    Select-Object ProcessName, MainWindowTitle |
    Sort-Object ProcessName |
    ForEach-Object {{ "WIN|" + $_.ProcessName + "|" + $_.MainWindowTitle }}
"""


def capture(note: str | None = None) -> Path:
    ts = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = CAPTURE_ROOT / ts
    outdir.mkdir(parents=True, exist_ok=True)

    ps_script = PS_CAPTURE.format(outdir=str(outdir).replace("\\", "\\\\"))
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print("PowerShell capture failed:", result.stderr, file=sys.stderr)
        sys.exit(1)

    monitor_paths = []
    windows = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("WIN|"):
            _, proc, title = line.split("|", 2)
            windows.append((proc, title))
        elif line.endswith(".png"):
            monitor_paths.append(line)

    context_md = outdir / "context.md"
    body = [f"# Shutdown Capture — {ts}", ""]
    if note:
        body.extend(["## Note from Mario", "", note, ""])
    body.append("Mario announced he was shutting down his computer. This snapshot")
    body.append("was captured immediately so the next session can pick up context.")
    body.append("")
    body.append("## Monitors captured")
    body.append("")
    for p in monitor_paths:
        body.append(f"- {p}")
    body.append("")
    body.append("## Active windows at capture (process | title)")
    body.append("")
    for proc, title in windows:
        body.append(f"- `{proc}` | {title}")
    body.append("")
    body.append("## Working directory")
    body.append("")
    body.append(f"- {os.getcwd()}")
    body.append("")
    body.append("## How to use this in the next session")
    body.append("")
    body.append("- The session-start hook (or memory rule `shutdown_screenshot_trigger`)")
    body.append("  surfaces this path so the new Claude can read context.md or view")
    body.append("  the PNGs.")
    body.append("- If Mario opens a fresh session: 'pick up where I left off' should")
    body.append("  trigger reading the most recent capture under ~/.claude/shutdown_screenshots/.")
    context_md.write_text("\n".join(body), encoding="utf-8")

    manifest = outdir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "monitors": monitor_paths,
                "windows": [{"process": p, "title": t} for p, t in windows],
                "cwd": os.getcwd(),
                "note": note,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return outdir


def latest() -> Path | None:
    if not CAPTURE_ROOT.exists():
        return None
    captures = sorted([p for p in CAPTURE_ROOT.iterdir() if p.is_dir()])
    return captures[-1] if captures else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--note", default=None, help="Free-text note saved into context.md")
    parser.add_argument("--latest", action="store_true", help="Print path to most-recent capture and exit")
    args = parser.parse_args()

    if args.latest:
        p = latest()
        if p:
            print(str(p))
        sys.exit(0)

    outdir = capture(args.note)
    print(f"Captured to: {outdir}")
    for f in sorted(outdir.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
