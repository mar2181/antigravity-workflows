#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a single combined preview page for all 6 March 14 posts
and serve it on http://localhost:8765
"""

import base64
import http.server
import os
import sys
import threading
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PORT = 8765

ADS = [
    {
        "key":      "sugar_shack",
        "name":     "The Sugar Shack",
        "avatar":   "SS",
        "color":    "#e91e63",
        "account":  "Yehuda account",
        "image":    r"C:\Users\mario\sugar_shack_ad_images\march14_spring_break.png",
        "copy": (
            "Spring break just started — and we are READY for you. 🍭\n\n"
            "Pulling up to South Padre Island? Make The Sugar Shack your first stop. "
            "We've got the biggest candy selection on the Island — gummies, chocolates, "
            "saltwater taffy, novelty treats, and more than you can carry in one bag.\n\n"
            "Road trip fuel. Beach day rewards. Late-night sweet fix. Whatever the "
            "occasion, we've got what you're looking for.\n\n"
            "Come in, fill a bag, and make the week sweeter.\n\n"
            "📍 South Padre Island, TX\n\n"
            "#SpringBreak #SouthPadreIsland #SugarShackSPI"
        ),
    },
    {
        "key":      "island_arcade",
        "name":     "Island Arcade SPI",
        "avatar":   "IA",
        "color":    "#7c3aed",
        "account":  "Yehuda account",
        "image":    r"C:\Users\mario\island_arcade_ad_images\march14_spring_break.png",
        "copy": (
            "Spring break is ON and the games are waiting. 🕹️\n\n"
            "Whether you're taking a break from the beach or looking for something to "
            "do after the sun goes down — Island Arcade has you covered. Compete with "
            "your crew, rack up tickets, and walk away with something to brag about.\n\n"
            "No rain required. Just walk in and start playing.\n\n"
            "📍 South Padre Island, TX\n\n"
            "#SpringBreak #IslandArcade #SouthPadreIsland"
        ),
    },
    {
        "key":      "spi",
        "name":     "SPI Fun Rentals",
        "avatar":   "SR",
        "color":    "#0ea5e9",
        "account":  "Yehuda account",
        "image":    r"C:\Users\mario\spi_fun_rentals_ad_images\march14_spring_break.png",
        "copy": (
            "Spring break is here — and the best way to see South Padre Island is "
            "from the seat of a golf cart. 🛻\n\n"
            "Cruise every beach access. Find your favorite sunset spot. Explore the "
            "whole Island on your schedule.\n\n"
            "Golf carts, jeeps, and beach gear — all ready to roll. Availability goes "
            "fast this week, so don't wait.\n\n"
            "📞 (956) 761-9999 | 1314 Padre Blvd #A, South Padre Island\n"
            "spifunrentals.com\n\n"
            "#SpringBreak #SouthPadreIsland #SPIFunRentals"
        ),
    },
    {
        "key":      "island_candy",
        "name":     "Island Candy",
        "avatar":   "IC",
        "color":    "#f59e0b",
        "account":  "Mario account",
        "image":    r"C:\Users\mario\island_candy_ad_images\march14_spring_break.png",
        "copy": (
            "You've been out in the sun all day. You deserve this. 🍦\n\n"
            "Cool off with a scoop (or two) at Island Candy — right inside Island "
            "Arcade on South Padre Island. The perfect pick-me-up after a long beach day.\n\n"
            "Spring break goes by fast. Make every afternoon count.\n\n"
            "📍 Inside Island Arcade — South Padre Island, TX\n\n"
            "#SpringBreak #IslandCandy #SouthPadreIsland"
        ),
    },
    {
        "key":      "juan",
        "name":     "Juan Elizondo RE/MAX Elite",
        "avatar":   "JE",
        "color":    "#cc0000",
        "account":  "Mario account",
        "image":    r"C:\Users\mario\juan_remax_ad_images\march14_spring_market.png",
        "copy": (
            "Spring is one of the best times to make a move in the Rio Grande Valley. 🏡\n\n"
            "Whether you've been thinking about buying, selling, or just want to know "
            "what your home is worth right now — this is the season when buyers are "
            "active and the market is moving.\n\n"
            "The RGV rewards those who act before summer. If you have questions about "
            "your neighborhood, your budget, or what's available — I'm here to help, "
            "no pressure, just answers.\n\n"
            "📱 DM me or call directly — Juan José Elizondo, RE/MAX Elite\n\n"
            "#RGV #McAllen #RealEstate"
        ),
    },
    {
        "key":      "optimum_clinic",
        "name":     "Optimum Health & Wellness Clinic",
        "avatar":   "OC",
        "color":    "#0f766e",
        "account":  "Mario account",
        "image":    r"C:\Users\mario\optimum_clinic_ad_images\march14_after_hours.png",
        "copy": (
            "Spring break is great — until someone gets sick at 8 PM. 🏥\n\n"
            "We're Optimum Health & Wellness Clinic in Pharr, open every night until "
            "10 PM. No appointment needed. No insurance required. Walk right in.\n\n"
            "Sick visits starting at $75. Rapid flu, COVID, and strep tests available. "
            "100% bilingual staff.\n\n"
            "While every other clinic in the RGV closes at 6 or 8 PM — we're still "
            "here for you and your family.\n\n"
            "📍 3912 N Jackson Rd, Pharr, TX | 📞 (956) 627-3258\n"
            "Open 5–10 PM, 7 days a week\n\n"
            "#Pharr #McAllen #RGVHealth"
        ),
    },
]


def img_to_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


def build_card(ad: dict, index: int) -> str:
    b64 = img_to_b64(ad["image"])
    if b64:
        img_tag = f'<img src="data:image/png;base64,{b64}" style="width:100%;display:block;">'
    else:
        img_tag = '<div style="width:100%;height:280px;background:#ddd;display:flex;align-items:center;justify-content:center;color:#888;font-size:13px;">Image not found</div>'

    copy_html = ad["copy"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    return f"""
    <div class="section">
      <div class="section-label">
        <span class="num">{index}</span>
        <span class="biz-name">{ad['name']}</span>
        <span class="acct-badge">{ad['account']}</span>
      </div>
      <div class="card">
        <div class="card-header">
          <div class="avatar" style="background:{ad['color']}">{ad['avatar']}</div>
          <div>
            <div class="page-name">{ad['name']}</div>
            <div class="sub">March 14, 2026 &nbsp;·&nbsp; 🌐 Public</div>
          </div>
        </div>
        <div class="card-body">{copy_html}</div>
        <div class="card-image">{img_tag}</div>
        <div class="card-footer">
          <span class="react">👍 Like</span>
          <span class="react">💬 Comment</span>
          <span class="react">↗️ Share</span>
        </div>
      </div>
    </div>
"""


def build_page() -> str:
    cards = "".join(build_card(ad, i + 1) for i, ad in enumerate(ADS))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>March 14 Posts — All 6 Accounts</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #f0f2f5;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 32px 16px 64px;
  }}
  .page-title {{
    max-width: 540px;
    margin: 0 auto 32px;
    text-align: center;
  }}
  .page-title h1 {{
    font-size: 22px;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 6px;
  }}
  .page-title p {{
    color: #65676b;
    font-size: 14px;
  }}
  .section {{
    max-width: 540px;
    margin: 0 auto 48px;
  }}
  .section-label {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }}
  .num {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #1a1a2e;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .biz-name {{
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
  }}
  .acct-badge {{
    font-size: 11px;
    font-weight: 600;
    color: #fff;
    background: #65676b;
    border-radius: 20px;
    padding: 2px 8px;
    margin-left: auto;
  }}
  .card {{
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 14px rgba(0,0,0,.12);
    overflow: hidden;
  }}
  .card-header {{
    display: flex;
    align-items: center;
    padding: 12px 16px;
    gap: 10px;
  }}
  .avatar {{
    width: 42px;
    height: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: 700;
    font-size: 15px;
    flex-shrink: 0;
  }}
  .page-name {{
    font-weight: 700;
    font-size: 15px;
    color: #050505;
    line-height: 1.3;
  }}
  .sub {{
    font-size: 12px;
    color: #65676b;
    margin-top: 1px;
  }}
  .card-body {{
    padding: 4px 16px 14px;
    font-size: 15px;
    color: #050505;
    line-height: 1.55;
  }}
  .card-image {{
    background: #000;
  }}
  .card-image img {{
    width: 100%;
    display: block;
  }}
  .card-footer {{
    padding: 8px 16px;
    border-top: 1px solid #e4e6eb;
    display: flex;
    gap: 4px;
  }}
  .react {{
    flex: 1;
    text-align: center;
    padding: 7px 4px;
    color: #65676b;
    font-size: 14px;
    font-weight: 600;
    border-radius: 4px;
    cursor: pointer;
  }}
  .react:hover {{ background: #f2f2f2; }}
  .divider {{
    max-width: 540px;
    margin: 0 auto 48px;
    border: none;
    border-top: 2px dashed #d0d3db;
  }}
</style>
</head>
<body>

<div class="page-title">
  <h1>📋 March 14, 2026 — Spring Break Posts</h1>
  <p>6 accounts &nbsp;·&nbsp; Review all before posting</p>
</div>

{cards}

</body>
</html>"""


# ── Simple HTTP handler serving only the combined page ─────────────────────────
HTML_CONTENT = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # suppress request logs


def main():
    global HTML_CONTENT

    print("[BUILD] Embedding images and building preview page...")
    HTML_CONTENT = build_page()
    print(f"[OK]    Page built ({len(HTML_CONTENT) // 1024}KB)")

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"

    print(f"[SERVE] Preview live at: {url}")
    print(f"        Press Ctrl+C to stop\n")

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
