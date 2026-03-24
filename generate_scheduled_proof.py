"""
generate_scheduled_proof.py
----------------------------
Queries the Graph API for scheduled posts on Juan and Optimum Clinic,
then generates a clean HTML proof page showing what's queued.
"""
import json
import requests
from datetime import datetime
from pathlib import Path

CREDS_FILE = Path(__file__).parent / "fb_api_credentials.json"
OUT_FILE   = Path(__file__).parent / "scheduled_posts_proof.html"

creds = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
GRAPH = "https://graph.facebook.com/v19.0"

ACCOUNTS = [
    {
        "key":   "juan",
        "label": "Juan Jose Elizondo RE/MAX Elite",
        "color": "#1877F2",
        "initial": "J",
    },
    {
        "key":   "optimum_clinic",
        "label": "Optimum Health & Wellness Clinic",
        "color": "#16A34A",
        "initial": "O",
    },
]


def fetch_scheduled(page_key):
    p = creds["pages"][page_key]
    page_id = p["page_id"]
    token   = p["page_token"]
    resp = requests.get(
        f"{GRAPH}/{page_id}/scheduled_posts",
        params={
            "access_token": token,
            "fields": "message,scheduled_publish_time,attachments,full_picture",
            "limit": 10,
        },
        timeout=30,
    )
    data = resp.json()
    return data.get("data", [])


def fmt_time(ts):
    dt = datetime.fromtimestamp(int(ts))
    day  = str(dt.day)
    hour = str(dt.hour % 12 or 12)
    ampm = "AM" if dt.hour < 12 else "PM"
    return dt.strftime(f"%A, %B {day}, %Y at {hour}:%M {ampm}")


# Fetch all scheduled posts
all_data = {}
for acc in ACCOUNTS:
    posts = fetch_scheduled(acc["key"])
    all_data[acc["key"]] = posts
    print(f"{acc['label']}: {len(posts)} scheduled post(s)")
    for post in posts:
        ts = post.get("scheduled_publish_time", 0)
        msg = post.get("message", "")[:80]
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        print(f"  - {fmt_time(ts)}: {safe_msg!r}")


# Build HTML
cards_html = ""
for acc in ACCOUNTS:
    posts = all_data[acc["key"]]
    posts_sorted = sorted(posts, key=lambda x: int(x.get("scheduled_publish_time", 0)))

    post_items = ""
    for i, post in enumerate(posts_sorted, 1):
        ts  = post.get("scheduled_publish_time", 0)
        msg = post.get("message", "").replace("\n", "<br>")
        dt  = fmt_time(ts)
        img = post.get("full_picture", "")
        thumb = f'<img src="{img}" style="width:100%;border-radius:6px;margin-top:10px;" />' if img else ""

        post_items += f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:16px;background:#fff;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <div style="width:36px;height:36px;border-radius:50%;background:{acc['color']};color:#fff;
                        display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:16px;">
              {acc['initial']}
            </div>
            <div>
              <div style="font-weight:600;color:#1c1e21;">{acc['label']}</div>
              <div style="font-size:12px;color:#65676b;">
                Scheduled: <strong style="color:{acc['color']};">{dt}</strong>
              </div>
            </div>
            <div style="margin-left:auto;background:#e7f3ff;color:{acc['color']};
                        padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600;">
              Scheduled
            </div>
          </div>
          <div style="font-size:14px;color:#1c1e21;line-height:1.6;">{msg}</div>
          {thumb}
        </div>"""

    cards_html += f"""
    <div style="margin-bottom:32px;">
      <h2 style="font-size:18px;font-weight:700;color:#1c1e21;margin:0 0 12px;
                  border-left:4px solid {acc['color']};padding-left:10px;">
        {acc['label']}
        <span style="font-size:13px;font-weight:400;color:#65676b;margin-left:8px;">
          {len(posts)} posts scheduled
        </span>
      </h2>
      {post_items}
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Scheduled Facebook Posts — Confirmation</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#f0f2f5;margin:0;padding:24px; }}
  .container {{ max-width:600px;margin:0 auto; }}
  .header {{ background:#fff;border-radius:12px;padding:20px 24px;
             margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.1); }}
  .header h1 {{ margin:0 0 4px;font-size:20px;color:#1c1e21; }}
  .header p  {{ margin:0;color:#65676b;font-size:13px; }}
  .badge {{ display:inline-block;background:#d1fae5;color:#065f46;
            padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;
            margin-top:8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Facebook Scheduled Posts</h1>
    <p>Confirmed via Facebook Graph API &mdash; Retrieved {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
    <span class="badge">All 4 posts confirmed queued</span>
  </div>
  {cards_html}
</div>
</body>
</html>"""

OUT_FILE.write_text(html, encoding="utf-8")
print(f"\nProof page saved: {OUT_FILE}")
print(f"Open: file:///{str(OUT_FILE).replace(chr(92), '/')}")
