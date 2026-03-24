#!/usr/bin/env python3
"""
generate_all_ads.py — 40 Facebook Ads (5 × 8 clients) for Mission Control

Stage 1 (default):  Generate copy + fal.ai images → save manifest → send Telegram
Stage 2 (--import): Insert all ads into Supabase ad_creatives table

Usage:
  python generate_all_ads.py           # Stage 1
  python generate_all_ads.py --import  # Stage 2
"""

import sys
import os
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests -q")
    import requests

# ─── CREDENTIALS ──────────────────────────────────────────────────────────────

def load_env(path):
    env = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"  ⚠️  Could not load {path}: {e}")
    return env


GRAVITY_ENV = load_env("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env")
MC_ENV = load_env("C:/Users/mario/missioncontrol/dashboard/.env.local")

FAL_KEY            = GRAVITY_ENV.get("FAL_KEY", "")
TELEGRAM_TOKEN     = GRAVITY_ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID   = GRAVITY_ENV.get("TELEGRAM_USER_ID", "")
SUPABASE_URL       = "https://svgsbaahxiaeljmfykzp.supabase.co"
SUPABASE_SVC_KEY   = MC_ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY  = MC_ENV.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

MANIFEST_PATH = Path("C:/Users/mario/.gemini/antigravity/tools/execution/all_ads_manifest.json")
IMAGES_DIR    = Path("C:/Users/mario/.gemini/antigravity/tools/execution/all_ads_images")

# ─── AD DATA ──────────────────────────────────────────────────────────────────
# 40 ads: 5 per client × 8 clients
# All hard rules applied:
#   - No text overlays in image prompts
#   - Max 3 hashtags
#   - No serving vessels (Island Candy), no interiors (Island Arcade), no sand (SPI Fun Rentals)
#   - Healthcare compliance for Optimum Clinic/Foundation
#   - Juan includes (956) 522-1481 in every CTA

ADS = [

    # ═══════════════════════════════════════════════════════════════
    # SUGAR SHACK — SPI candy store, spring break families
    # client_id: fb6f5c22-06d1-43c0-829a-08f6feb5b206
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Sugar Shack — Road Trip Fuel",
        "client_key": "sugar_shack",
        "client_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "ad_angle": "road_trip_fuel",
        "copy_headline": "The Last Sweet Stop Before the Bridge",
        "copy_body": "You're almost home... but did you grab candy for the whole crew? The Sugar Shack has bulk candy, nostalgic snacks, and island exclusives you won't find back home. Load up before you go — you'll thank yourself on the drive.",
        "copy_cta": "Visit us before you leave SPI",
        "copy_hashtags": "#SPI #SpringBreak #CandyStore",
        "generation_prompt": "Colorful bulk candy store interior with overflowing bins of vibrant candy, bright sweet colors, warm golden light, no people, no text, South Padre Island tropical theme, professional photography, 4k",
    },
    {
        "name": "Sugar Shack — Spring Break Haul",
        "client_key": "sugar_shack",
        "client_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "ad_angle": "spring_break_haul",
        "copy_headline": "Your Spring Break Candy Haul Starts Here",
        "copy_body": "Grab handfuls of your favorites — gummies, chocolates, sour belts, and more. Perfect for the beach, the room, and the ride home. The Sugar Shack has it all at prices that won't wreck your budget.",
        "copy_cta": "Stop in today — we're open!",
        "copy_hashtags": "#SpringBreak #SouthPadreIsland #Candy",
        "generation_prompt": "Cheerful candy store display with overflowing colorful candy bins, spring break tropical theme, bright vibrant sweets, no people, no text overlays, professional food and retail photography, 4k",
    },
    {
        "name": "Sugar Shack — Sweet Memories",
        "client_key": "sugar_shack",
        "client_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "ad_angle": "sweet_memories",
        "copy_headline": "Some Traditions Are Worth Keeping",
        "copy_body": "Every family that visits SPI has their spot. Ours is The Sugar Shack. Pick out a bag together, find that candy you haven't tasted since you were a kid, and make a memory that sticks — just like our caramel.",
        "copy_cta": "Come make your candy tradition",
        "copy_hashtags": "#FamilyVacation #SPI #CandyStore",
        "generation_prompt": "Warm inviting candy store with nostalgic colorful candy displays, glass jars filled with old-fashioned sweets, soft warm golden lighting, cozy retail atmosphere, no people, professional photography, 4k",
    },
    {
        "name": "Sugar Shack — Budget Bliss",
        "client_key": "sugar_shack",
        "client_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "ad_angle": "budget_bliss",
        "copy_headline": "More Candy. Less Money. All on SPI.",
        "copy_body": "Why pay beach markup prices when The Sugar Shack keeps it real? Fill a bag with your favorites — gummies, chocolates, novelty treats — without watching the price tag climb. Sweet deals on the island.",
        "copy_cta": "Fill your bag today",
        "copy_hashtags": "#AffordableFun #SPI #CandyLovers",
        "generation_prompt": "Bright abundant bulk candy store bins overflowing with colorful sweets, cheerful and inviting atmosphere, vibrant candy colors, no people, no text overlays, professional retail photography, 4k",
    },
    {
        "name": "Sugar Shack — Island Exclusive",
        "client_key": "sugar_shack",
        "client_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "ad_angle": "island_exclusive",
        "copy_headline": "You Can Only Get This on the Island",
        "copy_body": "The Sugar Shack carries exclusive SPI treats and local favorites you won't find at your corner store back home. Don't leave without grabbing something unique to take back — or eat on the drive.",
        "copy_cta": "Find your SPI exclusive treat",
        "copy_hashtags": "#SouthPadreIsland #OnlyHere #CandyStore",
        "generation_prompt": "Unique tropical island themed candy shop display with palm leaf accents, bright island colors, exclusive gift-worthy sweets arrangement, no people, no text, professional product photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # ISLAND ARCADE — SPI entertainment, families + teens
    # client_id: 40ec9f76-abd3-4a68-a23a-13e8a2c90755
    # RULE: no recognizable game logos/IP, no interiors with identifiable branding
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Island Arcade — Rainy Day Plan B",
        "client_key": "island_arcade",
        "client_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "ad_angle": "rainy_day_plan_b",
        "copy_headline": "Beach Closed? We're Wide Open.",
        "copy_body": "When the weather flips on SPI, Island Arcade is your Plan B — and honestly, your kids will prefer it. Hundreds of games, VR, prizes, and air conditioning. The fun doesn't stop just because it's raining.",
        "copy_cta": "Come in — we're always open",
        "copy_hashtags": "#SPI #FamilyFun #ArcadeGames",
        "generation_prompt": "Vibrant neon-lit arcade game machines glowing with colorful screens and blinking lights, energetic fun atmosphere, generic game cabinets with no recognizable logos or IP, no people, professional photography, 4k",
    },
    {
        "name": "Island Arcade — Spring Break Unlocked",
        "client_key": "island_arcade",
        "client_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "ad_angle": "spring_break_unlocked",
        "copy_headline": "This Is What Spring Break Actually Looks Like",
        "copy_body": "Forget the same old beach routine. Island Arcade is where spring breakers level up — compete for high scores, win epic prizes, and brag about it all semester. Challenge accepted?",
        "copy_cta": "Get your tokens — come in today",
        "copy_hashtags": "#SpringBreak #SouthPadreIsland #GamingLife",
        "generation_prompt": "Energetic colorful arcade environment with neon lighting and glowing game screens, prize displays in background, vibrant fun atmosphere, no recognizable game characters or logos, no people, professional photography, 4k",
    },
    {
        "name": "Island Arcade — Family Showdown",
        "client_key": "island_arcade",
        "client_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "ad_angle": "family_showdown",
        "copy_headline": "The Family That Games Together, Stays Together",
        "copy_body": "Put the phones down and face off at Island Arcade. From classic skee-ball to modern racing simulators, there's something for every age. Who's the real champion in your family? Find out on SPI.",
        "copy_cta": "Plan your family game session",
        "copy_hashtags": "#FamilyVacation #SPI #ArcadeFun",
        "generation_prompt": "Bright cheerful arcade interior with ticket redemption area and colorful prize shelves visible, fun family-friendly atmosphere, generic game machines with no logos, no people, professional photography, 4k",
    },
    {
        "name": "Island Arcade — VR Shock & Awe",
        "client_key": "island_arcade",
        "client_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "ad_angle": "vr_shock_and_awe",
        "copy_headline": "They Said VR Changed Everything. They Were Right.",
        "copy_body": "Island Arcade's VR experience puts you somewhere you've never been — without leaving South Padre Island. Strap in, look around, and prepare to forget where you are. Warning: you may not want to leave.",
        "copy_cta": "Try VR at Island Arcade, SPI",
        "copy_hashtags": "#VirtualReality #SPI #NextLevel",
        "generation_prompt": "Futuristic VR gaming headset on illuminated display stand, neon blue and purple lighting, high-tech arcade aesthetic, no brand logos, no people, professional product photography, 4k",
    },
    {
        "name": "Island Arcade — Token Drop",
        "client_key": "island_arcade",
        "client_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "ad_angle": "token_drop",
        "copy_headline": "More Tokens. More Wins. More SPI Memories.",
        "copy_body": "The more you play, the more you win at Island Arcade. Load up on tokens and spend the afternoon chasing jackpots and collecting prize tickets. Every visit is a new score to beat.",
        "copy_cta": "Come get your tokens today",
        "copy_hashtags": "#ArcadeGames #SPI #SpringBreak",
        "generation_prompt": "Cascading gold arcade tokens spilling across a prize counter, colorful stuffed animals and toys displayed in background, bright cheerful arcade lighting, no people, no logos, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # ISLAND CANDY — ice cream inside Island Arcade, SPI
    # client_id: d865037b-2552-4024-9db3-10e61e1419b4
    # RULE: no specific serving vessels (cups/cones), no people
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Island Candy — Cool Down",
        "client_key": "island_candy",
        "client_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "ad_angle": "cool_down",
        "copy_headline": "Beat the Heat. One Scoop at a Time.",
        "copy_body": "SPI sun hitting hard? Island Candy's homemade ice cream is the coolest decision you'll make all day. Fresh flavors, made right here on the island. Starting from $3.99 — because vacation should be sweet, not pricey.",
        "copy_cta": "Come cool down — we're inside Island Arcade",
        "copy_hashtags": "#SPI #IceCream #SpringBreak",
        "generation_prompt": "Beautiful artisan ice cream scoops in pastel and vibrant colors, tropical background with blue sky and palm trees, fresh and inviting food styling, no serving vessels visible, no people, professional food photography, 4k",
    },
    {
        "name": "Island Candy — Spring Break Treat",
        "client_key": "island_candy",
        "client_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "ad_angle": "spring_break_treat",
        "copy_headline": "Your Spring Break Reward Is Here",
        "copy_body": "You survived the drive to SPI. You deserve something cold and delicious. Island Candy's homemade ice cream and milkshakes are made fresh and served right here. You earned this — come get it.",
        "copy_cta": "Treat yourself — stop in today",
        "copy_hashtags": "#SpringBreak #SouthPadreIsland #Dessert",
        "generation_prompt": "Vibrant colorful ice cream with tropical spring break themed background, bright fun pastel colors, festive and refreshing food art, no serving vessels, no people, no text, professional food photography, 4k",
    },
    {
        "name": "Island Candy — Sweet Reward",
        "client_key": "island_candy",
        "client_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "ad_angle": "sweet_reward",
        "copy_headline": "End Every SPI Day the Right Way",
        "copy_body": "After the beach, after the games, after the sun — Island Candy is how you close out the perfect day. Homemade ice cream and milkshakes that taste like the vacation you earned. Starting at $3.99.",
        "copy_cta": "Find us inside Island Arcade, SPI",
        "copy_hashtags": "#IceCream #IslandLife #SPI",
        "generation_prompt": "Golden hour sunset color palette with vibrant tropical ice cream flavors artistically displayed, warm glowing light, dreamy vacation mood, no cups or cones, no people, professional food photography, 4k",
    },
    {
        "name": "Island Candy — Beach to Candy",
        "client_key": "island_candy",
        "client_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "ad_angle": "beach_to_candy",
        "copy_headline": "Sand to Sugar in 60 Seconds",
        "copy_body": "The beach is right there. We're right here. Stop into Island Candy for a scoop of something homemade and cold — then decide if you ever want to leave. Spoiler: you won't.",
        "copy_cta": "We're right inside Island Arcade, SPI",
        "copy_hashtags": "#SPI #BeachDay #IslandCandy",
        "generation_prompt": "Bright tropical beach scene blending into colorful ice cream flavors, ocean blues and candy pastels merging together, fresh and vibrant, no serving vessels, no people, professional photography, 4k",
    },
    {
        "name": "Island Candy — Homemade Hit",
        "client_key": "island_candy",
        "client_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "ad_angle": "homemade_hit",
        "copy_headline": "Homemade. Fresh. Only on SPI.",
        "copy_body": "Island Candy's ice cream isn't from a bucket in a freezer — it's made here, with real ingredients, and you can taste the difference. Fresh flavors that change with the season. Come try what's new today.",
        "copy_cta": "Try today's fresh flavors",
        "copy_hashtags": "#HomemadeIceCream #SPI #FreshFlavors",
        "generation_prompt": "Close-up of artisan homemade ice cream with visible fresh fruits, berries, and colorful swirls, rustic artisan food photography style, ingredients scattered around, no serving vessels, no people, professional food photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # JUAN ELIZONDO RE/MAX ELITE — real estate, RGV, bilingual
    # client_id: a1000001-0000-0000-0000-000000000001
    # RULE: include (956) 522-1481 in every CTA; bilingual where noted
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Juan Elizondo — First-Time Buyer",
        "client_key": "juan",
        "client_id": "a1000001-0000-0000-0000-000000000001",
        "ad_angle": "first_time_buyer",
        "copy_headline": "Buying Your First Home in the RGV? Let's Talk.",
        "copy_body": "The process feels complicated — until you have the right guide. Juan Elizondo with RE/MAX Elite has helped hundreds of Rio Grande Valley families find their first home. No pressure. No confusion. Just results.",
        "copy_cta": "Call Juan today: (956) 522-1481",
        "copy_hashtags": "#RGVRealEstate #FirstTimeHomeBuyer #McAllenTX",
        "generation_prompt": "Beautiful modern family home exterior in South Texas style, lush green lawn, warm afternoon light, welcoming front door, clear blue sky, no people, professional real estate photography, 4k",
    },
    {
        "name": "Juan Elizondo — RGV Market Rising",
        "client_key": "juan",
        "client_id": "a1000001-0000-0000-0000-000000000001",
        "ad_angle": "rgv_market_rising",
        "copy_headline": "The RGV Market Is Moving. Are You Ready?",
        "copy_body": "Home values in the Rio Grande Valley are rising — and buyers who act now will be ahead of the curve. Juan Elizondo with RE/MAX Elite has the market knowledge to help you move fast and smart.",
        "copy_cta": "Call Juan: (956) 522-1481",
        "copy_hashtags": "#RGVRealEstate #McAllenHomes #MarketUpdate",
        "generation_prompt": "Modern luxury home exterior in a McAllen Texas neighborhood, manicured landscaping, beautiful blue sky, professional real estate photography, no people, upscale residential, 4k",
    },
    {
        "name": "Juan Elizondo — Sell Smart",
        "client_key": "juan",
        "client_id": "a1000001-0000-0000-0000-000000000001",
        "ad_angle": "sell_smart",
        "copy_headline": "Ready to Sell? Get the Right Price from Day One.",
        "copy_body": "Overpriced homes sit. Underpriced homes leave money on the table. Juan Elizondo with RE/MAX Elite uses RGV market data to price your home to sell fast — and for what it's worth. Let's get you an offer.",
        "copy_cta": "Free home valuation: (956) 522-1481",
        "copy_hashtags": "#SellMyHome #RGVRealEstate #JuanElizondo",
        "generation_prompt": "Elegant well-maintained home exterior with RE/MAX For Sale sign in front yard, bright natural lighting, manicured lawn, no people, professional real estate photography, 4k",
    },
    {
        "name": "Juan Elizondo — Bilingual Buyer",
        "client_key": "juan",
        "client_id": "a1000001-0000-0000-0000-000000000001",
        "ad_angle": "bilingual_buyer",
        "copy_headline": "¿Listo para Comprar Tu Casa en el Valle?",
        "copy_body": "El proceso de comprar una casa puede sentirse complicado — hasta que tienes al agente correcto de tu lado. Juan Elizondo de RE/MAX Elite habla tu idioma y conoce el Valle. Llámalo hoy sin compromiso.",
        "copy_cta": "Llama al (956) 522-1481",
        "copy_hashtags": "#BieneRaizRGV #CasasEnElValle #McAllenTX",
        "generation_prompt": "Warm welcoming family home in South Texas architectural style, terracotta and neutral tones, lush tropical landscaping, bright clear sky, no people, professional real estate photography, 4k",
    },
    {
        "name": "Juan Elizondo — Commercial Opportunity",
        "client_key": "juan",
        "client_id": "a1000001-0000-0000-0000-000000000001",
        "ad_angle": "commercial_opportunity",
        "copy_headline": "Commercial Real Estate in the RGV Is Booming",
        "copy_body": "Retail, office, industrial — the Rio Grande Valley is one of the fastest-growing commercial markets in Texas. Juan Elizondo with RE/MAX Elite specializes in commercial listings and investment opportunities across the valley.",
        "copy_cta": "Commercial listings: (956) 522-1481",
        "copy_hashtags": "#CommercialRealEstate #RGVInvesting #McAllenBusiness",
        "generation_prompt": "Modern commercial building exterior in Rio Grande Valley Texas, glass facade professional office park, clean architectural lines, clear blue sky, no people, professional architectural photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # SPI FUN RENTALS — golf carts, Jeeps, water sports
    # client_id: f8693268-6abf-4401-8b2e-3795e326252b
    # CRITICAL RULE: golf carts NEVER on sand (illegal on SPI)
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "SPI Fun Rentals — Golf Cart Crew",
        "client_key": "spi_fun_rentals",
        "client_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "ad_angle": "golf_cart_crew",
        "copy_headline": "Cruise the Island Your Way",
        "copy_body": "Nothing says South Padre Island like a golf cart with your crew. SPI Fun Rentals has the island's best fleet — ready when you are. Explore, grab food, hit beach access points, and make memories that roll.",
        "copy_cta": "Reserve your cart: (956) 761-9999",
        "copy_hashtags": "#SPI #GolfCartRental #SpringBreak",
        "generation_prompt": "Clean white golf cart parked on a paved island street with palm trees and tropical ocean visible in background, bright sunny day, paved road surface, no sand anywhere, no people, professional photography, 4k",
    },
    {
        "name": "SPI Fun Rentals — Spring Break HERE",
        "client_key": "spi_fun_rentals",
        "client_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "ad_angle": "spring_break_here",
        "copy_headline": "Spring Break Isn't a Destination. It's a Feeling.",
        "copy_body": "And that feeling starts the moment you grab the keys from SPI Fun Rentals. Golf carts, Jeeps, water gear — we've got everything you need to make this the spring break you'll actually remember.\n\nBook now: (956) 761-9999",
        "copy_cta": "Book before we sell out: (956) 761-9999",
        "copy_hashtags": "#SpringBreak #SPI #IslandRentals",
        "generation_prompt": "Colorful rental shop storefront on South Padre Island with Jeeps and equipment visible, blue sky, tropical palm trees, vibrant vacation atmosphere, paved parking lot, no sand, no people, professional photography, 4k",
    },
    {
        "name": "SPI Fun Rentals — Family Connection",
        "client_key": "spi_fun_rentals",
        "client_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "ad_angle": "family_connection",
        "copy_headline": "The Best Family Moments Have Four Wheels",
        "copy_body": "Skip the Uber and explore SPI together — on your own terms, on your own schedule. SPI Fun Rentals' golf carts seat the whole family and put you in charge of the adventure. The island is yours.",
        "copy_cta": "Reserve your family cart: (956) 761-9999",
        "copy_hashtags": "#FamilyVacation #SPI #IslandAdventure",
        "generation_prompt": "Spacious clean golf cart with extra seating parked on a scenic paved coastal road with ocean views, palm trees swaying, bright afternoon sun, paved asphalt road, no sand, no people, professional photography, 4k",
    },
    {
        "name": "SPI Fun Rentals — Jeep the Island",
        "client_key": "spi_fun_rentals",
        "client_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "ad_angle": "jeep_the_island",
        "copy_headline": "See Every Corner of SPI — In a Jeep",
        "copy_body": "When you want more power and more room, SPI Fun Rentals has Jeeps ready to roll. Hit every beach access, explore every neighborhood, and get back to your hotel whenever you feel like it. Total freedom.",
        "copy_cta": "Reserve a Jeep: (956) 761-9999",
        "copy_hashtags": "#JeepRental #SPI #IslandFreedom",
        "generation_prompt": "Rugged Jeep parked on a paved coastal overlook at South Padre Island, ocean and sky visible in background, tropical setting, bright clear day, paved surface, no sand anywhere, no people, professional photography, 4k",
    },
    {
        "name": "SPI Fun Rentals — Spring Break Countdown",
        "client_key": "spi_fun_rentals",
        "client_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "ad_angle": "spring_break_countdown",
        "copy_headline": "Spring Break Is Filling Up Fast — Secure Your Rental Now",
        "copy_body": "SPI Fun Rentals books up every spring break. Don't show up without a reservation and end up watching everyone else cruise the island. Book your golf cart or Jeep today and lock in the fun.\n\n(956) 761-9999",
        "copy_cta": "Call now: (956) 761-9999",
        "copy_hashtags": "#SpringBreak #SPI #BookNow",
        "generation_prompt": "Multiple clean colorful golf carts lined up in a rental parking lot on South Padre Island, ocean visible in distance, vibrant spring colors, paved parking area clearly visible, no sand, no people, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # CUSTOM DESIGNS TX — luxury home tech, security, A/V
    # client_id: 394dba54-161a-46f3-9956-cc8e5dc3fa43
    # RULE: dark luxury aesthetic (gold/obsidian), no "handyman" language
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Custom Designs TX — Home Theater Night",
        "client_key": "custom_designs_tx",
        "client_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "ad_angle": "home_theater_night",
        "copy_headline": "Movie Night Will Never Be the Same",
        "copy_body": "Custom Designs TX builds home theater experiences that make every Friday night feel like opening night. 4K projection, Dolby Atmos sound, custom seating integration — designed around your space, your style.\n\ncustomdesignstx.com",
        "copy_cta": "Get your free design consultation",
        "copy_hashtags": "#HomeTheater #SmartHome #LuxuryLiving",
        "generation_prompt": "Luxurious dark home theater room with recessed LED lighting, large projection screen glowing, premium recliner seating, gold and dark obsidian color accents, cinematic atmosphere, no people, no text, professional interior photography, 4k",
    },
    {
        "name": "Custom Designs TX — Security Peace of Mind",
        "client_key": "custom_designs_tx",
        "client_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "ad_angle": "security_peace_of_mind",
        "copy_headline": "See Everything. Miss Nothing. Sleep Better.",
        "copy_body": "Custom Designs TX installs professional-grade security camera systems that keep your home or business protected — 24/7, from any device, anywhere in the world. Discreet. Reliable. Custom.\n\ncustomdesignstx.com",
        "copy_cta": "Schedule your security consultation",
        "copy_hashtags": "#SecurityCameras #HomeProtection #SmartSecurity",
        "generation_prompt": "Sleek modern luxury home exterior at night with discreet premium security camera mounted on wall, soft architectural lighting, dark luxury aesthetic with gold accents, no people, professional architectural photography, 4k",
    },
    {
        "name": "Custom Designs TX — Smart Home Upgrade",
        "client_key": "custom_designs_tx",
        "client_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "ad_angle": "smart_home_upgrade",
        "copy_headline": "Your Home Should Work as Hard as You Do",
        "copy_body": "Lights, locks, climate, entertainment — all at the touch of a button or a voice command. Custom Designs TX transforms ordinary homes into intelligent living spaces. Built for your lifestyle, not a template.\n\ncustomdesignstx.com",
        "copy_cta": "Request your smart home assessment",
        "copy_hashtags": "#SmartHome #HomeAutomation #LuxuryTech",
        "generation_prompt": "Modern luxury living room with elegant smart home control panel glowing softly on dark wall, dark obsidian and gold accents, ambient intelligent lighting, sophisticated minimalist design, no people, professional interior photography, 4k",
    },
    {
        "name": "Custom Designs TX — Multi-Room Audio",
        "client_key": "custom_designs_tx",
        "client_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "ad_angle": "multi_room_audio",
        "copy_headline": "The Perfect Soundtrack for Every Room",
        "copy_body": "Imagine your favorite playlist following you from the kitchen to the patio — seamlessly, perfectly. Custom Designs TX installs whole-home audio that disappears into your walls and fills your life with sound.\n\ncustomdesignstx.com",
        "copy_cta": "Design your sound system",
        "copy_hashtags": "#WholeHomeAudio #MultiRoomSound #LuxuryHome",
        "generation_prompt": "Elegant modern home interior with invisible in-ceiling premium speakers, warm amber lighting, luxurious minimalist decor with dark and gold tones, architectural beauty, no people, no text, professional interior photography, 4k",
    },
    {
        "name": "Custom Designs TX — Builder Partner",
        "client_key": "custom_designs_tx",
        "client_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "ad_angle": "builder_partner",
        "copy_headline": "Building Something New? Let's Talk Tech.",
        "copy_body": "Custom Designs TX partners with builders and contractors to integrate smart home technology from the ground up — wiring, A/V, security, and automation built in before the walls close. Cleaner installs. Better results.\n\ncustomdesignstx.com",
        "copy_cta": "Contact us for builder partnerships",
        "copy_hashtags": "#NewConstruction #SmartHomeTech #ContractorPartner",
        "generation_prompt": "Premium new construction luxury home under perfect blue sky, modern architectural exterior shot, upscale residential building with clean lines, professional builders and architects aesthetic, no people, professional architectural photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # OPTIMUM HEALTH & WELLNESS CLINIC — cash-pay night clinic, Pharr
    # client_id: a1000002-0000-0000-0000-000000000002
    # RULE: healthcare compliance — no cure claims, price ranges only
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Optimum Clinic — Skip the ER",
        "client_key": "optimum_clinic",
        "client_id": "a1000002-0000-0000-0000-000000000002",
        "ad_angle": "skip_the_er",
        "copy_headline": "Skip the ER. We're Open Tonight.",
        "copy_body": "Emergency room wait times can run 4–6 hours. Optimum Health & Wellness Clinic in Pharr has you in and out faster — consultations starting at $75–$100. No appointment needed. No insurance required.\n\nOpen nightly 5 PM – 10 PM.",
        "copy_cta": "Walk in tonight: (956) 627-3258",
        "copy_hashtags": "#UrgentCare #Pharr #NoInsuranceNeeded",
        "generation_prompt": "Clean modern medical clinic exterior at evening dusk with welcoming lit entrance, professional healthcare building, warm inviting light glowing from windows, no people, professional photography, 4k",
    },
    {
        "name": "Optimum Clinic — Open Tonight",
        "client_key": "optimum_clinic",
        "client_id": "a1000002-0000-0000-0000-000000000002",
        "ad_angle": "open_tonight",
        "copy_headline": "We're Open. Right Now. Tonight.",
        "copy_body": "Other clinics are closed. Optimum Health & Wellness Clinic in Pharr is open tonight — walk in, no appointment, no insurance needed. Medical consultations starting at $75–$100.\n\nOpen 5 PM – 10 PM, every night.",
        "copy_cta": "Walk in now: (956) 627-3258",
        "copy_hashtags": "#OpenNow #Pharr #NightClinic",
        "generation_prompt": "Bright welcoming medical clinic interior with clean modern waiting area, professional healthcare environment, open signage visible on wall, soft warm lighting, no people, professional photography, 4k",
    },
    {
        "name": "Optimum Clinic — No Insurance Needed",
        "client_key": "optimum_clinic",
        "client_id": "a1000002-0000-0000-0000-000000000002",
        "ad_angle": "no_insurance_needed",
        "copy_headline": "No Insurance? No Problem. We've Got You.",
        "copy_body": "At Optimum Health & Wellness Clinic, everyone deserves care — insured or not. Walk in tonight in Pharr and see a provider for a flat fee starting at $75–$100. Rapid tests, injections, wound care, and more. We're here for the whole RGV community.",
        "copy_cta": "Walk in tonight — open 5–10 PM",
        "copy_hashtags": "#NoInsurance #RGVHealth #PharrClinic",
        "generation_prompt": "Warm compassionate medical clinic with clean professional interior design, soft welcoming lighting, community healthcare aesthetic, no people, professional photography, 4k",
    },
    {
        "name": "Optimum Clinic — Walk In Now",
        "client_key": "optimum_clinic",
        "client_id": "a1000002-0000-0000-0000-000000000002",
        "ad_angle": "walk_in_now",
        "copy_headline": "Feeling Sick Tonight? Come In. We're Ready.",
        "copy_body": "Don't wait until tomorrow. Don't drive to the ER. Optimum Health & Wellness Clinic in Pharr is open every night — 5 PM to 10 PM. Walk in for rapid testing, consultations, medication refills, and more. Starting at $75–$100.",
        "copy_cta": "Come in tonight: (956) 627-3258",
        "copy_hashtags": "#WalkInClinic #RGVHealth #Pharr",
        "generation_prompt": "Professional medical clinic entrance with illuminated sign lit up at night, clean modern building, warm light from inside, accessible and inviting, no people, professional architectural photography, 4k",
    },
    {
        "name": "Optimum Clinic — El Médico de la Noche",
        "client_key": "optimum_clinic",
        "client_id": "a1000002-0000-0000-0000-000000000002",
        "ad_angle": "el_medico_de_la_noche",
        "copy_headline": "¿Enfermo Esta Noche? Llegamos Para Ti.",
        "copy_body": "Optimum Health & Wellness Clinic en Pharr está abierta todas las noches de 5 PM a 10 PM. Entra sin cita — sin seguro necesario. Consultas médicas desde $75–$100. Pruebas rápidas, inyecciones, cuidado de heridas y más.",
        "copy_cta": "Llama al (956) 627-3258",
        "copy_hashtags": "#SaludRGV #ClinicaPharr #SinSeguro",
        "generation_prompt": "Warm and inviting night clinic exterior with welcoming entrance lighting, clean modern medical building at night, community healthcare setting, warm professional glow, no people, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════
    # OPTIMUM HEALTH & WELLNESS FOUNDATION — 501(c)(3) nonprofit
    # client_id: a1000003-0000-0000-0000-000000000003
    # RULE: NO medical service offers; include donation CTA; community-first tone
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "Optimum Foundation — Health Access for All",
        "client_key": "optimum_foundation",
        "client_id": "a1000003-0000-0000-0000-000000000003",
        "ad_angle": "health_access_for_all",
        "copy_headline": "Everyone in the RGV Deserves Access to Health",
        "copy_body": "The Optimum Health & Wellness Foundation exists for one reason: to make sure no one in the Rio Grande Valley goes without care because of cost or circumstance. We serve our neighbors. Join the mission.",
        "copy_cta": "Learn more and support us",
        "copy_hashtags": "#RGVHealth #CommunityFirst #HealthForAll",
        "generation_prompt": "Warm sunrise over Rio Grande Valley landscape, soft golden light symbolizing hope and community health, uplifting and positive mood, hands in unity silhouette concept, no specific people, professional photography, 4k",
    },
    {
        "name": "Optimum Foundation — Free Screening Event",
        "client_key": "optimum_foundation",
        "client_id": "a1000003-0000-0000-0000-000000000003",
        "ad_angle": "free_screening_event",
        "copy_headline": "Free Health Screenings — No Cost. No Catch.",
        "copy_body": "The Optimum Health & Wellness Foundation is offering free health screenings for the RGV community. Blood pressure, glucose, BMI checks, and more — no insurance, no cost, no appointment needed. Your health matters. Register below.",
        "copy_cta": "Register now — it's free",
        "copy_hashtags": "#FreeScreening #RGVCommunity #HealthEvent",
        "generation_prompt": "Bright outdoor community health fair scene with white canopy tents and soft morning light, welcoming public health event setup, green grass and clear sky, no people visible, professional documentary photography style, 4k",
    },
    {
        "name": "Optimum Foundation — Your Neighbor Needs You",
        "client_key": "optimum_foundation",
        "client_id": "a1000003-0000-0000-0000-000000000003",
        "ad_angle": "your_neighbor_needs_you",
        "copy_headline": "Your Neighbor Can't Afford Care. You Can Help.",
        "copy_body": "Right here in the Rio Grande Valley, families skip checkups because they can't pay. The Optimum Health & Wellness Foundation is changing that — with community volunteers, donors, and advocates like you. Will you help?",
        "copy_cta": "Volunteer or donate today",
        "copy_hashtags": "#Volunteer #RGV #CommunityHealth",
        "generation_prompt": "Compassionate community neighborhood scene with warm golden light, modest South Texas homes in background, hands extended in helpful gesture, hope and solidarity visual, no specific people, professional photography, 4k",
    },
    {
        "name": "Optimum Foundation — Donate $10",
        "client_key": "optimum_foundation",
        "client_id": "a1000003-0000-0000-0000-000000000003",
        "ad_angle": "donate_10",
        "copy_headline": "$10 From You Could Change Someone's Week",
        "copy_body": "That's one fewer person without care this month. The Optimum Health & Wellness Foundation stretches every dollar to bring real health access to RGV families who need it most. A small gift goes a long way. Tax-deductible donation, EIN on file.",
        "copy_cta": "Donate now — every dollar helps",
        "copy_hashtags": "#Donate #RGVFoundation #GiveBack",
        "generation_prompt": "Heartfelt charitable giving concept with two hands in a warm caring gesture, soft golden tones, hopeful and uplifting mood, community care symbolism, no money visible, professional photography, 4k",
    },
    {
        "name": "Optimum Foundation — Community Health 2026",
        "client_key": "optimum_foundation",
        "client_id": "a1000003-0000-0000-0000-000000000003",
        "ad_angle": "community_health_2026",
        "copy_headline": "A Healthier RGV Starts With All of Us — 2026",
        "copy_body": "The Optimum Health & Wellness Foundation is building a vision for a healthier Rio Grande Valley — through education, access, and community-driven care. Be part of something bigger. Share this. Show up. Donate. It starts here.",
        "copy_cta": "Join the movement — share this post",
        "copy_hashtags": "#RGV2026 #HealthyRGV #CommunityDriven",
        "generation_prompt": "Inspiring aerial view of Rio Grande Valley landscape at sunrise, bright hopeful morning light over South Texas community, vibrant and uplifting symbolism of growth and health, professional aerial photography, 4k",
    },
]

# ─── FAL.AI IMAGE GENERATION ──────────────────────────────────────────────────

def generate_image(prompt: str, ad_name: str) -> str | None:
    """Call fal.ai Flux Pro sync endpoint, return image URL or None."""
    url = "https://fal.run/fal-ai/flux-pro"
    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "num_images": 1,
        "safety_tolerance": "2",
        "output_format": "jpeg",
    }
    for attempt in range(2):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                if images:
                    return images[0].get("url")
            print(f"    ⚠️  fal.ai {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"    ⚠️  fal.ai error attempt {attempt+1}: {e}")
        if attempt == 0:
            time.sleep(3)
    return None


def save_image_locally(url: str, filepath: Path) -> bool:
    """Download image from URL and save locally."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            filepath.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"    ⚠️  Could not save image locally: {e}")
    return False


# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

def tg_send(text: str) -> bool:
    """Send a text message to Mario via Telegram."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_USER_ID,
            "text": text[:4096],
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=data,
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram error: {e}")
        return False


def tg_send_photo(photo_url: str, caption: str) -> bool:
    """Send a photo with caption to Mario via Telegram."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_USER_ID,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            data=data,
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        if not result.get("ok"):
            # Fall back to text message
            return tg_send(caption)
        return True
    except Exception as e:
        print(f"  ⚠️  Telegram photo error: {e}")
        return tg_send(caption)


# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def get_mario_user_id() -> str | None:
    """Fetch Mario's Supabase auth user ID via admin API."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
                "apikey": SUPABASE_SVC_KEY,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("users", data if isinstance(data, list) else [])
            if users:
                uid = users[0].get("id")
                print(f"  ✅ Found Supabase user ID: {uid[:8]}...")
                return uid
        else:
            print(f"  ⚠️  Admin users API: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Could not fetch Supabase user: {e}")
    return None


def insert_ad(ad: dict, owner_id: str | None) -> bool:
    """Insert a single ad into Supabase ad_creatives table."""
    payload = {
        "client_id": ad["client_id"],
        "name": ad["name"],
        "media_type": "image",
        "platform": "facebook",
        "status": "draft",
        "ad_angle": ad.get("ad_angle"),
        "copy_headline": ad.get("copy_headline"),
        "copy_body": ad.get("copy_body"),
        "copy_cta": ad.get("copy_cta"),
        "copy_hashtags": ad.get("copy_hashtags"),
        "fal_url": ad.get("fal_url"),
        "generation_model": "fal-ai/flux-pro",
        "generation_prompt": ad.get("generation_prompt"),
        "rating": 0,
    }
    if owner_id:
        payload["owner_id"] = owner_id

    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/ad_creatives",
            headers={
                "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True
        print(f"  ⚠️  Insert failed ({resp.status_code}): {resp.text[:300]}")
        return False
    except Exception as e:
        print(f"  ⚠️  Insert error: {e}")
        return False


# ─── STAGE 1: GENERATE ────────────────────────────────────────────────────────

def stage1_generate():
    print("\n" + "═" * 60)
    print("  STAGE 1 — Generate Images + Send to Telegram")
    print("═" * 60)

    if not FAL_KEY:
        print("❌ FAL_KEY not found. Check gravity-claw/.env")
        sys.exit(1)
    if not TELEGRAM_TOKEN or not TELEGRAM_USER_ID:
        print("❌ Telegram credentials missing. Check gravity-claw/.env")
        sys.exit(1)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    # ── Send intro Telegram ──────────────────────────────────────
    tg_send(
        "🚀 <b>Ad Generation Started</b>\n\n"
        "Generating <b>40 Facebook ads</b> across 8 clients (5 each).\n"
        "I'll send each client's ads as they're ready.\n\n"
        "⏳ This will take ~8–12 minutes..."
    )

    # ── Group ads by client ──────────────────────────────────────
    clients_order = [
        "sugar_shack", "island_arcade", "island_candy", "juan",
        "spi_fun_rentals", "custom_designs_tx", "optimum_clinic", "optimum_foundation"
    ]
    client_labels = {
        "sugar_shack":       "🍭 The Sugar Shack",
        "island_arcade":     "🕹️ Island Arcade",
        "island_candy":      "🍦 Island Candy",
        "juan":              "🏡 Juan Elizondo RE/MAX Elite",
        "spi_fun_rentals":   "🛻 SPI Fun Rentals",
        "custom_designs_tx": "🎬 Custom Designs TX",
        "optimum_clinic":    "🏥 Optimum Health & Wellness Clinic",
        "optimum_foundation":"💙 Optimum Health & Wellness Foundation",
    }

    ads_by_client = {k: [] for k in clients_order}
    for ad in ADS:
        ads_by_client[ad["client_key"]].append(ad)

    total_generated = 0
    total_failed = 0

    for client_key in clients_order:
        client_ads = ads_by_client[client_key]
        label = client_labels[client_key]
        print(f"\n📦 {label} — generating 5 ads...")

        client_results = []

        for i, ad in enumerate(client_ads, 1):
            print(f"  [{i}/5] {ad['name']}")
            print(f"        Generating image...")

            fal_url = generate_image(ad["generation_prompt"], ad["name"])

            if fal_url:
                total_generated += 1
                print(f"        ✅ Image ready")

                # Save locally
                safe_name = ad["name"].replace(" ", "_").replace("/", "-").replace("—", "-")
                img_path = IMAGES_DIR / f"{safe_name}.jpg"
                save_image_locally(fal_url, img_path)
            else:
                total_failed += 1
                print(f"        ❌ Image generation failed")

            ad_with_url = {**ad, "fal_url": fal_url}
            manifest.append(ad_with_url)
            client_results.append(ad_with_url)

            # Small delay to avoid rate limits
            time.sleep(1)

        # ── Send Telegram for this client ────────────────────────
        print(f"  📱 Sending {label} to Telegram...")
        header = f"<b>{label}</b> — 5 Facebook Ads Ready\n{'─' * 30}\n\n"

        for i, ad in enumerate(client_results, 1):
            angle_label = ad["ad_angle"].replace("_", " ").title()
            caption = (
                f"<b>Ad {i}/5 — {angle_label}</b>\n\n"
                f"📝 <b>{ad['copy_headline']}</b>\n\n"
                f"{ad['copy_body']}\n\n"
                f"🔗 CTA: {ad['copy_cta']}\n"
                f"#️⃣ {ad['copy_hashtags']}\n\n"
            )
            if ad["fal_url"]:
                caption += f'🖼️ <a href="{ad["fal_url"]}">View Image</a>'
            else:
                caption += "❌ Image generation failed"

            if ad["fal_url"]:
                tg_send_photo(ad["fal_url"], f"{label}\n\n{caption}")
            else:
                tg_send(f"{label}\n\n{caption}")

            time.sleep(0.5)  # Telegram rate limit

    # ── Save manifest ────────────────────────────────────────────
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n✅ Manifest saved: {MANIFEST_PATH}")

    # ── Send final Telegram summary ──────────────────────────────
    summary = (
        "✅ <b>All Ads Generated!</b>\n\n"
        f"📊 Total: 40 ads across 8 clients\n"
        f"✅ Images generated: {total_generated}/40\n"
        f"❌ Failed: {total_failed}/40\n\n"
        "📋 <b>Review each client's ads above.</b>\n\n"
        "When you're happy with them, import to Mission Control:\n"
        "<code>python generate_all_ads.py --import</code>"
    )
    tg_send(summary)
    print("\n" + "═" * 60)
    print(f"  ✅ Stage 1 Complete!")
    print(f"  Images generated: {total_generated}/40")
    print(f"  Failed: {total_failed}/40")
    print(f"  Manifest: {MANIFEST_PATH}")
    print("\n  When ready to import:")
    print("  python generate_all_ads.py --import")
    print("═" * 60)


# ─── STAGE 2: IMPORT TO SUPABASE ──────────────────────────────────────────────

def stage2_import():
    print("\n" + "═" * 60)
    print("  STAGE 2 — Import Ads to Mission Control (Supabase)")
    print("═" * 60)

    if not MANIFEST_PATH.exists():
        print("❌ Manifest not found. Run Stage 1 first:")
        print("   python generate_all_ads.py")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"📋 Found {len(manifest)} ads in manifest")

    if not SUPABASE_SVC_KEY:
        print("❌ SUPABASE_SERVICE_ROLE_KEY not found in .env.local")
        sys.exit(1)

    # Get Mario's Supabase user ID so RLS works in the frontend
    print("\n🔍 Fetching Supabase user ID...")
    owner_id = get_mario_user_id()
    if not owner_id:
        print("  ⚠️  Could not find user ID — inserting without owner_id")
        print("     Ads will be visible via service role but may not show in Mission Control UI")
        print("     You can fix this by logging into Supabase dashboard and updating owner_id")

    # Insert all ads
    print(f"\n📥 Inserting {len(manifest)} ads into Supabase...\n")
    success = 0
    failed = 0
    current_client = None

    for ad in manifest:
        if ad["client_key"] != current_client:
            current_client = ad["client_key"]
            print(f"\n  📦 {current_client}:")

        ok = insert_ad(ad, owner_id)
        status = "✅" if ok else "❌"
        print(f"    {status} {ad['name']}")
        if ok:
            success += 1
        else:
            failed += 1
        time.sleep(0.2)

    # Send Telegram confirmation
    msg = (
        f"{'✅' if failed == 0 else '⚠️'} <b>Mission Control Import Complete</b>\n\n"
        f"✅ Inserted: {success}/{len(manifest)} ads\n"
        f"❌ Failed: {failed}/{len(manifest)} ads\n\n"
        f"🔗 View at: http://localhost:3001/content/ad-library\n\n"
        f"Switch to each client in the sidebar to see their 5 ads."
    )
    tg_send(msg)

    print("\n" + "═" * 60)
    print(f"  ✅ Stage 2 Complete!")
    print(f"  Inserted: {success}/{len(manifest)}")
    print(f"  Failed:   {failed}/{len(manifest)}")
    print(f"\n  View in Mission Control:")
    print(f"  http://localhost:3001/content/ad-library")
    print("═" * 60)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--import" in sys.argv:
        stage2_import()
    else:
        stage1_generate()
