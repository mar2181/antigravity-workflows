"""
Swap gTTS voice on Sugar Shack v2 + v3 with ElevenLabs Hope.

Strategy:
  - Existing branded videos already have correct visuals (clips + captions + brand overlay)
  - Just strip the old audio and re-mix with Hope VO + original music
  - No need to re-burn anything visual

Steps per version:
  1. Generate Hope VO via ElevenLabs (voice zGjIP4SZlMnY9m93k97r)
  2. Mix Hope VO + original music track onto existing branded video
  3. Upload new video to Supabase
  4. Update ad_creative record (or insert new one)
"""
import subprocess, json, urllib.request, urllib.error, sys, time
from pathlib import Path

RUNS_BASE  = Path("C:/Users/mario/.gemini/antigravity/tools/execution/content_loop/runs")
MUSIC_BASE = Path("C:/Users/mario/.gemini/antigravity/tools/execution/ad_music_library/tracks/youtube")

XI_KEY   = "sk_3514e27a0f0a412d95fd6e2c6a192ddcb0c4bcee100f2d7f"
VOICE_ID = "zGjIP4SZlMnY9m93k97r"   # Hope — Clear, Relatable and Charismatic

VO_SCRIPT = (
    "Step inside The Sugar Shack — South Padre Island's wildest candy destination. "
    "Wall-to-wall sweets, a giant astronaut rocket right at the center, a lollipop tree "
    "that'll blow your mind, gummies in every shape and color, a real carousel, and photo "
    "spots so wild you won't believe you're still in a candy store. Come in, grab a bag, "
    "fill it up with whatever looks good, ride the carousel, and taste something you've "
    "never had before. Open every day in the heart of South Padre. "
    "The Sugar Shack — where every visit is out of this world."
)

VERSIONS = [
    {
        "run":         "2026-04-20_sugar_shack_phone_v2",
        "label":       "V2",
        "music_file":  MUSIC_BASE / "jack_harlow_lovin_on_me.mp3",
        "music_start": 0.0,
        "music_track": "Jack Harlow – Lovin On Me",
        "music_slug":  "jack_harlow_lovin_on_me",
        "ad_id":       "58bde802-76a0-4420-9f61-4e94ceffa310",
    },
    {
        "run":         "2026-04-20_sugar_shack_phone_v3",
        "label":       "V3",
        "music_file":  MUSIC_BASE / "doja_cat_paint_the_town_red.mp3",
        "music_start": 52.0,
        "music_track": "Doja Cat – Paint The Town Red",
        "music_slug":  "doja_cat_paint_the_town_red",
        "ad_id":       "735db699-770e-4103-97c5-a7345a81d3ee",
    },
]

VIDEO_DUR   = 35.3
MUSIC_LEVEL = 0.09
VO_LEVEL    = 0.95

SUPA_URL = "https://svgsbaahxiaeljmfykzp.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN2Z3NiYWFoeGlhZWxqbWZ5a3pwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEyODc2ODksImV4cCI6MjA1Njg2MzY4OX0.S80GrL92vr2F-dwzWZqaz3Gt8RgttRi8ccC9y6sRQfI"
SUGAR_SHACK_CLIENT_ID = "fb6f5c22-06d1-43c0-829a-08f6feb5b206"

for ver in VERSIONS:
    HERE   = RUNS_BASE / ver["run"]
    LABEL  = ver["label"]
    MUSIC  = ver["music_file"]
    MSTART = ver["music_start"]

    BRANDED_IN = HERE / "final_phone_7clip_voiced_music_captioned_branded.mp4"
    VO_OUT     = HERE / "voiceover_hope.mp3"
    FINAL_OUT  = HERE / "final_phone_7clip_hope_branded.mp4"

    print(f"\n{'='*60}")
    print(f"  {LABEL} — {ver['music_track']}")
    print(f"{'='*60}")

    # 1. Generate Hope VO via ElevenLabs
    print(f"\n[1/3] Generating Hope VO via ElevenLabs...")
    xi_url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    payload = json.dumps({
        "text": VO_SCRIPT,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        xi_url, data=payload, method="POST",
        headers={
            "xi-api-key": XI_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        VO_OUT.write_bytes(r.read())
    print(f"[OK] Hope VO: {VO_OUT.stat().st_size/1024:.1f} KB")

    # 2. Mix Hope VO + music onto existing branded video (replace audio only)
    print(f"\n[2/3] Mixing Hope VO + {ver['music_track']} onto existing branded video...")
    fc = (
        f"[1:a]volume={VO_LEVEL},apad[vo];"
        f"[2:a]atrim=start={MSTART}:duration={VIDEO_DUR},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.5,afade=t=out:st={VIDEO_DUR-0.6}:d=0.6,"
        f"volume={MUSIC_LEVEL}[bed];"
        f"[vo][bed]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[mix]"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(BRANDED_IN),   # video source (visuals already done)
        "-i", str(VO_OUT),        # Hope VO
        "-i", str(MUSIC),         # music bed
        "-filter_complex", fc,
        "-map", "0:v",            # video from branded source
        "-map", "[mix]",          # new audio mix
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(VIDEO_DUR),
        str(FINAL_OUT),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    final_mb = FINAL_OUT.stat().st_size / 1024 / 1024
    print(f"[OK] Final: {final_mb:.2f} MB -> {FINAL_OUT.name}")

    # 3. Upload to Supabase storage
    print(f"\n[3/3] Uploading to Supabase...")
    storage_path = f"videos/sugar_shack/2026-04-20_phone_ad_{ver['label'].lower()}_hope_{int(time.time())}.mp4"
    upload_url   = f"{SUPA_URL}/storage/v1/object/mission-control-media/{storage_path}"
    req2 = urllib.request.Request(
        upload_url, data=FINAL_OUT.read_bytes(), method="POST",
        headers={"Authorization": f"Bearer {ANON_KEY}", "Content-Type": "video/mp4", "x-upsert": "true"}
    )
    with urllib.request.urlopen(req2, timeout=300) as r:
        json.loads(r.read())
    public_url = f"{SUPA_URL}/storage/v1/object/public/mission-control-media/{storage_path}"
    print(f"[OK] {storage_path}")

    # 4. Update existing ad_creative record with new URL + note
    print(f"\n[4/4] Updating ad_creative {ver['ad_id'][:8]}... in Mission Control...")
    update = {
        "fal_url":          public_url,
        "size_mb":          round(final_mb, 2),
        "generation_model": f"kling-v2.1-pro + ElevenLabs Hope + {ver['music_track']}",
        "notes":            f"35.3s phone reel {LABEL}. Hope (ElevenLabs zGjIP4SZlMnY9m93k97r) VO. {ver['music_track']}. Updated {time.strftime('%Y-%m-%d')}.",
    }
    req3 = urllib.request.Request(
        f"http://localhost:3001/api/ad-creatives/{ver['ad_id']}",
        data=json.dumps(update).encode("utf-8"),
        method="PATCH",
        headers={"Content-Type": "application/json"}
    )
    try:
        resp3 = json.loads(urllib.request.urlopen(req3, timeout=15).read())
        print(f"[OK] Updated: {resp3.get('ad', {}).get('id', 'unknown')[:8]}...")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # If PATCH not supported, fall back to re-insert
        print(f"[!] PATCH failed ({e.code}): {body[:200]} — inserting new record instead")
        copy_body = (
            "Walls of candy. Giant astronaut. A real carousel. Photo spots you wont believe.\n\n"
            "The Sugar Shack is South Padre Islands wildest candy destination - "
            "open every day right in the heart of SPI.\n\n"
            "Come get a little sugar crazy with us.\n\nSouth Padre Island, TX"
        )
        record = {
            "client_id":        SUGAR_SHACK_CLIENT_ID,
            "name":             f"[Daily Video - phone] The Sugar Shack - 2026-04-20 ({LABEL} - {ver['music_track']} - Hope VO)",
            "fal_url":          public_url,
            "media_type":       "video",
            "size_mb":          round(final_mb, 2),
            "copy_headline":    "South Padre Islands Wildest Candy Destination",
            "copy_body":        copy_body,
            "copy_cta":         "Visit Us Today",
            "copy_hashtags":    "#SugarShack #SouthPadreIsland #CandyStore",
            "status":           "draft",
            "rating":           0,
            "platform":         "facebook",
            "generation_model": f"kling-v2.1-pro + ElevenLabs Hope + {ver['music_track']}",
            "generation_prompt": f"7-clip phone reel 1080x1920 35s. {LABEL} variant. Hope ElevenLabs VO + {ver['music_track']} @ 9% + captions + brand overlay.",
            "music_track_slug": ver["music_slug"],
            "notes":            f"35.3s phone reel {LABEL}. Hope (ElevenLabs) VO. {ver['music_track']}. Rebuilt {time.strftime('%Y-%m-%d')}.",
        }
        req4 = urllib.request.Request(
            "http://localhost:3001/api/ad-creatives",
            data=json.dumps(record).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        resp4 = json.loads(urllib.request.urlopen(req4, timeout=15).read())
        print(f"[OK] New ad_creative: {resp4.get('ad', {}).get('id', 'unknown')[:8]}...")

    print(f"[DONE] {LABEL} complete")

print(f"""
Both videos updated with Hope's voice:
  V2 (Jack Harlow)  — updated in ad library
  V3 (Doja Cat)     — updated in ad library

View: http://localhost:3001/content/ad-library → Sugar Shack
""")
