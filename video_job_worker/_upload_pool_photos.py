"""One-off: upload the 4 Sugar Shack pool photos to the MC media bucket so the
branded-template test (and real client-pool inputs) have reachable remote URLs.
Reuses the worker's own Supabase client. Prints only URLs/status (never the key)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_job_worker import load_supabase_creds, Supabase  # noqa: E402

PUB = Path(r"C:\Users\mario\remotion-branded-templates\public\sugar_shack")
NAMES = ["bulk_bins", "cone_seats", "spaceship_mural", "choc_case"]

url, key = load_supabase_creds()
sb = Supabase(url, key)
print(f"Supabase: {url}")
for n in NAMES:
    f = PUB / f"{n}.jpg"
    data = f.read_bytes()
    pub = sb.upload_object(f"sugar_shack/{n}.jpg", data, "image/jpeg")
    print(f"{n}.jpg -> {pub} ({len(data)} bytes)")
print("DONE")
