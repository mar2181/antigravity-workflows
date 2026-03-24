import sys, re, os
sys.stdout.reconfigure(encoding='utf-8')

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Preview — {title}</title>
<style>
  body{{margin:0;padding:24px;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;}}
  .lbl{{max-width:520px;margin:0 auto 12px;color:#65676b;font-size:13px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;}}
  .meta{{max-width:520px;margin:0 auto 8px;color:#65676b;font-size:12px;}}
  .card{{max-width:520px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden;}}
  .hdr{{display:flex;align-items:center;padding:12px 16px;gap:10px;}}
  .av{{width:42px;height:42px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:15px;flex-shrink:0;}}
  .pn{{font-weight:700;font-size:15px;color:#050505;line-height:1.2;}}
  .sp{{font-size:12px;color:#65676b;}}
  .body{{padding:0 16px 12px;font-size:15px;color:#050505;line-height:1.5;white-space:pre-wrap;}}
  .img img{{width:100%;display:block;}}
  .ftr{{padding:10px 16px;border-top:1px solid #e4e6eb;display:flex;gap:8px;}}
  .rx{{flex:1;text-align:center;padding:6px;color:#65676b;font-size:14px;font-weight:600;cursor:pointer;border-radius:4px;}}
  .rx:hover{{background:#f2f2f2;}}
  .bar{{max-width:520px;margin:16px auto 0;display:flex;gap:12px;}}
  .btn{{flex:1;padding:12px;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;}}
  .ok{{background:{color};color:#fff;}}
  .sk{{background:#e4e6eb;color:#050505;}}
  .msg{{display:none;max-width:520px;margin:12px auto;padding:12px 16px;background:#d4edda;color:#155724;border-radius:8px;font-weight:600;font-size:14px;}}
</style>
</head>
<body>
<div class="lbl">📋 {label}</div>
<div class="meta">📅 2026-03-15 &nbsp;|&nbsp; Angle: {angle}</div>
<div class="card">
  <div class="hdr">
    <div class="av">{initials}</div>
    <div><div class="pn">{page_name}</div><div class="sp">Sponsored · 🌐</div></div>
  </div>
  <div class="body">{copy}</div>
  <div class="img"><img src="{image_path}"></div>
  <div class="ftr">
    <div class="rx">👍 Like</div>
    <div class="rx">💬 Comment</div>
    <div class="rx">↗️ Share</div>
  </div>
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

def extract_body(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'<div class="body">(.*?)</div>', content, re.DOTALL)
    if match:
        text = re.sub(r'<br\s*/?>', '\n', match.group(1))
        text = re.sub(r'<[^>]+>', '', text).strip()
        return text
    return None

def extract_inline_body(content, ad_num):
    pattern = rf'AD #{ad_num}\s*[^\<]*</div>.*?line-height:1\.6;">(.*?)</div>'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        text = re.sub(r'<br\s*/?>', '\n', match.group(1))
        text = re.sub(r'<[^>]+>', '', text).strip()
        text = text.replace('&amp;', '&')
        return text
    return None

ads = []

# ---- Sugar Shack Ad 4 — Bulk Candy Budget ----
ss_copy = extract_body('C:/Users/mario/sugar_shack_ad_images/preview_ad4.html')
ads.append({
    'out': 'C:/Users/mario/sugar_shack_ad_images/preview_march15_ad4.html',
    'title': 'Sugar Shack — Ad 4 — Bulk Candy Budget',
    'label': 'Ad #4 Preview — Bulk Candy Budget | Sugar Shack',
    'angle': 'bulk_candy_budget',
    'color': '#e91e63',
    'initials': 'SS',
    'page_name': 'The Sugar Shack',
    'copy': ss_copy,
    'image_path': 'file:///C:/Users/mario/sugar_shack_ad_images/ad_4_bulk_candy_budget.png',
})

# ---- Island Arcade Ad 4 — Family Showdown ----
with open('C:/Users/mario/island_arcade_ad_images/preview_all11.html', encoding='utf-8') as f:
    ia_content = f.read()
ia_copy = extract_inline_body(ia_content, 4)
ads.append({
    'out': 'C:/Users/mario/island_arcade_ad_images/preview_march15_ad4.html',
    'title': 'Island Arcade — Ad 4 — Family Showdown',
    'label': 'Ad #4 Preview — Family Showdown | Island Arcade',
    'angle': 'family_showdown',
    'color': '#ff6b35',
    'initials': 'IA',
    'page_name': 'Island Arcade South Padre Island',
    'copy': ia_copy,
    'image_path': 'file:///C:/Users/mario/island_arcade_ad_images/ad_4_family_showdown.png',
})

# ---- Island Candy Ad 2 — Sweet Reward ----
with open('C:/Users/mario/island_candy_ad_images/preview_all12.html', encoding='utf-8') as f:
    ic_content = f.read()
ic_copy = extract_inline_body(ic_content, 2)
ads.append({
    'out': 'C:/Users/mario/island_candy_ad_images/preview_march15_ad2.html',
    'title': 'Island Candy — Ad 2 — Sweet Reward',
    'label': 'Ad #2 Preview — Sweet Reward | Island Candy',
    'angle': 'sweet_reward',
    'color': '#9c27b0',
    'initials': 'IC',
    'page_name': 'Island Candy',
    'copy': ic_copy,
    'image_path': 'file:///C:/Users/mario/island_candy_ad_images/ad_2_sweet_reward.png',
})

# ---- SPI Fun Rentals Ad 1 — Golf Cart Spring Break ----
spi_copy = extract_body('C:/Users/mario/spi_fun_rentals_ad_images/preview_spi_ad1.html')
ads.append({
    'out': 'C:/Users/mario/spi_fun_rentals_ad_images/preview_march15_spi_ad1.html',
    'title': 'SPI Fun Rentals — Ad 1 — Golf Cart Spring Break',
    'label': 'Ad #1 Preview — Golf Cart Spring Break | SPI Fun Rentals',
    'angle': 'golf_cart_spring_break',
    'color': '#f97316',
    'initials': 'SF',
    'page_name': 'SPI Fun Rentals',
    'copy': spi_copy,
    'image_path': 'file:///C:/Users/mario/.gemini/antigravity/tools/execution/spi_fun_rentals/assets/images/Yehuda%206%20Seater%20Golf%20Cart%20wNumber.jpg',
})

for ad in ads:
    html = TEMPLATE.format(**ad)
    with open(ad['out'], 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ {ad['out']}")
