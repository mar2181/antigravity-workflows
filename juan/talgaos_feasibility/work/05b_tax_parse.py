"""
Re-parse the already-fetched tax office detail HTMLs (saved in tax_office_detailed.json was bare;
need to re-fetch since first version didn't store HTMLs). Pull from /tax_office/ HTML files where saved,
or re-fetch with corrected parser.
"""
import requests, re, json, time
from pathlib import Path

OUT = Path(__file__).parent
DETAIL = 'https://actweb.acttax.com/act_webdev/hidalgo/showdetail2.jsp'
HEADERS = {'user-agent': 'Mozilla/5.0', 'referer': 'https://actweb.acttax.com/act_webdev/hidalgo/index.jsp'}

records = json.loads((OUT / 'tax_office_accounts.json').read_text())

# Filter same as 05
keep_keys = ['LOT', 'TOWNHOM', 'PATIO HOM', 'VILLA', 'CONDO', 'UNIT', 'PH ']
skip_keys_legal = [' AC', ' AC ']  # We want SMALL lots, not multi-acre tracts
# We exclude any account whose legal mentions multi-AC tract OR commercial plaza
filtered = []
for r in records:
    legal = r['legal'].upper()
    if 'AC' in legal and re.search(r'\d+\.\d+\s*AC', legal):
        # check acreage
        m = re.search(r'(\d+\.\d+)\s*AC', legal)
        if m and float(m.group(1)) > 0.20: continue  # >0.20 ac = >8,712 SF, not townhouse-pad
    if any(k in legal for k in keep_keys) and 'LOT' in legal:
        if 'COMMON AREA' in legal or 'PRIVATE ROADWAYS' in legal: continue
        filtered.append(r)

# Dedup
seen = set(); dedup=[]
for r in filtered:
    if r['account'] not in seen:
        seen.add(r['account']); dedup.append(r)
print(f'Filtered candidates: {len(dedup)}')

def fetch_detail(can):
    try:
        r = requests.get(DETAIL, params={'can': can}, headers=HEADERS, timeout=30)
        return r.text if r.status_code == 200 else None
    except: return None

def parse(html):
    if not html: return {}
    out = {}
    for label in ['Gross Value', 'Land Value', 'Improvement Value', 'Capped Value', 'Agricultural Value', 'Net Taxable']:
        m = re.search(rf'<b>\s*{re.escape(label)}\s*:\s*</b>\s*(?:&nbsp;)?\s*\$?([\d,]+)', html)
        if m: out[label.lower().replace(' ','_')] = int(m.group(1).replace(',',''))
    # Legal description (full)
    m = re.search(r'<b>Legal Description:</b>\s*<br>\s*([^<]+?)\s*<br>', html)
    if m: out['legal_full'] = m.group(1).strip()
    # Site address
    m = re.search(r'<b>Property Site Address:</b>\s*<br>\s*([^<]+?)\s*<br>', html)
    if m: out['site_address'] = m.group(1).strip()
    # Owner address
    m = re.search(r'<b>Owner Address:</b>\s*<br>(.*?)</h3>', html, re.S)
    if m: out['owner_address'] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', m.group(1))).strip()
    # Owner name
    m = re.search(r'<h3[^>]*>\s*<b>Owner Name:</b>\s*<br>\s*([^<]+?)\s*<', html, re.S)
    if m: out['owner_name'] = m.group(1).strip()
    # Tax levy
    m = re.search(r'<b>Current Tax Levy:\s*(?:&nbsp;)?\s*</b>\s*\$?([\d,.]+)', html)
    if m: out['tax_levy'] = float(m.group(1).replace(',',''))
    return out

# Cap at 100
detailed = []
for i, r in enumerate(dedup[:100]):
    html = fetch_detail(r['account'])
    p = parse(html or '')
    r['_detail'] = p
    detailed.append(r)
    if i % 20 == 0:
        print(f'  {i+1}/{min(100,len(dedup))} {r["account"]} | land=${p.get("land_value", "?")}')
    time.sleep(0.5)

(OUT / 'tax_office_detailed.json').write_text(json.dumps(detailed, indent=2))

# Compute per-lot land values for residential townhouse legals
print('\n--- Tax-office land values for townhouse-style records ---')
print(f'{"can":18} {"legal":50} {"land_val":>10} {"impr_val":>10} {"site":40}')
shown = 0
for r in detailed:
    d = r['_detail']
    if d.get('land_value'):
        print(f'{r["account"]:18} {r["legal"][:50]:50} ${d["land_value"]:>9,} ${d.get("improvement_value", 0):>9,} {r["site_addr"][:40]}')
        shown += 1
print(f'\n{shown} records with land_value\n')

# Median + p25/p75 of land value for these records
import statistics
vals = [r['_detail']['land_value'] for r in detailed if r['_detail'].get('land_value')]
if vals:
    print(f'Land value distribution (CAD-assessed): n={len(vals)}')
    print(f'  median=${statistics.median(vals):,.0f}')
    print(f'  p25=${sorted(vals)[len(vals)//4]:,.0f} p75=${sorted(vals)[3*len(vals)//4]:,.0f}')
    print(f'  mean=${statistics.mean(vals):,.0f}')
