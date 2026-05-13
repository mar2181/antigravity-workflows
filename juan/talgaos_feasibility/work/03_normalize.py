"""
Normalize the detailed IDX data into clean comp records with:
  - lot_sf (true, from detail page)
  - sale_price (from sold_price OR listingPrice if active)
  - sale_date (from sold_date OR closed_date OR list_date OR dateAdded)
  - status (sold/active/pending)
  - source_url

Then split into:
  pure_land_comps.csv  — Bucket A pure-land sales (≤5,000 SF)
  townhouse_comps.csv  — Bucket B finished-townhouse sales (for imputed-land calc)
"""
import json, re, csv
from pathlib import Path
from datetime import datetime, timedelta

OUT = Path(__file__).parent
A = json.loads((OUT / 'detailed_A_land.json').read_text())
B = json.loads((OUT / 'detailed_B_townhouse.json').read_text())

def to_int(x):
    if x is None: return None
    s = str(x).replace(',','').replace('$','').replace(' SqFt','').replace('sqft','').strip()
    try: return int(float(s))
    except: return None

def to_date(s):
    if not s: return None
    s = str(s).strip()
    for fmt in ['%m/%d/%Y','%Y-%m-%d','%Y-%m-%dT%H:%M:%S+00:00','%Y-%m-%dT%H:%M:%S%z']:
        try: return datetime.strptime(s.split('+')[0].split('T')[0] if 'T' in s else s, fmt.split('T')[0] if 'T' in s else fmt)
        except: continue
    try: return datetime.fromisoformat(s.replace('Z',''))
    except: return None

def normalize(p, kind):
    d = p.get('_detail', {}) or {}
    rec = {
        'kind': kind,
        'address': p.get('address'),
        'city': p.get('cityName'),
        'state': p.get('stateAbrv'),
        'zip': p.get('_query_zip'),
        'subdivision': p.get('subdivision') or d.get('subdivision') or '',
        'prop_type': d.get('propType') or '',
        'prop_subtype': d.get('propSubType') or '',
        'year_built': to_int(d.get('yearBuilt')),
        'acres': p.get('acres'),
        'lot_sf': to_int(d.get('lotSizeSquareFeet')),
        'finished_sf': to_int(p.get('sqFt')),
        'beds': p.get('bedrooms'),
        'baths': p.get('totalBaths'),
        'list_price': to_int(p.get('listingPrice')),
        'sold_price': to_int(d.get('sold_price') or d.get('closed_price') or d.get('close_price')),
        'sold_date': d.get('sold_date') or d.get('closed_date') or d.get('close_date'),
        'list_date': d.get('list_date') or d.get('listing_date'),
        'date_added': p.get('dateAdded'),
        'status': p.get('propStatus') or '',
        'query_status': p.get('_query_status'),
        'listing_id': p.get('listingID'),
        'source_url': p.get('detailsURL'),
        'source': 'IDX-juanjoseelizondo',
    }
    # If lot_sf missing but acres present, compute
    if not rec['lot_sf'] and rec['acres']:
        try: rec['lot_sf'] = int(round(float(rec['acres']) * 43560))
        except: pass
    # Choose effective sale price + date
    rec['effective_price'] = rec['sold_price'] or rec['list_price']
    rec['effective_date'] = rec['sold_date'] or rec['list_date'] or (rec['date_added'][:10] if rec['date_added'] else None)
    # Compute price_per_sf
    if rec['effective_price'] and rec['lot_sf'] and rec['lot_sf'] > 0:
        rec['price_per_lot_sf'] = round(rec['effective_price'] / rec['lot_sf'], 2)
    else:
        rec['price_per_lot_sf'] = None
    return rec

land = [normalize(p, 'land') for p in A]
town = [normalize(p, 'townhouse') for p in B]

# Filter pure land to <=5,000 SF, with valid price
land_clean = [r for r in land if r['lot_sf'] and 1000 <= r['lot_sf'] <= 5500 and r['effective_price']]
# Filter townhouses: must have lot_sf, finished_sf, price, prop_subtype hint of attached/townhouse/condo
TOWNHOUSE_HINTS = ['TOWNHOUSE','TOWN HOUSE','PATIO','VILLA','ATTACH','CONDO','MULTI','DUPLEX','TRIPLEX','FOURPLEX','PLEX','TWO ON LOT']
town_clean = []
for r in town:
    sub = (r['subtype_hit'] if False else r['prop_subtype'] + ' ' + r['subdivision']).upper() if r.get('prop_subtype') is not None else ''
    s_join = (r.get('prop_subtype','') + ' ' + r.get('subdivision','')).upper()
    is_townhouse_like = any(k in s_join for k in TOWNHOUSE_HINTS)
    has_small_lot = r['lot_sf'] and 1500 <= r['lot_sf'] <= 6500
    if is_townhouse_like and has_small_lot and r['effective_price']:
        town_clean.append(r)

print(f'Pure land cleaned: {len(land_clean)} (of {len(land)})')
print(f'Townhouse cleaned: {len(town_clean)} (of {len(town)})')

# Save CSVs
def write_csv(path, rows):
    if not rows:
        Path(path).write_text('')
        return
    keys = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows: w.writerow(r)

write_csv(OUT / 'pure_land_comps.csv', land_clean)
write_csv(OUT / 'townhouse_comps.csv', town_clean)
(OUT / 'pure_land_comps.json').write_text(json.dumps(land_clean, indent=2))
(OUT / 'townhouse_comps.json').write_text(json.dumps(town_clean, indent=2))

# Quick summary of lot-size distribution in pure land
sizes = [r['lot_sf'] for r in land_clean]
prices = [r['effective_price'] for r in land_clean]
ppsf = [r['price_per_lot_sf'] for r in land_clean if r['price_per_lot_sf']]
print('\nPure-land lot SF distribution:')
sizes.sort()
import statistics
if sizes:
    print(f'  n={len(sizes)} min={sizes[0]} p25={sizes[len(sizes)//4]} median={statistics.median(sizes):.0f} p75={sizes[3*len(sizes)//4]} max={sizes[-1]}')
    print(f'  prices median=${statistics.median(prices):,.0f} ppsf_median=${statistics.median(ppsf):.2f}/SF')
print('\nTownhouse cleaned subdivisions:')
from collections import Counter
subs = Counter(r['subdivision'] for r in town_clean)
for s, c in subs.most_common(20):
    print(f'  {c}x {s}')
