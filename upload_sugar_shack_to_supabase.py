"""
Upload 144 Sugar Shack 360-extracted images to Supabase Storage.
Bucket: sugar-shack-images
Organizes by clip folder: clip_001/, clip_002/, etc.
"""
import sys
import requests
from pathlib import Path

SUPABASE_URL = "https://svgsbaahxiaeljmfykzp.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN2Z3NiYWFoeGlhZWxqbWZ5a3pwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEyODc2ODksImV4cCI6MjA1Njg2MzY4OX0.S80GrL92vr2F-dwzWZqaz3Gt8RgttRi8ccC9y6sRQfI"
BUCKET = "sugar-shack-images"
SOURCE_DIR = Path(r"C:\Users\mario\.gemini\antigravity\tools\execution\sugar_shack\assets\images\360_shots")

HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
}

def upload_file(local_path: Path, remote_path: str) -> bool:
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{remote_path}"
    content_type = "image/jpeg"
    with open(local_path, "rb") as f:
        resp = requests.post(
            url,
            headers={**HEADERS, "Content-Type": content_type},
            data=f.read(),
        )
    if resp.status_code in (200, 201):
        return True
    else:
        print(f"  FAIL [{resp.status_code}]: {remote_path} — {resp.text[:200]}")
        return False

def main():
    if not SOURCE_DIR.exists():
        print(f"Source dir not found: {SOURCE_DIR}")
        sys.exit(1)

    clip_dirs = sorted([d for d in SOURCE_DIR.iterdir() if d.is_dir()])
    print(f"Found {len(clip_dirs)} clip folders in {SOURCE_DIR}\n")

    total = 0
    success = 0
    failed = 0

    for clip_dir in clip_dirs:
        clip_name = clip_dir.name
        images = sorted([f for f in clip_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
        print(f"-- {clip_name}: {len(images)} images")

        for img in images:
            remote_path = f"{clip_name}/{img.name}"
            total += 1
            ok = upload_file(img, remote_path)
            if ok:
                success += 1
                print(f"  OK{remote_path}")
            else:
                failed += 1

    print(f"\n{'='*50}")
    print(f"Done! {success}/{total} uploaded, {failed} failed")
    print(f"View at: https://supabase.com/dashboard/project/svgsbaahxiaeljmfykzp/storage/files/buckets/sugar-shack-images")

if __name__ == "__main__":
    main()
