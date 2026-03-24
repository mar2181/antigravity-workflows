import sys, re, os, json
sys.stdout.reconfigure(encoding='utf-8')

OWNER_ID = '33762f2f-deec-4804-b746-de0cdf08c0ce'
CLIENTS = {
    'sugar_shack': 'fb6f5c22-06d1-43c0-829a-08f6feb5b206',
    'spi_fun_rentals': 'f8693268-6abf-4401-8b2e-3795e326252b',
    'island_arcade': '40ec9f76-abd3-4a68-a23a-13e8a2c90755',
    'island_candy': 'd865037b-2552-4024-9db3-10e61e1419b4',
}

def e(s):
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"

def extract_hashtags(text):
    tags = re.findall(r'#\w+', text)
    return ' '.join(tags[:3]) if tags else None

def extract_cta(text):
    for cta in ['Get Directions', 'Book Now', 'DM me', 'Walk in', 'Come in', 'Stop by', 'Come find us', 'Find us', 'Call us', 'Visit us', 'FIND US', 'Reserve']:
        if cta.lower() in text.lower():
            return cta
    return 'Come visit us'

def first_line(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines[0][:120] if lines else 'Ad'

# -------- Sugar Shack --------
ss_manifest = json.load(open('C:/Users/mario/sugar_shack_ad_images/fal_generation_manifest.json', encoding='utf-8'))
ss_fal = {item['name']: {'fal_url': item.get('url'), 'size_mb': item.get('size_mb')} for item in ss_manifest}

ss_names = ['road_trip_fuel', 'souvenir_play', 'sweet_memories', 'bulk_candy_budget', 'cool_down_beach',
            'kids_choice', 'spring_break_fuel', 'local_favorite', 'last_stop_home', 'candy_world']
ss_ads = []
for i in range(1, 11):
    fp = f'C:/Users/mario/sugar_shack_ad_images/preview_ad{i}.html'
    if not os.path.exists(fp):
        continue
    with open(fp, encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'<div class="body">(.*?)</div>', content, re.DOTALL)
    angle_m = re.search(r'Angle:\s*([a-z_]+)', content)
    if not match:
        continue
    text = re.sub(r'<br\s*/?>', '\n', match.group(1))
    text = re.sub(r'<[^>]+>', '', text).strip()
    name = ss_names[i - 1]
    fal_info = ss_fal.get(name, {})
    ss_ads.append({
        'name': f'Sugar Shack — {name.replace("_", " ").title()}',
        'client_id': CLIENTS['sugar_shack'],
        'fal_url': fal_info.get('fal_url'),
        'size_mb': fal_info.get('size_mb'),
        'copy_body': text,
        'copy_headline': first_line(text),
        'copy_cta': extract_cta(text),
        'copy_hashtags': extract_hashtags(text),
        'ad_angle': angle_m.group(1) if angle_m else name,
        'status': 'approved',
    })

# march14 posts
march14 = json.load(open('C:/Users/mario/.gemini/antigravity/tools/execution/march14_posts_manifest.json', encoding='utf-8'))
m14 = {item['key']: item for item in march14}

def add_march14(key, client_key, label):
    item = m14.get(key)
    if not item:
        return None
    copy = item['copy']
    return {
        'name': f'{label} — Spring Break March 14',
        'client_id': CLIENTS[client_key],
        'fal_url': None,
        'size_mb': None,
        'copy_body': copy,
        'copy_headline': first_line(copy),
        'copy_cta': extract_cta(copy),
        'copy_hashtags': extract_hashtags(copy),
        'ad_angle': 'spring_break',
        'status': 'approved',
    }

ss_ads.append(add_march14('sugar_shack', 'sugar_shack', 'Sugar Shack'))

# -------- Island Arcade --------
ia_fp = 'C:/Users/mario/island_arcade_ad_images/preview_all11.html'
with open(ia_fp, encoding='utf-8') as f:
    ia_content = f.read()
ia_fp2 = 'C:/Users/mario/island_arcade_ad_images/preview_all12.html'
with open(ia_fp2, encoding='utf-8') as f:
    ia_content2 = f.read()

ia_pattern = r'AD #(\d+)\s*[^\<]*</div>.*?line-height:1\.6;">(.*?)</div>'
ia_matches = re.findall(ia_pattern, ia_content, re.DOTALL)
ia_matches2 = re.findall(ia_pattern, ia_content2, re.DOTALL)

ia_by_num = {}
for num, body in ia_matches + ia_matches2:
    if num not in ia_by_num:
        text = re.sub(r'<br\s*/?>', '\n', body)
        text = re.sub(r'<[^>]+>', '', text).strip()
        text = text.replace('&amp;', '&')
        ia_by_num[num] = text

ia_manifest = json.load(open('C:/Users/mario/island_arcade_ad_images/fal_generation_manifest.json', encoding='utf-8'))
ia_fal = {item['name']: item.get('size_mb') for item in ia_manifest}
ia_mnames = ['island_arrival', 'beat_high_score', 'vr_shock_awe', 'family_showdown', 'late_night_legends',
             'prize_haul', 'sweet_play_combo', 'retro_nostalgia', 'spring_break_alternative',
             'sunday_winddown', 'worlds_largest_pacman', 'rainy_day_hero']
ia_angles = ['island_arrival', 'beat_high_score', 'vr_shock_awe', 'family_showdown', 'late_night_legends',
             'prize_haul', 'sweet_play_combo', 'retro_nostalgia', 'spring_break_alternative',
             'sunday_winddown', 'worlds_largest_pacman', 'rainy_day_hero']

ia_ads = []
for num in sorted(ia_by_num.keys(), key=int):
    idx = int(num) - 1
    mname = ia_mnames[idx] if idx < len(ia_mnames) else None
    angle = ia_angles[idx] if idx < len(ia_angles) else f'ad_{num}'
    size_mb = ia_fal.get(mname) if mname else None
    copy = ia_by_num[num]
    ia_ads.append({
        'name': f'Island Arcade — Ad {num} {mname.replace("_", " ").title() if mname else ""}',
        'client_id': CLIENTS['island_arcade'],
        'fal_url': None,
        'size_mb': size_mb,
        'copy_body': copy,
        'copy_headline': first_line(copy),
        'copy_cta': extract_cta(copy),
        'copy_hashtags': extract_hashtags(copy),
        'ad_angle': angle,
        'status': 'approved',
    })

ia_ads.append(add_march14('island_arcade', 'island_arcade', 'Island Arcade'))

# -------- Island Candy --------
ic_fp = 'C:/Users/mario/island_candy_ad_images/preview_all12.html'
with open(ic_fp, encoding='utf-8') as f:
    ic_content = f.read()
ic_pattern = r'AD #(\d+)\s*[^\<]*</div>.*?line-height:1\.6;">(.*?)</div>'
ic_matches = re.findall(ic_pattern, ic_content, re.DOTALL)
ic_manifest = json.load(open('C:/Users/mario/island_candy_ad_images/fal_generation_manifest.json', encoding='utf-8'))
ic_fal = {item['name']: item.get('size_mb') for item in ic_manifest}
ic_mnames = ['cool_down', 'sweet_reward', 'homemade_icecream', 'instagram_cone', 'candy_store_wonder',
             'souvenir_sweets', 'family_tradition', 'late_night_sweet', 'candy_discovery',
             'arcade_powerup', 'spring_break_treat', 'beach_to_candy']

ic_ads = []
for num, body in ic_matches:
    text = re.sub(r'<br\s*/?>', '\n', body)
    text = re.sub(r'<[^>]+>', '', text).strip()
    text = text.replace('&amp;', '&')
    idx = int(num) - 1
    mname = ic_mnames[idx] if idx < len(ic_mnames) else None
    size_mb = ic_fal.get(mname) if mname else None
    angle = mname if mname else f'ad_{num}'
    ic_ads.append({
        'name': f'Island Candy — Ad {num} {mname.replace("_", " ").title() if mname else ""}',
        'client_id': CLIENTS['island_candy'],
        'fal_url': None,
        'size_mb': size_mb,
        'copy_body': text,
        'copy_headline': first_line(text),
        'copy_cta': extract_cta(text),
        'copy_hashtags': extract_hashtags(text),
        'ad_angle': angle,
        'status': 'approved',
    })
ic_ads.append(add_march14('island_candy', 'island_candy', 'Island Candy'))

# -------- SPI Fun Rentals --------
spi_ads = []
spi_prev = 'C:/Users/mario/spi_fun_rentals_ad_images/preview_spi_ad2.html'
if os.path.exists(spi_prev):
    with open(spi_prev, encoding='utf-8') as f:
        sc = f.read()
    match = re.search(r'<div class="body">(.*?)</div>', sc, re.DOTALL)
    if match:
        text = re.sub(r'<br\s*/?>', '\n', match.group(1))
        text = re.sub(r'<[^>]+>', '', text).strip()
        spi_ads.append({
            'name': 'SPI Fun Rentals — Family Connection',
            'client_id': CLIENTS['spi_fun_rentals'],
            'fal_url': None,
            'size_mb': 0.678,
            'copy_body': text,
            'copy_headline': first_line(text),
            'copy_cta': extract_cta(text),
            'copy_hashtags': extract_hashtags(text),
            'ad_angle': 'family_connection',
            'status': 'approved',
        })
spi_ads.append(add_march14('spi', 'spi_fun_rentals', 'SPI Fun Rentals'))

# Build SQL
all_ads = ss_ads + ia_ads + ic_ads + spi_ads
all_ads = [a for a in all_ads if a is not None]

rows = []
for ad in all_ads:
    size = str(ad['size_mb']) if ad.get('size_mb') else 'NULL'
    row = (
        f"({e(OWNER_ID)},{e(ad['client_id'])},{e(ad['name'])},"
        f"{e(ad.get('fal_url'))},NULL,{size},"
        f"{e(ad['copy_headline'])},{e(ad['copy_body'])},{e(ad['copy_cta'])},"
        f"{e(ad['ad_angle'])},{e(ad['status'])},{e(ad.get('copy_hashtags'))})"
    )
    rows.append(row)

sql = ('INSERT INTO ad_creatives '
       '(owner_id,client_id,name,fal_url,storage_url,size_mb,copy_headline,copy_body,copy_cta,ad_angle,status,copy_hashtags)'
       ' VALUES\n')
sql += ',\n'.join(rows)
sql += '\nON CONFLICT DO NOTHING;'

out = 'C:/Users/mario/.gemini/antigravity/tools/execution/supabase_ads_insert.sql'
with open(out, 'w', encoding='utf-8') as f:
    f.write(sql)

print(f'Total ads: {len(all_ads)}')
print(f'  Sugar Shack: {len(ss_ads)}')
print(f'  Island Arcade: {len(ia_ads)}')
print(f'  Island Candy: {len(ic_ads)}')
print(f'  SPI Fun Rentals: {len(spi_ads)}')
print(f'SQL written to: {out}')
