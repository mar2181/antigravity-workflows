import sqlite3, json
c = sqlite3.connect('/home/mario/crexiscrapperloopnet/warehouse/comps.db')
cur = c.cursor()
cur.execute('SELECT canonical_address, city, acreage, sqft, current_price, listing_status, property_type, source_primary FROM properties WHERE acreage IS NOT NULL AND acreage<5 AND current_price IS NOT NULL ORDER BY acreage')
rows = cur.fetchall()
print(f'total <5ac: {len(rows)}')
small = []
for r in rows:
    per_acre = r[4]/r[2] if r[2] else 0
    per_sf = r[4]/r[3] if r[3] else 0
    print(f'  {(r[0] or "")[:38]:38} {(r[1] or "")[:14]:14} {r[2]:.3f}ac {r[3] or 0:>6}sf  ${r[4] or 0:>9,}  ${per_acre:>10,.0f}/ac  ${per_sf:>5.2f}/sf  {r[5]:8} {(r[6] or "")[:14]:14} {r[7]}')
    small.append({'address':r[0],'city':r[1],'acres':r[2],'sqft':r[3],'price':r[4],'per_acre':round(per_acre,0),'per_sf':round(per_sf,2),'status':r[5],'type':r[6],'source':r[7]})
with open('/mnt/c/Users/mario/.gemini/antigravity/tools/execution/juan/talgaos_feasibility/work/crexi_under_5ac.json','w') as f:
    json.dump(small, f, indent=2)
print(f'\nsaved {len(small)} records')
