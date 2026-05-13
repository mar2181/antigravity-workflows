"""
Tax-office portfolio sweep:
  - Search by owner name for known small-lot developer LLCs
  - Search by named-subdivision keywords (where they appear in legal descriptions)
This gives us off-market / non-MLS comps via developer inventory.
"""
import requests, re, time
from pathlib import Path

OUT = Path(__file__).parent / 'tax_office'
OUT.mkdir(exist_ok=True)

URL = 'https://actweb.acttax.com/act_webdev/hidalgo/showlist.jsp'
DETAIL = 'https://actweb.acttax.com/act_webdev/hidalgo/showdetail2.jsp'
HEADERS = {'user-agent': 'Mozilla/5.0', 'referer': 'https://actweb.acttax.com/act_webdev/hidalgo/index.jsp'}

# Developer LLCs and entities likely to hold small townhouse lots
DEVELOPER_QUERIES = [
    'TURQUESA CONSTRUCTION',
    'TALGAOS',
    'TRES LAGOS',
    'STONEGATE',
    'TRENTON',
    'RINCON DE LAS FUENTES',
    'GEORGETOWN PARK',
    'GARDEN PATH',
    'SHIBUI',
    'BROWNWOOD',
    'SUMMER WINDS',
    'CESAR VILLAGE',
    'QUIET VILLAGE',
    'EDINBURG MANOR',
    'RUSSELL VILLAGE',
    'VILLAS DEL RIO',
    'TOWNHOMES OF LOS ALEGRES',
    'NORTH GARDEN',
    'COVENTRY',
    'SAN MARTIN',
    'LAS BRISAS',
]

def search(criteria):
    data = {'criteria': criteria, 'searchby': '3', 'submit': 'Search'}
    try:
        r = requests.post(URL, data=data, headers=HEADERS, timeout=30, allow_redirects=True)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        print(f'  err {criteria}: {e}'); return None

def parse_list(html):
    """Extract account number, owner, address, legal description from list HTML."""
    if not html: return []
    rows = []
    # Each result row links to showdetail2.jsp?can=...
    # Find blocks with the can pattern
    cans = re.findall(r"showdetail2\.jsp\?can=([A-Z0-9]+)", html)
    cans = list(dict.fromkeys(cans))  # unique preserve order
    # Parse table rows
    table_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for tr in table_rows:
        m = re.search(r"showdetail2\.jsp\?can=([A-Z0-9]+)", tr)
        if not m: continue
        cells = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if len(cells) < 4: continue
        clean = [re.sub(r'<[^>]+>', ' ', c).strip() for c in cells]
        rows.append({
            'account': m.group(1),
            'owner_addr': re.sub(r'\s+', ' ', clean[1])[:200] if len(clean) > 1 else '',
            'site_addr': re.sub(r'\s+', ' ', clean[2])[:200] if len(clean) > 2 else '',
            'legal': re.sub(r'\s+', ' ', clean[3])[:300] if len(clean) > 3 else '',
            'cad_ref': re.sub(r'\s+', ' ', clean[4])[:50] if len(clean) > 4 else '',
        })
    return rows

all_records = []
for q in DEVELOPER_QUERIES:
    print(f'searching: {q}')
    html = search(q)
    if not html:
        time.sleep(1); continue
    (OUT / f'{q.replace(" ","_")}.html').write_text(html[:200000], encoding='utf-8')
    rows = parse_list(html)
    print(f'  -> {len(rows)} accounts')
    for r in rows:
        r['query'] = q
        all_records.append(r)
    time.sleep(1)

import json
(OUT.parent / 'tax_office_accounts.json').write_text(json.dumps(all_records, indent=2))

# Filter to townhouse/villa subdivision legal descriptions and small-lot indicators
townhouse_legal = [r for r in all_records if any(k in r['legal'].upper() for k in [
    'TOWNHOM','PATIO HOM','VILLA','COMMON','CONDO','UNIT','LOT'
])]
print(f'\n\nTOTAL accounts: {len(all_records)}')
print(f'Townhouse-style legal descriptions: {len(townhouse_legal)}')

# Show sample
print('\nSample of townhouse-style records:')
for r in townhouse_legal[:30]:
    print(f'  [{r["query"]}] {r["account"]} | {r["legal"][:90]} | site={r["site_addr"][:60]}')
