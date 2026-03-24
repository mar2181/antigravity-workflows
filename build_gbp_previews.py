import sys
sys.stdout.reconfigure(encoding='utf-8')

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GBP Preview — {title}</title>
<style>
  body{{margin:0;padding:24px;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;}}
  .lbl{{max-width:520px;margin:0 auto 12px;color:#1a73e8;font-size:13px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;}}
  .meta{{max-width:520px;margin:0 auto 8px;color:#65676b;font-size:12px;}}
  .card{{max-width:520px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden;}}
  .hdr{{display:flex;align-items:center;padding:12px 16px;gap:10px;}}
  .av{{width:42px;height:42px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:15px;flex-shrink:0;}}
  .pn{{font-weight:700;font-size:15px;color:#050505;line-height:1.2;}}
  .sp{{font-size:12px;color:#65676b;}}
  .body{{padding:0 16px 12px;font-size:15px;color:#050505;line-height:1.5;white-space:pre-wrap;}}
  .img img{{width:100%;display:block;}}
  .bar{{max-width:520px;margin:16px auto 0;display:flex;gap:12px;}}
  .btn{{flex:1;padding:12px;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;}}
  .ok{{background:{color};color:#fff;}}
  .sk{{background:#e4e6eb;color:#050505;}}
  .msg{{display:none;max-width:520px;margin:12px auto;padding:12px 16px;background:#d4edda;color:#155724;border-radius:8px;font-weight:600;font-size:14px;}}
  .gbp-badge{{display:inline-block;background:#1a73e8;color:#fff;font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px;margin-bottom:6px;}}
</style>
</head>
<body>
<div class="lbl">🗺️ Google Business Profile Preview</div>
<span class="gbp-badge">GBP POST</span>
<div class="meta">📅 2026-03-15 &nbsp;|&nbsp; Angle: {angle} &nbsp;|&nbsp; Platform: Google Business Profile</div>
<div class="card">
  <div class="hdr">
    <div class="av">{initials}</div>
    <div><div class="pn">{page_name}</div><div class="sp">Google Business Profile · Update</div></div>
  </div>
  <div class="body">{copy}</div>
  <div class="img"><img src="{image_path}"></div>
</div>
<div class="bar">
  <button class="btn ok" onclick="approve()">✅ APPROVED — Post this</button>
  <button class="btn sk" onclick="skip()">⏭ Skip</button>
</div>
<div class="msg" id="msg">✅ Approved! Return to terminal and press Y.</div>
<script>
function approve(){{document.getElementById('msg').style.display='block';document.querySelector('.ok').disabled=true;document.querySelector('.ok').textContent='✅ Approved';}}
function skip(){{document.querySelector('.sk').textContent='⏭ Skipped';document.querySelector('.sk').disabled=true;}}
</script>
</body>
</html>'''

ads = [
    {
        'out': 'C:/Users/mario/sugar_shack_ad_images/preview_gbp_ad9.html',
        'title': 'Sugar Shack — GBP Ad 9 — Last Stop Home',
        'angle': 'last_stop_home',
        'color': '#e91e63',
        'initials': 'SS',
        'page_name': 'The Sugar Shack',
        'copy': (
            "Don't leave the island without this stop. 🍬\n\n"
            "The Sugar Shack is South Padre Island's favorite candy store — and your last chance to grab "
            "something sweet before you hit the road home.\n\n"
            "🍭 Bulk candy — pick exactly what you want, pay by the piece\n"
            "🌈 Novelty treats the kids won't find anywhere else\n"
            "🏖️ Souvenir sweets that actually taste good\n"
            "💰 Low enough to stock up the whole car\n\n"
            "Five minutes and a full bag. Smiles all the way home.\n\n"
            "📍 910 Padre Blvd, South Padre Island, TX\n"
            "📞 (956) 524-8009\n"
            "Open 7 days a week\n\n"
            "#SouthPadreIsland #CandyStore #SPI"
        ),
        'image_path': 'ad_9_last_stop_home.png',
    },
    {
        'out': 'C:/Users/mario/island_candy_ad_images/preview_gbp_ad12.html',
        'title': 'Island Candy — GBP Ad 12 — Beach to Candy',
        'angle': 'beach_to_candy',
        'color': '#9c27b0',
        'initials': 'IC',
        'page_name': 'Island Candy',
        'copy': (
            "Beach day done. Now comes the best part. 🍦\n\n"
            "Island Candy is the sweet stop right inside Island Arcade on Padre Blvd — "
            "homemade ice cream made fresh, served fast, and priced for the whole family.\n\n"
            "🍦 Scoops, sundaes, and specialty flavors\n"
            "🍬 Candy treats to go alongside your scoop\n"
            "🎮 Inside Island Arcade — one stop for games AND sweets\n"
            "💵 Homemade ice cream starting at $3.99\n\n"
            "The perfect end to a perfect beach day.\n\n"
            "📍 2311 Padre Blvd, South Padre Island, TX 78597\n"
            "📞 (956) 433-5599\n"
            "Open until 10 PM\n\n"
            "#IslandCandy #SouthPadreIsland #SPI"
        ),
        'image_path': 'ad_3_homemade_icecream.png',
    },
    {
        'out': 'C:/Users/mario/custom_designs_ad_images/preview_gbp_ad5.html',
        'title': 'Custom Designs TX — GBP Ad 5 — Family Safety',
        'angle': 'family_safety',
        'color': '#1a3a5c',
        'initials': 'CD',
        'page_name': 'Custom Designs TX',
        'copy': (
            "Your family is at home right now. Do you know what's happening there? 🏠\n\n"
            "A professional camera system from Custom Designs TX gives you eyes on every corner "
            "of your property — live, from your phone, from anywhere.\n\n"
            "📱 Watch your front door, backyard, and driveway in real time\n"
            "⚡ Instant alerts the moment anything triggers\n"
            "🔒 Cameras + alarm working together — the complete system\n"
            "🛠️ Professional installation — no DIY guesswork\n\n"
            "We've protected homes across Hidalgo and Cameron County. We'll do the same for yours.\n\n"
            "📞 Free on-site consultation — we come to you.\n"
            "No obligation. No charge. Just honest answers.\n\n"
            "Call or message us: (956) 624-2463\n"
            "📍 Serving McAllen, Edinburg, Mission, Pharr & the RGV\n\n"
            "#McAllen #HomeSecurity #RGV"
        ),
        'image_path': 'ad_5_family_safety.png',
    },
]

for ad in ads:
    html = TEMPLATE.format(**ad)
    with open(ad['out'], 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ {ad['out']}")
