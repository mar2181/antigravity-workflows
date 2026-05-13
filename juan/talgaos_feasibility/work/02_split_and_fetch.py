"""
Split candidates into two priority buckets and fetch detail pages.
Bucket A: Pure land (pt=3) with acres 0.04-0.12 (~1,750-5,200 SF)  [Tier A/B candidates]
Bucket B: Residential townhouse/multi-family with named subdivision OR low acres [Tier D imputed]
Detail pages give us: lot SF, sold date, prop subtype, year built, finished SF, sold price.
"""
import json, re, time, requests
from pathlib import Path

OUT = Path(__file__).parent
candidates = json.loads((OUT / 'idx_candidates.json').read_text())
HEADERS = {'user-agent': 'Mozilla/5.0', 'referer': 'https://juanjoseelizondo.com/'}

# Bucket A: small pure land
bucket_A = []
# Bucket B: residential townhouse/named-sub
bucket_B = []
for p in candidates:
    pt = p.get('_query_pt', '')
    try: ac = float(p.get('acres') or 0)
    except: ac = 0
    if pt == 'pt3':
        if 0.03 < ac <= 0.20:
            bucket_A.append(p)
    elif pt == 'pt1':
        # Only townhouse/multi-fam style - filter by subdivision keyword OR very small
        sub = (p.get('subdivision') or '').upper()
        township_keys = ['TOWNHOM','PATIO HOM','VILLA','TRES LAGOS','STONEGATE','TRENTON','LAS BRISAS','SHARYLAND','COVENTRY','ALHAMBRA','CONDOMIN']
        named_match = any(n in sub for n in township_keys)
        if named_match or 0 < ac <= 0.10:
            bucket_B.append(p)

print(f'Bucket A (small land): {len(bucket_A)}')
print(f'Bucket B (named-sub residential): {len(bucket_B)}')

def fetch_detail(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=45)
        if r.status_code != 200: return None
        return r.text
    except Exception as e:
        return None

def parse_detail(html):
    """Extract relevant fields from IDX detail page."""
    if not html: return {}
    out = {}
    fields = {
        'lotSizeArea':       r'id="IDX-field-lotSizeArea"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'lotSizeSquareFeet': r'id="IDX-field-lotSizeSquareFeet"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'lotSizeUnits':      r'id="IDX-field-lotSizeUnits"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'subdivision':       r'id="IDX-field-subdivision"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'yearBuilt':         r'id="IDX-field-yearBuilt"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'propType':          r'id="IDX-field-propType"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'propSubType':       r'id="IDX-field-propSubType"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
        'newConstructionYN': r'id="IDX-field-newConstructionYN"[^>]*>.*?IDX-text">\s*([^<]+?)\s*</span>',
    }
    for k, pat in fields.items():
        m = re.search(pat, html, re.S)
        if m: out[k] = m.group(1).strip()

    # Sold Date / Closed Date / List Date
    for label in ['Sold Date', 'Closed Date', 'List Date', 'Listing Date', 'Close Date']:
        m = re.search(rf'>{re.escape(label)}</span>\s*<span[^>]*>\s*([^<]+?)\s*</span>', html, re.S)
        if m: out[label.replace(' ','_').lower()] = m.group(1).strip()

    # Sold Price
    for label in ['Sold Price', 'Closed Price', 'Close Price']:
        m = re.search(rf'>{re.escape(label)}</span>\s*<span[^>]*>\s*([^<]+?)\s*</span>', html, re.S)
        if m: out[label.replace(' ','_').lower()] = m.group(1).strip()

    # Bedrooms / Baths / Total SF (finished)
    for label in ['Bedrooms', 'Total Baths', 'Living Area', 'Above Grade Finished Area', 'Building Area Total']:
        m = re.search(rf'>{re.escape(label)}</span>\s*<span[^>]*>\s*([^<]+?)\s*</span>', html, re.S)
        if m: out[label.replace(' ','_').lower()] = m.group(1).strip()

    return out

# Save buckets
(OUT / 'bucket_A_land.json').write_text(json.dumps(bucket_A, indent=2))
(OUT / 'bucket_B_residential.json').write_text(json.dumps(bucket_B, indent=2))

# Fetch detail for ALL of bucket A (small set)
# Fetch detail for SAMPLED bucket B — only those with low acres or townhouse/villa keyword
print('\n--- Fetching detail for bucket A (all, pure land) ---')
detailed_A = []
for i, p in enumerate(bucket_A):
    url = p.get('detailsURL', '')
    if not url: continue
    html = fetch_detail(url)
    parsed = parse_detail(html or '')
    p['_detail'] = parsed
    detailed_A.append(p)
    if i % 20 == 0: print(f'  A {i+1}/{len(bucket_A)} {p.get("address","?")[:40]}')
    time.sleep(0.4)
(OUT / 'detailed_A_land.json').write_text(json.dumps(detailed_A, indent=2))

# Bucket B: filter to most likely townhouse comps then detail-fetch
likely_townhouse = []
for p in bucket_B:
    sub = (p.get('subdivision') or '').upper()
    try: ac = float(p.get('acres') or 0)
    except: ac = 0
    keys = ['TOWNHOM','PATIO HOM','VILLA','CONDOMIN','TRES LAGOS','STONEGATE','TRENTON','LAS BRISAS','COVENTRY','ALHAMBRA']
    if any(k in sub for k in keys) or 0 < ac <= 0.08:
        likely_townhouse.append(p)
print(f'\n--- Fetching detail for bucket B (likely townhouse): {len(likely_townhouse)} ---')
detailed_B = []
for i, p in enumerate(likely_townhouse):
    url = p.get('detailsURL', '')
    if not url: continue
    html = fetch_detail(url)
    parsed = parse_detail(html or '')
    p['_detail'] = parsed
    detailed_B.append(p)
    if i % 20 == 0: print(f'  B {i+1}/{len(likely_townhouse)} {p.get("address","?")[:40]} | {p.get("subdivision","?")[:30]}')
    time.sleep(0.4)
(OUT / 'detailed_B_townhouse.json').write_text(json.dumps(detailed_B, indent=2))
print(f'\nDone. detailed_A={len(detailed_A)}, detailed_B={len(detailed_B)}')
