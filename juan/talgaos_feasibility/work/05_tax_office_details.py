"""
Pull tax-office detail pages for the most relevant accounts found in 04.
Detail page provides:
  - Legal description (already have)
  - Land value (CAD's tax assessment of LAND only)
  - Improvement value
  - Total value
  - Acres / sq ft (sometimes in legal)
  - Most-recent transfer (rare on this site, but worth checking)
"""
import requests, re, json, time
from pathlib import Path

OUT = Path(__file__).parent / 'tax_office'
DETAIL = 'https://actweb.acttax.com/act_webdev/hidalgo/showdetail2.jsp'
HEADERS = {'user-agent': 'Mozilla/5.0', 'referer': 'https://actweb.acttax.com/act_webdev/hidalgo/index.jsp'}

records = json.loads((Path(__file__).parent / 'tax_office_accounts.json').read_text())

# Filter to highest-value records: small townhouse-style lots, not commercial parks
keep_keys = ['LOT', 'TOWNHOM', 'PATIO HOM', 'VILLA', 'CONDO', 'UNIT', 'PH ']
skip_keys = ['IRR TR', 'BLK', 'PRIVATE ROADWAYS', 'COMMON AREA', 'PARK', 'PLAZA', 'COMMERCIAL']

filtered = []
for r in records:
    legal = r['legal'].upper()
    if any(k in legal for k in skip_keys) and 'LOT' in legal and 'AC' in legal:
        continue
    if any(k in legal for k in keep_keys) and 'LOT' in legal:
        # exclude commercial-flavored
        if 'PARK' in legal and 'TRENTON PARK' in legal: continue
        filtered.append(r)

# Dedup by account
seen = set(); dedup=[]
for r in filtered:
    if r['account'] not in seen:
        seen.add(r['account']); dedup.append(r)
print(f'Filtered tax-office records (residential-style with LOT): {len(dedup)}')

# Cap at 80 to keep this reasonable
dedup = dedup[:80]

def fetch_detail(can):
    try:
        r = requests.get(DETAIL, params={'can': can}, headers=HEADERS, timeout=30)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        return None

def parse_detail(html):
    if not html: return {}
    out = {}
    # Look for value rows (Gross Value / Land / Improvement / Tax / etc.)
    # The site uses structured tables. Common labels:
    labels = ['Improvement HS', 'Improvement NHS', 'Land HS', 'Land NHS',
              'Productivity Market', 'Productivity Use', 'Assessed Value',
              'HS Cap Loss', 'Total', 'Gross Value', 'Net Taxable',
              'Property Site Address', 'Owner Name', 'Owner Address', 'Legal Description',
              'CAD Reference Number', 'Account Number', 'Year Built', 'Acreage',
              'Acres', 'Square Footage', 'Square Feet', 'Lot Size']
    for label in labels:
        # Common pattern: <td>Label</td><td>Value</td> with various formatting
        for pat in [
            rf'<td[^>]*>\s*{re.escape(label)}\s*[:.]?\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>',
            rf'>\s*{re.escape(label)}\s*[:.]?\s*<[^>]*>\s*([^<]+?)\s*<',
            rf'<td[^>]*>{re.escape(label)}</td>[^<]*<td[^>]*>([^<]+?)</td>',
        ]:
            m = re.search(pat, html, re.S | re.I)
            if m:
                v = re.sub(r'\s+', ' ', m.group(1)).strip()
                if v and v != '&nbsp;': out[label] = v
                break
    return out

print('Fetching detail pages...')
detailed = []
for i, r in enumerate(dedup):
    html = fetch_detail(r['account'])
    parsed = parse_detail(html or '')
    r['_detail'] = parsed
    detailed.append(r)
    if i % 10 == 0:
        print(f'  {i+1}/{len(dedup)} {r["account"]} -> {list(parsed.keys())[:6]}')
    time.sleep(0.6)

(Path(__file__).parent / 'tax_office_detailed.json').write_text(json.dumps(detailed, indent=2))
print(f'\nSaved {len(detailed)} records')

# Show representative records with land value
print('\n--- Sample records with land value ---')
shown = 0
for r in detailed:
    d = r['_detail']
    land_val = d.get('Land NHS') or d.get('Land HS')
    if land_val and shown < 30:
        print(f'  [{r["query"]}] {r["account"]} | {r["legal"][:60]} | land=${land_val} site={r["site_addr"][:40]}')
        shown += 1
