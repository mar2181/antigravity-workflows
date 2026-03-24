#!/usr/bin/env python3
"""
weekend_ad_batch.py — Generate 40 ads (5 per client x 8 clients) and push to Mission Control

Generates images via fal.ai Flux Pro, then inserts into Supabase ad_creatives table.
Mario reviews them in Mission Control's Ad Creative Library over the weekend.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).resolve().parent
ENV_FILE = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
MC_ENV_FILE = Path("C:/Users/mario/missioncontrol/dashboard/.env.local")

def load_env(path):
    env = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env

ENV = load_env(ENV_FILE)
MC_ENV = load_env(MC_ENV_FILE)

FAL_KEY = ENV.get("FAL_KEY", "")
SUPABASE_URL = MC_ENV.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = MC_ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")

# ─── CLIENT DB IDS ───────────────────────────────────────────────────────────

CLIENTS = {
    "sugar_shack": {
        "db_id": "fb6f5c22-06d1-43c0-829a-08f6feb5b206",
        "label": "The Sugar Shack",
    },
    "island_arcade": {
        "db_id": "40ec9f76-abd3-4a68-a23a-13e8a2c90755",
        "label": "Island Arcade",
    },
    "island_candy": {
        "db_id": "d865037b-2552-4024-9db3-10e61e1419b4",
        "label": "Island Candy",
    },
    "spi_fun_rentals": {
        "db_id": "f8693268-6abf-4401-8b2e-3795e326252b",
        "label": "SPI Fun Rentals",
    },
    "juan": {
        "db_id": "a1000001-0000-0000-0000-000000000001",
        "label": "Juan Elizondo RE/MAX Elite",
    },
    "custom_designs_tx": {
        "db_id": "394dba54-161a-46f3-9956-cc8e5dc3fa43",
        "label": "Custom Designs TX",
    },
    "optimum_clinic": {
        "db_id": "a1000002-0000-0000-0000-000000000002",
        "label": "Optimum Care Clinic",
    },
    "optimum_foundation": {
        "db_id": "a1000003-0000-0000-0000-000000000003",
        "label": "Optimum Health & Wellness Foundation",
    },
}

# ─── 40 ADS (5 per client) ──────────────────────────────────────────────────

ADS = [
    # ═══════════════════════════════════════════════════════════════════════════
    # SUGAR SHACK (5 ads) — bright, playful, no faces, no text overlays
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "sugar_shack",
        "name": "Sugar Shack — Candy Paradise",
        "ad_angle": "visual candy overload",
        "copy_headline": "Welcome to Candy Paradise",
        "copy_body": "Rows and rows of bulk candy bins overflowing with every sweet you dreamed of as a kid. Gummy bears, sour belts, chocolate-covered everything, and flavors you won't find anywhere else on the island.\n\nThe Sugar Shack on South Padre Island is where vacation memories are made — one scoop at a time.\n\nStop by and fill a bag with your favorites today.",
        "copy_cta": "Visit us on South Padre Island!",
        "copy_hashtags": "#SouthPadreIsland #CandyShop #SPILife",
        "image_prompt": "overhead view of colorful bulk candy bins filled with gummy bears, sour belts, jelly beans, chocolate truffles, and lollipops, vibrant rainbow colors, bright natural lighting, candy store display, professional photography, 4k",
    },
    {
        "client": "sugar_shack",
        "name": "Sugar Shack — Road Trip Fuel",
        "ad_angle": "road trip families",
        "copy_headline": "The Sweetest Stop on the Island",
        "copy_body": "Driving down to South Padre? Your road trip isn't complete without a stop at The Sugar Shack.\n\nLet the kids pick their own candy bags while you sneak a few chocolate-covered pretzels for yourself. We won't judge.\n\nOpen daily — right in the heart of SPI.",
        "copy_cta": "Tag someone who needs a candy run!",
        "copy_hashtags": "#SugarShackSPI #CandyLovers #VacationSweets",
        "image_prompt": "colorful candy bags filled with assorted gummy candies, chocolate truffles, and sour candy strips laid out on a bright white surface, festive vacation vibes, overhead shot, bright studio lighting, professional photography, 4k",
    },
    {
        "client": "sugar_shack",
        "name": "Sugar Shack — Nostalgic Candy Jars",
        "ad_angle": "nostalgia",
        "copy_headline": "Remember When Candy Was This Good?",
        "copy_body": "Glass jars filled with the classics. Jawbreakers, rock candy, wax bottles, candy necklaces — the ones you begged your parents for at the corner store.\n\nThey're all here at The Sugar Shack on South Padre Island. Bring the kids and relive the magic.\n\nSome things just never get old.",
        "copy_cta": "Come taste the nostalgia!",
        "copy_hashtags": "#NostalgicCandy #SouthPadreIsland #SugarShack",
        "image_prompt": "vintage glass candy jars filled with colorful jawbreakers, rock candy sticks, gumballs, and ribbon candy, nostalgic candy shop aesthetic, warm golden lighting, shallow depth of field, professional photography, 4k",
    },
    {
        "client": "sugar_shack",
        "name": "Sugar Shack — Spring Break Sweets",
        "ad_angle": "spring break",
        "copy_headline": "Spring Break Just Got Sweeter",
        "copy_body": "Beach by day. Candy by night.\n\nSpring breakers — whether you're 8 or 28 — The Sugar Shack is the spot. Grab a mixed bag of sour gummies, share some chocolate-dipped strawberries with your crew, or challenge your friends to a warhead eating contest.\n\nRight on SPI. Open late.",
        "copy_cta": "Bring your crew to The Sugar Shack!",
        "copy_hashtags": "#SpringBreakSPI #CandyStore #SouthPadre",
        "image_prompt": "close-up of bright colorful sour gummy worms and sour candy belts in neon green, pink, blue, and yellow, sugar-coated texture visible, vibrant tropical candy aesthetic, bright lighting, professional photography, 4k",
    },
    {
        "client": "sugar_shack",
        "name": "Sugar Shack — Weekend Treat",
        "ad_angle": "weekend indulgence",
        "copy_headline": "You Deserve Something Sweet This Weekend",
        "copy_body": "It's been a long week. Treat yourself.\n\nThe Sugar Shack has walls of chocolate, bins of gummies, and jars of every hard candy you can imagine. Whether you're a dark chocolate purist or a sour candy warrior — we've got your fix.\n\nLife's short. Eat the candy.",
        "copy_cta": "Stop by this weekend!",
        "copy_hashtags": "#WeekendVibes #CandyTime #SugarShackSPI",
        "image_prompt": "artful arrangement of premium chocolate truffles, dark chocolate bars, white chocolate pieces, and cocoa powder dusted desserts on a marble surface, luxury candy aesthetic, warm moody lighting, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ISLAND ARCADE (5 ads) — retro arcade game themed, no trademarked characters
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "island_arcade",
        "name": "Island Arcade — Fighter Showdown",
        "ad_angle": "classic fighting games",
        "copy_headline": "Step Into the Ring",
        "copy_body": "Think you've got what it takes? Our classic fighting game cabinets are calling your name.\n\nButton-mash your way to victory, pull off that perfect combo, and prove you're the champion of Island Arcade on South Padre Island.\n\nBring a friend. Things are about to get competitive.",
        "copy_cta": "Challenge accepted? Come play!",
        "copy_hashtags": "#IslandArcade #ArcadeGames #SouthPadreIsland",
        "image_prompt": "retro arcade fighting game cabinet screen glowing with neon blue and red lights, two generic pixel art fighters in combat stance, arcade button controls visible, dark arcade room with colorful neon reflections, cinematic gaming atmosphere, professional photography, 4k",
    },
    {
        "client": "island_arcade",
        "name": "Island Arcade — Space Shooter",
        "ad_angle": "space shooter nostalgia",
        "copy_headline": "Defend the Galaxy. Win the Prizes.",
        "copy_body": "Laser blasts. Alien waves. High scores.\n\nOur space shooter cabinets take you back to the golden age of gaming. Dodge, shoot, and rack up points while the neon lights glow around you.\n\nIsland Arcade on South Padre Island — where every quarter is an adventure.",
        "copy_cta": "How high can you score?",
        "copy_hashtags": "#ArcadeLife #RetroGaming #SPIFun",
        "image_prompt": "retro arcade space shooter game screen with pixel art spaceships, laser beams, and explosions in neon green and purple, classic arcade cabinet in a dark room lit by screen glow, tokens scattered on the control panel, professional photography, 4k",
    },
    {
        "client": "island_arcade",
        "name": "Island Arcade — Ticket Jackpot",
        "ad_angle": "prizes and tickets",
        "copy_headline": "Stack Those Tickets!",
        "copy_body": "The ticket counter is loaded. Stuffed animals, electronics, candy, and toys — all yours if you can rack up enough tickets.\n\nIsland Arcade on South Padre Island has dozens of games that spit out tickets like confetti. Skee-ball, wheel spinners, claw machines, and more.\n\nThe real question: are you saving up for the big prize or cashing in now?",
        "copy_cta": "Come win big this weekend!",
        "copy_hashtags": "#ArcadePrizes #WinBig #IslandArcadeSPI",
        "image_prompt": "pile of golden arcade tokens and cascading prize tickets spilling from a game machine, colorful neon lights reflecting off the tokens, arcade atmosphere with blurred game cabinets in background, vibrant and exciting, professional photography, 4k",
    },
    {
        "client": "island_arcade",
        "name": "Island Arcade — Racing Games",
        "ad_angle": "racing game excitement",
        "copy_headline": "Start Your Engines",
        "copy_body": "Grip the wheel. Floor it.\n\nOur racing game cabinets put you in the driver's seat of high-speed action. Drift around corners, boost past opponents, and cross the finish line first.\n\nIsland Arcade on South Padre — the ultimate rainy day (or any day) hangout for families and thrill-seekers.",
        "copy_cta": "Race you there!",
        "copy_hashtags": "#ArcadeRacing #FamilyFun #SouthPadreIsland",
        "image_prompt": "arcade racing game cabinet with a glowing screen showing a high-speed race track, steering wheel and pedals visible, neon orange and blue lighting, dynamic motion blur on screen, dark arcade environment with colorful ambient lighting, professional photography, 4k",
    },
    {
        "client": "island_arcade",
        "name": "Island Arcade — Retro Pixel Night",
        "ad_angle": "retro gaming night",
        "copy_headline": "Game On, SPI",
        "copy_body": "The glow of the screens. The click of the buttons. The thrill of beating your high score.\n\nIsland Arcade on South Padre Island is a neon-lit escape where old-school gaming meets island vibes. Whether you're into classic beat-em-ups, shooters, or racing — we've got the cabinet for you.\n\nOpen late. Come play.",
        "copy_cta": "See you at the arcade!",
        "copy_hashtags": "#RetroArcade #GameNight #IslandArcade",
        "image_prompt": "row of glowing retro arcade cabinets in a dark room, screens displaying colorful pixel art games, neon pink and blue ambient lighting, reflective floor, classic arcade atmosphere, wide angle shot, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ISLAND CANDY (5 ads) — no serving vessels, no people, no spoons
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "island_candy",
        "name": "Island Candy — Tropical Swirl",
        "ad_angle": "tropical ice cream",
        "copy_headline": "Taste the Island",
        "copy_body": "Mango. Coconut. Passion fruit. Guava.\n\nIsland Candy brings you tropical ice cream flavors inspired by the island itself. Every scoop is a little vacation within your vacation.\n\nLocated inside Island Arcade on South Padre Island. Starting at just $3.99.",
        "copy_cta": "Come taste the tropics!",
        "copy_hashtags": "#IslandCandy #TropicalIceCream #SPITreats",
        "image_prompt": "artistic floating ice cream scoops in mango yellow, coconut white, and passion fruit pink, surrounded by fresh tropical fruits and splashing fruit juice, bright tropical background, vibrant colors, professional photography, 4k",
    },
    {
        "client": "island_candy",
        "name": "Island Candy — Berry Explosion",
        "ad_angle": "berry flavors",
        "copy_headline": "Berry Good. Berry Fresh.",
        "copy_body": "Strawberry. Blueberry. Mixed berry swirl.\n\nOur berry flavors are made with real fruit and taste like summer picked fresh. Sweet, creamy, and impossible to have just one scoop.\n\nIsland Candy inside Island Arcade on SPI. Scoops starting at $3.99.",
        "copy_cta": "Which berry is your favorite?",
        "copy_hashtags": "#BerryIceCream #IslandCandySPI #SweetTooth",
        "image_prompt": "floating ice cream scoops in strawberry red, blueberry purple, and mixed berry pink, surrounded by fresh strawberries, blueberries, and raspberries, juice splashes, bright white background, vibrant and fresh, professional photography, 4k",
    },
    {
        "client": "island_candy",
        "name": "Island Candy — Chocolate Dream",
        "ad_angle": "chocolate indulgence",
        "copy_headline": "Chocolate Lovers, This One's for You",
        "copy_body": "Rich. Creamy. Decadent.\n\nOur chocolate ice cream isn't just chocolate — it's double chocolate, chocolate fudge, cookies and cream, and chocolate peanut butter all in one freezer.\n\nIsland Candy on South Padre Island. Starting at $3.99.",
        "copy_cta": "Come get your chocolate fix!",
        "copy_hashtags": "#ChocolateIceCream #IslandCandy #Dessert",
        "image_prompt": "artistic swirls of rich dark chocolate and milk chocolate ice cream textures, melting chocolate drizzle, cocoa powder dust, chocolate shavings floating, dark indulgent aesthetic with warm lighting, professional photography, 4k",
    },
    {
        "client": "island_candy",
        "name": "Island Candy — Rainbow Scoops",
        "ad_angle": "colorful fun",
        "copy_headline": "Life Is Too Short for Boring Ice Cream",
        "copy_body": "Cotton candy. Birthday cake. Rainbow sherbet. Bubblegum.\n\nIsland Candy has the most colorful, fun, and Instagram-worthy ice cream on the island. Pick your flavor, mix and match, and enjoy the sweetest part of your SPI trip.\n\nStarting at just $3.99. Inside Island Arcade.",
        "copy_cta": "Which color are you picking?",
        "copy_hashtags": "#RainbowIceCream #SPIFun #IslandCandySPI",
        "image_prompt": "vibrant rainbow-colored ice cream scoops floating artistically in cotton candy pink, sky blue, mint green, and sunny yellow, colorful candy sprinkles and sugar crystals suspended in air, bright white background, playful and fun, professional photography, 4k",
    },
    {
        "client": "island_candy",
        "name": "Island Candy — After Beach Treat",
        "ad_angle": "post-beach cooldown",
        "copy_headline": "Sun. Sand. Scoops.",
        "copy_body": "After a long day on the beach, nothing hits like cold, creamy ice cream.\n\nIsland Candy is your after-beach reward. Cool down with a scoop (or three) of our handcrafted flavors. Right inside Island Arcade on South Padre.\n\nScoops starting at $3.99.",
        "copy_cta": "You earned it. Come cool down!",
        "copy_hashtags": "#BeachDay #IceCream #SouthPadreIsland",
        "image_prompt": "creamy vanilla and strawberry ice cream scoops with fresh fruit toppings, surrounded by tropical flowers and palm fronds, soft golden sunset lighting, summer vacation vibes, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # SPI FUN RENTALS (5 ads) — golf carts NEVER on sand, on paved roads only
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "spi_fun_rentals",
        "name": "SPI Fun Rentals — Island Cruiser",
        "ad_angle": "golf cart cruising",
        "copy_headline": "Cruise the Island in Style",
        "copy_body": "Skip the parking hassle. Grab a golf cart and cruise South Padre Island like a local.\n\nOur street-legal golf carts let you zip between restaurants, shops, and beach access points with the ocean breeze in your hair.\n\nSPI Fun Rentals — hourly, daily, and weekly rates available.\n\nCall (956) 761-9999 to book.",
        "copy_cta": "Book your cart today! (956) 761-9999",
        "copy_hashtags": "#SPIFunRentals #GolfCartRentals #SouthPadreIsland",
        "image_prompt": "colorful street-legal golf cart driving on a paved coastal road on South Padre Island, palm trees lining the road, ocean visible in the background behind a seawall, sunny blue sky, tropical vacation vibes, professional photography, 4k",
    },
    {
        "client": "spi_fun_rentals",
        "name": "SPI Fun Rentals — Family Adventure",
        "ad_angle": "family fun",
        "copy_headline": "The Best Way to See the Island",
        "copy_body": "Families love our golf carts. Kids love the open air. Parents love the convenience.\n\nExplore South Padre Island at your own pace — hit the restaurants, check out the shops, and cruise by the water all from the comfort of your own golf cart.\n\nHourly and daily rates. Free delivery.\n\nCall (956) 761-9999 to reserve.",
        "copy_cta": "Reserve now: (956) 761-9999",
        "copy_hashtags": "#FamilyVacation #SPIRentals #IslandLife",
        "image_prompt": "bright colorful golf cart parked on a paved parking lot near a tropical beach boardwalk, palm trees and blue ocean in the background, sunny day, vacation rental aesthetic, no sand under wheels, professional photography, 4k",
    },
    {
        "client": "spi_fun_rentals",
        "name": "SPI Fun Rentals — Jeep Explorer",
        "ad_angle": "Jeep rentals",
        "copy_headline": "Explore SPI in a Jeep",
        "copy_body": "Want more horsepower? Our Jeep rentals let you explore South Padre Island with room for the whole crew and all your gear.\n\nPerfect for island hopping, beach access runs, and sunset cruises down the boulevard.\n\nSPI Fun Rentals — call (956) 761-9999 to book your Jeep today.",
        "copy_cta": "Book a Jeep: (956) 761-9999",
        "copy_hashtags": "#JeepRental #SouthPadre #IslandAdventure",
        "image_prompt": "rugged open-top Jeep Wrangler driving on a paved coastal boulevard on South Padre Island, ocean and palm trees visible in background, golden hour lighting, adventure travel aesthetic, vehicle on asphalt road, professional photography, 4k",
    },
    {
        "client": "spi_fun_rentals",
        "name": "SPI Fun Rentals — Sunset Cruise",
        "ad_angle": "sunset drives",
        "copy_headline": "Catch the Sunset from a Golf Cart",
        "copy_body": "There's no better way to watch a South Padre Island sunset than cruising down the boulevard in a golf cart.\n\nWarm breeze, golden sky, and the sound of the waves — all from the comfort of your rental.\n\nSPI Fun Rentals. Daily and weekly rates.\n\nCall (956) 761-9999.",
        "copy_cta": "Book your sunset ride: (956) 761-9999",
        "copy_hashtags": "#SPISunset #GolfCartLife #SouthPadreIsland",
        "image_prompt": "golf cart parked on a paved ocean-view overlook at sunset on South Padre Island, golden orange sky reflecting on the water, palm tree silhouettes, warm golden hour lighting, romantic vacation vibes, vehicle on concrete surface, professional photography, 4k",
    },
    {
        "client": "spi_fun_rentals",
        "name": "SPI Fun Rentals — Spring Break Fleet",
        "ad_angle": "spring break groups",
        "copy_headline": "Spring Break Fleet Ready to Roll",
        "copy_body": "Squad trip to South Padre? You need wheels.\n\nSPI Fun Rentals has a full fleet of golf carts and Jeeps ready for your spring break crew. Cruise the strip, hit the restaurants, and make it a trip to remember.\n\nGroup rates available. Call (956) 761-9999.",
        "copy_cta": "Reserve for your group: (956) 761-9999",
        "copy_hashtags": "#SpringBreakSPI #GroupRentals #SPIFunRentals",
        "image_prompt": "fleet of three colorful golf carts lined up on a paved parking area with palm trees and tropical landscaping, South Padre Island street scene, bright sunny day, rental fleet ready for customers, vehicles on pavement, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # JUAN ELIZONDO RE/MAX ELITE (5 ads) — RGV homes, bilingual welcome
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "juan",
        "name": "Juan Elizondo — Dream Home RGV",
        "ad_angle": "first-time buyer",
        "copy_headline": "Your Dream Home in the Rio Grande Valley",
        "copy_body": "First time buying a home? The RGV market has incredible opportunities right now — from modern new builds in McAllen to charming family homes in Edinburg and Mission.\n\nJuan Elizondo with RE/MAX Elite will guide you through every step, from pre-approval to closing.\n\nCall (956) 522-1481 for a free consultation.",
        "copy_cta": "Call Juan: (956) 522-1481",
        "copy_hashtags": "#RGVRealEstate #FirstTimeHomeBuyer #REMAXElite",
        "image_prompt": "beautiful modern stucco home exterior in South Texas Rio Grande Valley style, terracotta roof tiles, palm trees in front yard, manicured lawn, warm golden hour lighting, McAllen Texas residential neighborhood, professional real estate photography, 4k",
    },
    {
        "client": "juan",
        "name": "Juan Elizondo — Commercial Investment",
        "ad_angle": "commercial property",
        "copy_headline": "Smart Commercial Investments in the RGV",
        "copy_body": "The Rio Grande Valley is booming. New businesses, growing population, and commercial corridors expanding every year.\n\nWhether you're looking for retail space on 10th Street, warehouse property on Military Highway, or office space in McAllen — Juan Elizondo has the connections and market knowledge to find your next investment.\n\nCall (956) 522-1481.",
        "copy_cta": "Let's talk investment: (956) 522-1481",
        "copy_hashtags": "#CommercialRealEstate #RGVBusiness #McAllenTX",
        "image_prompt": "modern commercial property exterior in Rio Grande Valley Texas, professional office building with glass facade, landscaped parking area, palm trees, clear blue sky, commercial real estate aesthetic, professional photography, 4k",
    },
    {
        "client": "juan",
        "name": "Juan Elizondo — Familia Primero",
        "ad_angle": "bilingual family buyer",
        "copy_headline": "Tu Hogar Te Espera en el Valle",
        "copy_body": "Buscar casa no tiene que ser complicado. Juan Elizondo de RE/MAX Elite te ayuda en cada paso — desde la pre-aprobación hasta las llaves en tu mano.\n\nCon años de experiencia en McAllen, Edinburg, Mission, y todo el Valle del Rio Grande, Juan conoce cada colonia y cada oportunidad.\n\nLlama hoy: (956) 522-1481. Consulta gratis.",
        "copy_cta": "Llama a Juan: (956) 522-1481",
        "copy_hashtags": "#BienesRaicesRGV #TuHogar #REMAXElite",
        "image_prompt": "warm inviting family home in South Texas with stucco walls, red tile roof, colorful bougainvillea flowers, front porch with rocking chairs, palm trees, sunset golden light, Rio Grande Valley residential style, professional photography, 4k",
    },
    {
        "client": "juan",
        "name": "Juan Elizondo — Luxury Living",
        "ad_angle": "luxury properties",
        "copy_headline": "Luxury Living in the Rio Grande Valley",
        "copy_body": "Gated communities. Pool homes. Custom builds with premium finishes.\n\nThe RGV has a luxury market that rivals cities twice its size — and Juan Elizondo knows every listing, every builder, and every neighborhood worth your investment.\n\nFrom Sharyland Plantation to Tres Lagos — your next upgrade starts with a call.\n\n(956) 522-1481",
        "copy_cta": "Explore luxury: (956) 522-1481",
        "copy_hashtags": "#LuxuryHomes #RGVLuxury #REMAXElite",
        "image_prompt": "luxurious modern home with pool in South Texas, contemporary architecture, large windows, outdoor patio with seating, palm trees, twilight blue hour lighting, premium residential real estate, professional photography, 4k",
    },
    {
        "client": "juan",
        "name": "Juan Elizondo — Selling Your Home",
        "ad_angle": "home sellers",
        "copy_headline": "Thinking About Selling? Let's Talk.",
        "copy_body": "The RGV market is moving fast. If you've been thinking about selling your home, now is the time.\n\nJuan Elizondo brings professional marketing, strategic pricing, and a network of qualified buyers to get your home sold quickly and at top dollar.\n\nFree home valuation. Call (956) 522-1481 today.",
        "copy_cta": "Get your free valuation: (956) 522-1481",
        "copy_hashtags": "#SellingYourHome #RGVRealtor #McAllenHomes",
        "image_prompt": "aerial view of a beautiful residential neighborhood in McAllen Texas Rio Grande Valley, rows of stucco homes with tile roofs, palm-lined streets, warm sunset lighting, real estate market overview aesthetic, professional drone photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CUSTOM DESIGNS TX (5 ads) — dark luxury aesthetic, no handyman look
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "custom_designs_tx",
        "name": "Custom Designs — Home Theater",
        "ad_angle": "home theater",
        "copy_headline": "Your Private Cinema. Professionally Installed.",
        "copy_body": "Imagine movie night with a 120-inch screen, Dolby Atmos surround sound, and lighting that dims on cue.\n\nCustom Designs TX builds premium home theaters for homes across McAllen and the Rio Grande Valley. Every wire hidden. Every speaker placed perfectly.\n\nVisit customdesignstx.com to see our work.",
        "copy_cta": "Visit customdesignstx.com",
        "copy_hashtags": "#HomeTheater #CustomDesignsTX #McAllenTX",
        "image_prompt": "luxury home theater room with tiered leather recliners, massive projection screen showing a cinematic scene, Dolby Atmos ceiling speakers, LED ambient lighting in deep blue, all cables hidden, premium dark room aesthetic, professional interior photography, 4k",
    },
    {
        "client": "custom_designs_tx",
        "name": "Custom Designs — Security Cameras",
        "ad_angle": "security camera installation",
        "copy_headline": "See Everything. Miss Nothing.",
        "copy_body": "Professional security camera installation for homes and businesses across Hidalgo and Cameron County.\n\nCustom Designs TX installs 4K camera systems with night vision, motion alerts, and remote viewing from your phone. Clean installation, hidden wiring, and 24/7 peace of mind.\n\nVisit customdesignstx.com for a free quote.",
        "copy_cta": "Get a free quote at customdesignstx.com",
        "copy_hashtags": "#SecurityCameras #HomeSecurityRGV #CustomDesignsTX",
        "image_prompt": "sleek modern security camera mounted on the exterior of a luxury home, clean professional installation with hidden wiring, nighttime shot with the camera's IR illuminator glowing subtly, dark premium aesthetic, gold accent lighting, professional photography, 4k",
    },
    {
        "client": "custom_designs_tx",
        "name": "Custom Designs — Smart Home",
        "ad_angle": "smart home automation",
        "copy_headline": "Your Home, Smarter Than Ever",
        "copy_body": "Lights that respond to your voice. Blinds that open with the sunrise. Music that follows you room to room.\n\nCustom Designs TX integrates smart home systems that are invisible, intuitive, and professionally installed. No exposed wires. No DIY headaches.\n\nServing McAllen, Edinburg, Mission, and all of the RGV.\n\nVisit customdesignstx.com.",
        "copy_cta": "Make your home smart: customdesignstx.com",
        "copy_hashtags": "#SmartHome #HomeAutomation #CustomDesignsTX",
        "image_prompt": "elegant smart home control panel mounted on a dark wall, sleek touchscreen interface glowing with room controls, premium modern interior visible in background, hidden in-ceiling speakers, ambient gold lighting, luxury technology aesthetic, professional photography, 4k",
    },
    {
        "client": "custom_designs_tx",
        "name": "Custom Designs — Audio Systems",
        "ad_angle": "whole-home audio",
        "copy_headline": "Sound That Fills Every Room",
        "copy_body": "In-ceiling speakers. In-wall subwoofers. Outdoor audio zones.\n\nCustom Designs TX installs whole-home audio systems that deliver crystal-clear sound in every room without a single visible speaker or cable.\n\nFrom the kitchen to the patio — your music, your way.\n\nVisit customdesignstx.com.",
        "copy_cta": "Explore audio at customdesignstx.com",
        "copy_hashtags": "#WholeHomeAudio #PremiumSound #CustomDesignsTX",
        "image_prompt": "luxury living room with invisible in-ceiling speakers, subtle speaker grilles flush with the ceiling, premium furniture, dark wood and gold accents, warm ambient lighting, sound waves visualization subtle overlay, high-end interior design, professional photography, 4k",
    },
    {
        "client": "custom_designs_tx",
        "name": "Custom Designs — Commercial Security",
        "ad_angle": "commercial security B2B",
        "copy_headline": "Protect Your Business. Professionally.",
        "copy_body": "Warehouses. Retail stores. Office buildings. Medical clinics.\n\nCustom Designs TX provides commercial-grade security systems with 4K cameras, access control, and 24/7 remote monitoring for businesses across the Rio Grande Valley.\n\nOne call. Full assessment. Professional installation.\n\nVisit customdesignstx.com.",
        "copy_cta": "Business security: customdesignstx.com",
        "copy_hashtags": "#CommercialSecurity #BusinessProtection #CustomDesignsTX",
        "image_prompt": "row of professional 4K security cameras mounted along a modern commercial building exterior, clean installation with conduit hidden, nighttime shot with subtle blue security lighting, commercial property with parking lot visible, premium security aesthetic, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIMUM CARE CLINIC (5 ads) — $75 sick visits, 5-10 PM, no cure claims
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "optimum_clinic",
        "name": "Optimum Clinic — Night Clinic Open",
        "ad_angle": "after-hours care",
        "copy_headline": "Sick After 5 PM? We're Open.",
        "copy_body": "Urgent cares close at 5. ERs cost a fortune. Optimum Care Clinic fills the gap.\n\nWe're open 5 PM to 10 PM every night for sick visits — colds, flu, infections, minor injuries, and more. Walk-ins welcome. No appointment needed.\n\nSick visits starting at $75.\n\nCall (956) 627-3258.",
        "copy_cta": "Walk in tonight: (956) 627-3258",
        "copy_hashtags": "#NightClinic #AfterHoursCare #OptimumCare",
        "image_prompt": "warm inviting medical clinic entrance at dusk with soft interior lighting glowing through windows, modern healthcare facility exterior, clean and welcoming, evening sky visible, professional medical photography, 4k",
    },
    {
        "client": "optimum_clinic",
        "name": "Optimum Clinic — Skip the ER",
        "ad_angle": "ER alternative",
        "copy_headline": "Don't Wait 4 Hours in the ER",
        "copy_body": "For non-emergency sick visits, the ER is expensive and slow. Optimum Care Clinic sees you the same night — no long wait, no surprise bills.\n\nOpen 5 PM to 10 PM nightly. Walk-ins welcome.\n\nSick visits starting at $75. Cash-pay friendly.\n\nCall (956) 627-3258.",
        "copy_cta": "Visit us tonight: (956) 627-3258",
        "copy_hashtags": "#SkipTheER #CashPayClinic #OptimumCare",
        "image_prompt": "nurse in professional scrubs holding a clipboard in a clean modern exam room, warm soft healthcare lighting, stethoscope around neck, welcoming professional expression, close-up interaction shot without showing full clinic interior, professional medical photography, 4k",
    },
    {
        "client": "optimum_clinic",
        "name": "Optimum Clinic — Wound Care",
        "ad_angle": "wound care specialty",
        "copy_headline": "Expert Wound Care — Every Night",
        "copy_body": "Cuts, burns, surgical wound follow-ups, and chronic wound management.\n\nOptimum Care Clinic specializes in regenerative wound care with professional nursing staff trained to help you heal properly.\n\nOpen 5 PM to 10 PM nightly. Walk-ins welcome.\n\nCall (956) 627-3258.",
        "copy_cta": "Wound care specialists: (956) 627-3258",
        "copy_hashtags": "#WoundCare #RegenerativeMedicine #OptimumCare",
        "image_prompt": "close-up of professional medical supplies arranged neatly on a clean white surface, bandages, gauze, antiseptic, medical tape, and gloves, soft warm healthcare lighting, clean and professional, medical still life, professional photography, 4k",
    },
    {
        "client": "optimum_clinic",
        "name": "Optimum Clinic — Parents Night",
        "ad_angle": "sick kids after hours",
        "copy_headline": "Kid Sick Tonight? We Can Help.",
        "copy_body": "When your child gets sick after the pediatrician closes, you don't have to rush to the ER.\n\nOptimum Care Clinic is open 5 PM to 10 PM every night. Fever, ear infections, sore throats, rashes — we see kids and adults.\n\nSick visits starting at $75. Walk-ins welcome.\n\nCall (956) 627-3258.",
        "copy_cta": "Bring them in tonight: (956) 627-3258",
        "copy_hashtags": "#SickKids #NightClinic #ParentLife",
        "image_prompt": "warm comforting medical scene with a stethoscope and small teddy bear on a clean exam table, soft warm lighting, pediatric care aesthetic, close-up detail shot without showing full clinic, gentle and reassuring mood, professional photography, 4k",
    },
    {
        "client": "optimum_clinic",
        "name": "Optimum Clinic — Cash Pay Friendly",
        "ad_angle": "no insurance needed",
        "copy_headline": "No Insurance? No Problem.",
        "copy_body": "Healthcare shouldn't break the bank. Optimum Care Clinic is cash-pay friendly with transparent pricing and no surprise bills.\n\nSick visits starting at $75. Open 5 PM to 10 PM nightly. Walk-ins welcome.\n\nQuality care at a price you can afford.\n\nCall (956) 627-3258.",
        "copy_cta": "Affordable care: (956) 627-3258",
        "copy_hashtags": "#CashPayHealthcare #AffordableCare #OptimumCare",
        "image_prompt": "medical professional hand writing on a clean modern clipboard, healthcare documents visible, stethoscope on table, clean white and blue medical office aesthetic, close-up hands and desk shot, warm professional lighting, professional photography, 4k",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIMUM FOUNDATION (5 ads) — nonprofit, community, no medical imagery
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "client": "optimum_foundation",
        "name": "Optimum Foundation — Community Health",
        "ad_angle": "community wellness",
        "copy_headline": "Building a Healthier Rio Grande Valley",
        "copy_body": "The Optimum Health & Wellness Foundation is on a mission to bring free health education, wellness workshops, and community outreach to underserved neighborhoods across the RGV.\n\nFrom health screenings to nutrition classes — we believe everyone deserves access to wellness.\n\nLearn how you can help. Donate. Volunteer. Share.",
        "copy_cta": "Get involved today!",
        "copy_hashtags": "#RGVCommunity #HealthForAll #OptimumFoundation",
        "image_prompt": "community gathering in a South Texas park with volunteers setting up tables and tents for a health fair, warm sunrise lighting, diverse group of people, hopeful and positive atmosphere, outdoor community event, professional photography, 4k",
    },
    {
        "client": "optimum_foundation",
        "name": "Optimum Foundation — Volunteer",
        "ad_angle": "volunteer recruitment",
        "copy_headline": "Your Time Can Change a Life",
        "copy_body": "The Optimum Health & Wellness Foundation needs volunteers. Whether you can give an hour or a whole Saturday, your time makes a difference in the Rio Grande Valley.\n\nHelp us run community health events, mentor families, and build a healthier neighborhood.\n\nSign up to volunteer today.",
        "copy_cta": "Volunteer with us!",
        "copy_hashtags": "#VolunteerRGV #GiveBack #OptimumFoundation",
        "image_prompt": "group of volunteers in matching t-shirts organizing supplies at an outdoor community event in South Texas, warm morning sunlight, palm trees in background, smiling and working together, community spirit, professional photography, 4k",
    },
    {
        "client": "optimum_foundation",
        "name": "Optimum Foundation — Donate",
        "ad_angle": "donation drive",
        "copy_headline": "Every Dollar Builds a Healthier Community",
        "copy_body": "Your donation to the Optimum Health & Wellness Foundation goes directly to free health education, community wellness programs, and outreach in the Rio Grande Valley.\n\n$25 provides supplies for a wellness workshop.\n$50 sponsors a family health screening.\n$100 funds a full community outreach event.\n\nEvery contribution matters.",
        "copy_cta": "Donate today!",
        "copy_hashtags": "#DonateNow #CommunityHealth #OptimumFoundation",
        "image_prompt": "symbolic image of open hands reaching toward a sunrise over a South Texas landscape, hopeful and warm golden light, community spirit, abstract and inspiring, no medical imagery, professional photography, 4k",
    },
    {
        "client": "optimum_foundation",
        "name": "Optimum Foundation — Education",
        "ad_angle": "health education",
        "copy_headline": "Knowledge Is the First Step to Wellness",
        "copy_body": "The Optimum Health & Wellness Foundation hosts free health education workshops across the RGV.\n\nNutrition basics. Diabetes prevention. Heart health. Mental wellness.\n\nBecause understanding your body is the first step to taking care of it.\n\nAll workshops are free and open to the community.",
        "copy_cta": "Join our next workshop!",
        "copy_hashtags": "#HealthEducation #FreeWorkshops #OptimumFoundation",
        "image_prompt": "outdoor community workshop setup in a South Texas neighborhood park, folding chairs arranged in a semicircle under shade trees, welcome banner, educational materials on a table, warm inviting morning light, community education event, professional photography, 4k",
    },
    {
        "client": "optimum_foundation",
        "name": "Optimum Foundation — Together Stronger",
        "ad_angle": "community solidarity",
        "copy_headline": "Together, We're Stronger",
        "copy_body": "The Rio Grande Valley is a community that looks out for each other. The Optimum Health & Wellness Foundation is here to make sure no family falls through the cracks.\n\nFree wellness resources. Community events. Health education for all ages.\n\nJoin us in building something bigger than ourselves.",
        "copy_cta": "Stand with us!",
        "copy_hashtags": "#RGVStrong #CommunityFirst #OptimumFoundation",
        "image_prompt": "beautiful sunrise over South Texas Rio Grande Valley landscape, wide open sky with golden and pink clouds, palm tree silhouettes, hopeful and inspiring vista, community and nature, warm uplifting mood, professional landscape photography, 4k",
    },
]

# ─── FAL.AI IMAGE GENERATION ────────────────────────────────────────────────

def generate_image(prompt: str, retries: int = 2) -> str | None:
    """Generate an image via fal.ai Flux Pro. Returns the image URL."""
    import requests

    endpoint = "https://fal.run/fal-ai/flux-pro"
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
        "output_format": "png",
    }

    for attempt in range(retries + 1):
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200:
                images = resp.json().get("images", [])
                if images:
                    return images[0].get("url")
            print(f"    ⚠️ fal.ai {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            print(f"    ⚠️ fal.ai error: {e}")
        if attempt < retries:
            time.sleep(3)
    return None


# ─── SUPABASE INSERT ────────────────────────────────────────────────────────

def insert_ads_to_supabase(entries: list[dict]) -> int:
    """Insert ads directly into Supabase ad_creatives table. Returns count inserted."""
    import requests

    url = f"{SUPABASE_URL}/rest/v1/ad_creatives"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    resp = requests.post(url, headers=headers, json=entries, timeout=30)
    if resp.status_code in (200, 201):
        data = resp.json()
        return len(data) if isinstance(data, list) else 1
    else:
        print(f"  ❌ Supabase insert failed: {resp.status_code} {resp.text[:300]}")
        return 0


# ─── TELEGRAM NOTIFY ────────────────────────────────────────────────────────

def notify_mario(text: str) -> bool:
    token = ENV.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = ENV.get("TELEGRAM_USER_ID", "")
    if not token or not chat_id:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("\n🎨 Weekend Ad Batch — 40 Ads (5 per client x 8 clients)\n")
    print(f"  Supabase: {SUPABASE_URL[:40]}...")
    print(f"  FAL Key:  {FAL_KEY[:15]}...")

    if not FAL_KEY:
        print("❌ FAL_KEY not found"); sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Supabase credentials not found"); sys.exit(1)

    # Check for requests
    try:
        import requests
    except ImportError:
        print("❌ requests not installed. Run: pip install requests")
        sys.exit(1)

    total = len(ADS)
    generated = 0
    failed_images = []
    supabase_entries = []

    campaign_id = f"weekend-batch-{time.strftime('%Y%m%d')}"

    for i, ad in enumerate(ADS, 1):
        client_key = ad["client"]
        client_info = CLIENTS[client_key]
        client_db_id = client_info["db_id"]

        print(f"\n  [{i}/{total}] {ad['name']}")
        print(f"    Client: {client_info['label']}")
        print(f"    Angle:  {ad['ad_angle']}")

        # Generate image
        print(f"    🎨 Generating image...")
        image_url = generate_image(ad["image_prompt"])

        if image_url:
            print(f"    ✅ Image ready")
            generated += 1
        else:
            print(f"    ❌ Image failed — will create ad without image")
            failed_images.append(ad["name"])

        # Build Supabase row
        entry = {
            "owner_id": "00000000-0000-0000-0000-000000000000",
            "client_id": client_db_id,
            "campaign_id": None,
            "name": ad["name"],
            "fal_url": image_url,
            "storage_url": None,
            "media_type": "image",
            "size_mb": None,
            "copy_headline": ad.get("copy_headline"),
            "copy_body": ad.get("copy_body"),
            "copy_cta": ad.get("copy_cta"),
            "copy_features": None,
            "copy_hashtags": ad.get("copy_hashtags"),
            "ad_angle": ad.get("ad_angle"),
            "status": "draft",
            "rating": 0,
            "notes": f"Weekend batch {time.strftime('%Y-%m-%d')} — review in Mission Control",
            "generation_model": "fal-ai/flux-pro",
            "generation_prompt": ad["image_prompt"],
            "platform": "facebook",
            "scheduled_date": None,
            "posted_at": None,
        }
        supabase_entries.append(entry)

        # Small delay between API calls
        if i < total:
            time.sleep(1)

    # Insert all into Supabase in batches of 10
    print(f"\n\n📌 Inserting {len(supabase_entries)} ads into Mission Control...")
    inserted = 0
    batch_size = 10
    for i in range(0, len(supabase_entries), batch_size):
        batch = supabase_entries[i:i + batch_size]
        count = insert_ads_to_supabase(batch)
        inserted += count
        print(f"    Batch {i // batch_size + 1}: {count} ads inserted")

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ DONE!")
    print(f"   Total ads:       {total}")
    print(f"   Images generated: {generated}")
    print(f"   Images failed:    {len(failed_images)}")
    print(f"   Inserted to MC:   {inserted}")
    print(f"   Est. cost:        ${generated * 0.05:.2f} (Flux Pro)")
    print(f"{'='*60}")

    if failed_images:
        print(f"\n  ⚠️ Failed images:")
        for name in failed_images:
            print(f"    - {name}")

    # Notify Mario
    msg = (
        f"🎨 Weekend Ad Batch Complete!\n\n"
        f"✅ {inserted} ads loaded into Mission Control\n"
        f"📸 {generated}/{total} images generated\n"
        f"💰 Est. cost: ${generated * 0.05:.2f}\n\n"
        f"Clients: Sugar Shack, Island Arcade, Island Candy, SPI Fun Rentals, "
        f"Juan Elizondo, Custom Designs TX, Optimum Clinic, Optimum Foundation\n\n"
        f"👉 Open Mission Control → Ad Creative Library to review.\n"
        f"All ads are in DRAFT status — approve or reject each one."
    )
    if notify_mario(msg):
        print(f"\n  📱 Telegram notification sent to Mario")
    else:
        print(f"\n  ⚠️ Telegram notification failed")


if __name__ == "__main__":
    main()
