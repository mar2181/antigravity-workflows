"""
Deep dive on Russell Village (Edinburg) — Turquesa's prior platted product.
Pull every Russell Village lot from HCAD tax office (legal contains 'RUSSELL VILLAGE LOT').
Cross-reference with Juan's IDX listings (sold + active) by site address.
Goal: actual market lot prices for the SAME builder's same product type.
"""
import requests, re, json, time
from pathlib import Path

OUT = Path(__file__).parent
URL = 'https://actweb.acttax.com/act_webdev/hidalgo/showlist.jsp'
DETAIL = 'https://actweb.acttax.com/act_webdev/hidalgo/showdetail2.jsp'
HEADERS = {'user-agent': 'Mozilla/5.0', 'referer': 'https://actweb.acttax.com/act_webdev/hidalgo/index.jsp'}

# Russell Village owners search returned 0 because we searched by owner name
# Need to search by criteria 'RUSSELL VILLAGE' — but searchby=3 is owner. searchby=6 is address only.
# The trick: Russell Village is on N Woody Street and W Cloud 9 Lane in Edinburg
# Strategy: search every street name we know belongs to Russell Village

streets = ['N WOODY','W CLOUD 9','N REVOLUTION','W FREEDOM','W LIBERTY']
all_accts = []
for street in streets:
    print(f'searching street: {street}')
    try:
        r = requests.post(URL, data={'criteria': street, 'searchby': '6', 'submit': 'Search'},
                          headers=HEADERS, timeout=30)
        if r.status_code != 200: continue
        # Parse rows
        table_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', r.text, re.S)
        for tr in table_rows:
            m = re.search(r"showdetail2\.jsp\?can=([A-Z0-9]+)", tr)
            if not m: continue
            cells = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
            if len(cells) < 4: continue
            clean = [re.sub(r'<[^>]+>', ' ', c).strip() for c in cells]
            legal = re.sub(r'\s+', ' ', clean[3] if len(clean) > 3 else '').upper()
            if 'RUSSELL VILLAGE' in legal:
                rec = {
                    'account': m.group(1),
                    'owner_addr': re.sub(r'\s+', ' ', clean[1])[:200] if len(clean) > 1 else '',
                    'site_addr': re.sub(r'\s+', ' ', clean[2])[:200] if len(clean) > 2 else '',
                    'legal': legal[:200],
                    'street_q': street,
                }
                all_accts.append(rec)
        time.sleep(1)
    except Exception as e:
        print(f'  err {street}: {e}')

# Dedup
seen=set(); dedup=[]
for r in all_accts:
    if r['account'] not in seen:
        seen.add(r['account']); dedup.append(r)
print(f'\nUnique Russell Village accounts: {len(dedup)}')

# Now pull detail values for each
def parse_detail(html):
    out = {}
    for label in ['Land Value','Improvement Value','Gross Value']:
        pat = r'<b>\s*' + label + r'\s*:\s*</b>\s*(?:&nbsp;)?\s*\$?([\d,]+)'
        m = re.search(pat, html)
        if m: out[label.lower().replace(' ','_')] = int(m.group(1).replace(',',''))
    m = re.search(r'<b>Legal Description:</b>\s*<br>\s*([^<]+?)\s*<br>', html)
    if m: out['legal'] = m.group(1).strip()
    m = re.search(r'<b>Property Site Address:</b>\s*<br>\s*([^<]+?)\s*<br>', html)
    if m: out['site'] = m.group(1).strip()
    m = re.search(r'<h3[^>]*>\s*<b>Owner Name:</b>\s*<br>\s*([^<]+?)\s*<', html, re.S)
    if m: out['owner'] = m.group(1).strip()
    return out

print('Pulling detail for each Russell Village account...')
for r in dedup:
    try:
        det = requests.get(DETAIL, params={'can': r['account']}, headers=HEADERS, timeout=20)
        d = parse_detail(det.text)
        r['detail'] = d
    except Exception as e:
        r['detail'] = {}
    time.sleep(0.5)

# Stats
vacant = [r for r in dedup if r.get('detail',{}).get('improvement_value', 0) == 0]
improved = [r for r in dedup if r.get('detail',{}).get('improvement_value', 0) > 0]
print(f'\n=== RUSSELL VILLAGE BREAKDOWN ===')
print(f'  vacant lots (no improvement): {len(vacant)}')
print(f'  improved lots (built townhouses): {len(improved)}')

if vacant:
    vlands = [v['detail']['land_value'] for v in vacant if v['detail'].get('land_value')]
    import statistics
    print(f'  vacant land values: median=${statistics.median(vlands):,.0f} mean=${statistics.mean(vlands):,.0f} min=${min(vlands):,.0f} max=${max(vlands):,.0f}')

if improved:
    ilands = [v['detail']['land_value'] for v in improved if v['detail'].get('land_value')]
    igross = [v['detail']['gross_value'] for v in improved if v['detail'].get('gross_value')]
    import statistics
    print(f'  improved land values: median=${statistics.median(ilands):,.0f}')
    print(f'  improved gross values: median=${statistics.median(igross):,.0f}')

print('\n--- All Russell Village accounts ---')
for r in dedup:
    d = r.get('detail',{})
    print(f'  {r["account"]} {d.get("legal","?")[:30]:30} | {d.get("site","?")[:30]:30} | land=${d.get("land_value",0):>7,} impr=${d.get("improvement_value",0):>7,} owner={d.get("owner","?")[:30]}')

(OUT / 'russell_village_lots.json').write_text(json.dumps(dedup, indent=2))
print(f'\nSaved to russell_village_lots.json')

# Now match to IDX listings — need to load townhouse_comps and filter by 'Russell Village' subdivision
town = json.loads((OUT / 'townhouse_comps.json').read_text())
rv_idx = [r for r in town if 'RUSSELL VILLAGE' in (r.get('subdivision','') or '').upper()]
print(f'\n--- Russell Village IDX MLS listings: {len(rv_idx)} ---')
for r in rv_idx:
    print(f'  {(r["address"] or "")[:35]:35} {r["status"]:10} {r.get("query_status","?"):8} ${r["effective_price"] or 0:>9,} lot_sf={r["lot_sf"]} fin_sf={r["finished_sf"]} yb={r["year_built"]} date={(r["effective_date"] or "")[:10]}')

(OUT / 'russell_village_idx.json').write_text(json.dumps(rv_idx, indent=2))
