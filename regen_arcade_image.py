#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate Island Arcade image — Street Fighter vs Special Ops concept.
"""
import os, sys, urllib.request, base64, http.server, threading, webbrowser
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import fal_client
except ImportError:
    os.system(f"{sys.executable} -m pip install fal_client -q")
    import fal_client

os.environ["FAL_KEY"] = "39cee61b-1fb5-40ca-b489-7ff6bcec01ad:e223d38f3f0f8df11bff0b49cc46a73f"

PROMPT = (
    "Epic video game crossover battle scene: a classic Street Fighter-style martial arts "
    "character in a dynamic fighting stance — glowing fists, dramatic energy aura, "
    "colorful costume — squaring off against a heavily armored modern Special Ops military "
    "soldier character with tactical gear and futuristic weapon; both characters facing each "
    "other in an electrifying standoff, neon-lit dramatic arena background with crowd "
    "silhouettes, cinematic game art style, intense action lighting, high contrast, "
    "professional digital art, 4k"
)

OUT_DIR  = r"C:\Users\mario\island_arcade_ad_images"
FILENAME = "march14_spring_break.png"
PORT     = 8765

COPY = (
    "Spring break is ON and the games are waiting. 🕹️\n\n"
    "Whether you're taking a break from the beach or looking for something to "
    "do after the sun goes down — Island Arcade has you covered. Compete with "
    "your crew, rack up tickets, and walk away with something to brag about.\n\n"
    "No rain required. Just walk in and start playing.\n\n"
    "📍 South Padre Island, TX\n\n"
    "#SpringBreak #IslandArcade #SouthPadreIsland"
)


def generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    filepath = os.path.join(OUT_DIR, FILENAME)
    print("[GEN] Island Arcade — Street Fighter vs Special Ops...")
    handler = fal_client.submit(
        "fal-ai/flux-pro/v1.1-ultra",
        arguments={"prompt": PROMPT, "image_size": "landscape_16_9", "num_images": 1},
    )
    result = handler.get()
    url = result["images"][0]["url"]
    print("      Downloading...")
    urllib.request.urlretrieve(url, filepath)
    size = os.path.getsize(filepath) / (1024*1024)
    print(f"      [OK] {filepath} ({size:.1f}MB)")
    return filepath


def build_page(img_path):
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    copy_html = COPY.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Preview — Island Arcade</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#f0f2f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; padding:32px 16px; }}
  .title {{ max-width:540px; margin:0 auto 24px; text-align:center; }}
  .title h1 {{ font-size:20px; font-weight:800; color:#1a1a2e; margin-bottom:4px; }}
  .title p {{ font-size:13px; color:#65676b; }}
  .card {{ max-width:540px; margin:0 auto; background:#fff; border-radius:10px; box-shadow:0 2px 14px rgba(0,0,0,.13); overflow:hidden; }}
  .header {{ display:flex; align-items:center; padding:12px 16px; gap:10px; }}
  .avatar {{ width:42px; height:42px; border-radius:50%; background:#7c3aed; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:15px; flex-shrink:0; }}
  .page-name {{ font-weight:700; font-size:15px; color:#050505; }}
  .sub {{ font-size:12px; color:#65676b; }}
  .body {{ padding:4px 16px 14px; font-size:15px; color:#050505; line-height:1.55; }}
  .image-wrap img {{ width:100%; display:block; }}
  .footer {{ padding:8px 16px; border-top:1px solid #e4e6eb; display:flex; gap:4px; }}
  .react {{ flex:1; text-align:center; padding:7px; color:#65676b; font-size:14px; font-weight:600; border-radius:4px; cursor:pointer; }}
  .react:hover {{ background:#f2f2f2; }}
</style>
</head>
<body>
<div class="title">
  <h1>📋 Island Arcade — March 14 Preview</h1>
  <p>Street Fighter vs Special Ops concept · Approve to post all 6</p>
</div>
<div class="card">
  <div class="header">
    <div class="avatar">IA</div>
    <div>
      <div class="page-name">Island Arcade SPI</div>
      <div class="sub">March 14, 2026 · 🌐 Public</div>
    </div>
  </div>
  <div class="body">{copy_html}</div>
  <div class="image-wrap"><img src="data:image/png;base64,{b64}"></div>
  <div class="footer">
    <span class="react">👍 Like</span>
    <span class="react">💬 Comment</span>
    <span class="react">↗️ Share</span>
  </div>
</div>
</body>
</html>"""


HTML = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))
    def log_message(self, *a): pass


def main():
    global HTML
    img = generate()
    HTML = build_page(img)
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n[SERVE] http://localhost:{PORT}")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
