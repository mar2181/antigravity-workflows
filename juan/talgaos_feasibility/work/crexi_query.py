import sqlite3, json
c = sqlite3.connect('/home/mario/crexiscrapperloopnet/warehouse/comps.db')
cur = c.cursor()

print('--- Hidalgo county properties by city ---')
cur.execute("SELECT city, COUNT(*) FROM properties WHERE city IS NOT NULL AND zip IN ('78539','78541','78542','78504','78501','78503','78572','78573','78574','78577','78589','78537','78516') GROUP BY city ORDER BY 2 DESC")
for r in cur.fetchall(): print(' ', r)

print('\n--- Small lots <=0.5 acre with full data ---')
cur.execute("""SELECT canonical_address, city, zip, acreage, sqft, current_price, listing_status, property_type, source_primary, first_seen_at, last_seen_at FROM properties
WHERE acreage IS NOT NULL AND acreage<=0.5 AND current_price IS NOT NULL
AND zip IN ('78539','78541','78542','78504','78501','78503','78572','78573','78574','78577','78589','78537','78516')
ORDER BY acreage""")
small = []
for r in cur.fetchall():
    rec = {
        'address': r[0], 'city': r[1], 'zip': r[2], 'acres': r[3], 'sqft': r[4],
        'price': r[5], 'status': r[6], 'type': r[7], 'source': r[8],
        'first_seen': r[9], 'last_seen': r[10],
    }
    small.append(rec)
    per_ac = r[5]/r[3] if r[3] else 0
    per_sf = r[5]/r[4] if r[4] else 0
    print(f'  {(r[0] or "")[:38]:38} {r[1]:10} {r[2]:5} {r[3]:.3f}ac {r[4] or 0:>7}sf ${r[5] or 0:>9,} {r[6]:8} {(r[7] or "")[:15]:15} ${per_ac:>9,.0f}/ac ${per_sf:>5.2f}/sf  src={r[8]}')

with open('/mnt/c/Users/mario/.gemini/antigravity/tools/execution/juan/talgaos_feasibility/work/crexi_small_lots.json', 'w') as f:
    json.dump(small, f, indent=2, default=str)

print('\n--- All RGV <5ac aggregate ---')
cur.execute("SELECT COUNT(*), AVG(price_per_acre), MIN(acreage), MAX(acreage), MIN(price_per_acre), MAX(price_per_acre) FROM properties WHERE acreage<5 AND zip IN ('78539','78541','78542','78504','78501','78503','78572','78573','78574','78577','78589','78537','78516')")
print(cur.fetchone())

# Also pull all properties under 5 ac for tier-broader sanity
print('\n--- All RGV <5ac with $/ac (sorted by $/ac) ---')
cur.execute("""SELECT canonical_address, city, acreage, current_price, ROUND(current_price/acreage,0) per_acre, listing_status, source_primary FROM properties
WHERE acreage<5 AND current_price IS NOT NULL AND acreage IS NOT NULL
AND zip IN ('78539','78541','78542','78504','78501','78503','78572','78573','78574','78577','78589','78537','78516')
ORDER BY 5""")
all_small = []
for r in cur.fetchall():
    all_small.append({'address':r[0],'city':r[1],'acres':r[2],'price':r[3],'per_acre':r[4],'status':r[5],'source':r[6]})
with open('/mnt/c/Users/mario/.gemini/antigravity/tools/execution/juan/talgaos_feasibility/work/crexi_all_under_5ac.json', 'w') as f:
    json.dump(all_small, f, indent=2, default=str)
print(f'  saved {len(all_small)} records')
