"""
Pull IDX comps for Talgaos feasibility study.
Goals:
  - Pure small-lot land sales (pt=3, acres <=0.10) — Tier A/B candidates
  - Townhouse / multi-family residential in named subdivisions (pt=1) — Tier D imputed land
  - Expand to neighboring cities (Mission, Pharr, San Juan, Donna)
Output: idx_raw.json with everything pulled, idx_candidates.json with filtered set.
"""
import requests, json, time
from pathlib import Path

OUT = Path(__file__).parent
URL = 'https://juanjoseelizondo.idxbroker.com/idx/api/widgets/mapsearch/results'
HEADERS = {
    'referer': 'https://juanjoseelizondo.com/',
    'accept': 'application/json, text/plain, */*',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/145.0.0.0',
}

# 5 primary ZIPs + 4 neighboring-city expansion ZIPs
# Edinburg: 78539, 78541, 78542
# McAllen: 78504, 78501, 78503, 78505
# Mission: 78572, 78573, 78574
# Pharr: 78577
# San Juan: 78589
# Donna: 78537
# Alamo: 78516
ZIPS_PRIMARY = ['78539', '78541', '78542', '78504', '78501']
ZIPS_EXPANSION = ['78572', '78573', '78574', '78577', '78589', '78537', '78503', '78516']

# pt=1 Residential (homes/townhouses), pt=3 Land
PROP_TYPES = ['1', '3']
STATUSES = ['sold', 'active', 'pending']

def fetch(zc, status, pt, srt='newest'):
    params = {
        'idxID': 'd337', 'ccz': 'zipcode', 'coID': 'd337',
        'statusCategory': status, 'zipcode': zc, 'pt': pt, 'srt': srt,
    }
    try:
        r = requests.get(URL, params=params, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return []
        d = r.json()
        return d.get('properties', []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
    except Exception as e:
        print(f'  ERR {zc} {status} pt={pt}: {e}')
        return []

def main():
    raw = {}  # key: f'{zc}_{status}_{pt}' -> list
    all_zips = ZIPS_PRIMARY + ZIPS_EXPANSION
    total = 0
    for zc in all_zips:
        for status in STATUSES:
            for pt in PROP_TYPES:
                key = f'{zc}_{status}_pt{pt}'
                # Sort variants to maximize coverage despite 50-cap
                seen = {}
                for srt in ['newest', 'oldest', 'pricelo', 'pricehi']:
                    lst = fetch(zc, status, pt, srt=srt)
                    for p in lst:
                        lid = p.get('listingID')
                        if lid: seen[lid] = p
                    time.sleep(0.4)
                raw[key] = list(seen.values())
                total += len(raw[key])
                print(f'  {key}: {len(raw[key])} unique')
    (OUT / 'idx_raw.json').write_text(json.dumps(raw, indent=2))
    print(f'TOTAL unique listings collected: {total} (with duplicates across keys)')

    # Filter candidates
    # Land (pt=3): keep all (small lot land is the goal regardless of size for context)
    # Residential (pt=1): keep townhouse / multi-family / patio home subtypes if hint in subdivision or low acres
    candidates = []
    NAMED_SUBS = [
        'TRES LAGOS', 'STONEGATE', 'TRENTON', 'VILLA DEL SOL', 'LAS BRISAS',
        'SHARYLAND', 'SAN JUAN ESTATES', 'ALTA VISTA', 'LA TIERRA',
        'COVENTRY', 'TOWNHOMES', 'TOWNHOME', 'PATIO HOMES', 'VILLA',
        'CORNERSTONE', 'EDINBURG ORIGINAL TOWNSITE', 'ALHAMBRA',
        'HACIENDA PLAZA', 'ESTATE',
    ]
    for key, lst in raw.items():
        zc, status, pt = key.split('_')[0], key.split('_')[1], key.split('_')[2]
        for p in lst:
            try: ac = float(p.get('acres') or 0)
            except: ac = 0
            sub = (p.get('subdivision') or '').upper()
            named_match = any(n in sub for n in NAMED_SUBS)
            small_lot = 0 < ac <= 0.12  # ~5,200 SF
            if pt == 'pt3' and ac > 0 and ac <= 0.20:  # all small land up to 8,712 SF
                p['_query_zip'] = zc; p['_query_status'] = status; p['_query_pt'] = pt
                candidates.append(p)
            elif pt == 'pt1' and (small_lot or named_match):
                p['_query_zip'] = zc; p['_query_status'] = status; p['_query_pt'] = pt
                candidates.append(p)
    # Dedup by listingID
    seen = {}
    for p in candidates:
        lid = p.get('listingID')
        if lid and lid not in seen:
            seen[lid] = p
    cands = list(seen.values())
    (OUT / 'idx_candidates.json').write_text(json.dumps(cands, indent=2))
    print(f'CANDIDATES (small-lot land or townhouse/named-sub residential): {len(cands)}')

if __name__ == '__main__':
    main()
