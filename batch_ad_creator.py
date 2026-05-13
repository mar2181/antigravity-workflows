#!/usr/bin/env python3
"""
Batch Ad Creator — Generate 1 hero ad per client
Includes image generation, ad copy, and preview HTML
"""

import json
from pathlib import Path
from datetime import datetime

# Ad specifications for each client
CLIENTS_ADS = {
    "sugar_shack": {
        "business_name": "The Sugar Shack",
        "location": "South Padre Island, TX",
        "angle": "Road Trip Fuel",
        "image_prompt": "Colorful candy store display with bright gummies, chocolates, and bulk candy bins, vibrant shelves overflowing with sweets, warm daylight through store windows, inviting entrance, family-friendly confectionery, professional photography, 4k",
        "copy": """Your road trip just got sweeter.

The Sugar Shack is your perfect stop between destinations. Fill a bag with your favorites—gummies, chocolates, bulk candy, and snacks that make the drive unforgettable.

Come see us on South Padre Island. Your sweet tooth will thank you. 🍬

#SweetStop #RoadTripFood #SouthPadreIsland""",
        "offer": "Fill a bag with your favorites",
        "cta": "Stop by today",
        "colors": {"bg": "#FFF5E6", "accent": "#FF6B9D"}
    },

    "island_arcade": {
        "business_name": "Island Arcade",
        "location": "South Padre Island, TX",
        "angle": "Rainy Day Escape",
        "image_prompt": "Vibrant arcade game cabinets with glowing neon screens, colorful light trails, arcade tokens on a counter, excited gaming atmosphere, VR headsets visible, neon signage reflecting, professional photography, 4k",
        "copy": """Rainy day? We've got you covered.

Spring break plans falling through? Island Arcade is your answer. VR games, classic arcade cabinets, prizes, and unlimited fun—all under one roof.

Walk in today. No reservations needed. Just pure arcade fun.

#IslandArcade #SPI #RainyDayFun""",
        "offer": "50 tokens for $10 this week",
        "cta": "Come play now",
        "colors": {"bg": "#1A1A1A", "accent": "#00FF9F"}
    },

    "island_candy": {
        "business_name": "Island Candy",
        "location": "South Padre Island, TX",
        "angle": "Cool Down From the Heat",
        "image_prompt": "Creamy homemade ice cream scoops in colorful flavors, melting perfectly, banana split with whipped cream and toppings, beach backdrop golden hour lighting, cold condensation on glass, tropical summer aesthetic, professional photography, 4k",
        "copy": """Been on the beach all day? Time to cool down.

Island Candy inside Island Arcade has homemade ice cream made fresh, starting at $3.99. Walk off the sand and into our sweetest spot.

Scoops, shakes, treats—everything you need to beat the SPI heat.

#IslandCandy #IceCream #SPI""",
        "offer": "Homemade ice cream starting at $3.99",
        "cta": "Walk in today",
        "colors": {"bg": "#FFF0F5", "accent": "#FF69B4"}
    },

    "juan": {
        "business_name": "Juan José Elizondo — RE/MAX Elite",
        "location": "Rio Grande Valley, TX",
        "angle": "Market Knowledge + Community Trust",
        "image_prompt": "Modern Texas home with warm sunset lighting, professional real estate photography, landscaped front, welcoming entrance, morning light, premium residential, professional photography, 4k",
        "copy": """The RGV real estate market is moving. Here's what you need to know.

Spring brings opportunity—whether you're buying, selling, or investing. Juan José Elizondo, RE/MAX Elite, knows the RGV market inside and out. Residential, commercial, investment properties—we help families and businesses find their perfect fit.

Ready to talk about your next move? Let's connect.

📞 (956) 522-1481

#RealEstate #McAllen #RGV""",
        "offer": "Free market consultation",
        "cta": "Call today",
        "colors": {"bg": "#FFF8DC", "accent": "#DAA520"}
    },

    "spi_fun_rentals": {
        "business_name": "SPI Fun Rentals",
        "location": "South Padre Island, TX",
        "angle": "Your Vacation Starts Here",
        "image_prompt": "Group of friends in colorful golf carts on sunny SPI street, smiling, palm trees, beach road, convertible tops down, happy vacation energy, professional photography, 4k",
        "copy": """Your vacation starts the moment you rent from us.

Spring break isn't complete without a golf cart. Six-seater families, couples, groups—we've got the perfect ride for your SPI adventure. Reserve now before peak weekends sell out.

📞 (956) 761-9999
www.spifunrentals.com

#GolfCartLife #SpringBreak #SPI""",
        "offer": "Spring break golf carts—book now",
        "cta": "Reserve your cart today",
        "colors": {"bg": "#E0FFFF", "accent": "#00CED1"}
    },

    "custom_designs_tx": {
        "business_name": "Custom Designs TX",
        "location": "McAllen & Houston, TX",
        "angle": "Dark Luxury Home Theater",
        "image_prompt": "Premium home theater room with gold accents, dramatic backlighting, high-end projection screen, luxury cinema seating, warm ambiance, professional audio equipment visible, dark luxury aesthetic, professional photography, 4k",
        "copy": """Transform your home into something extraordinary.

Custom Designs TX creates premium experiences—home theaters, smart home automation, security systems, audio integration. We don't just install—we transform spaces into luxury environments.

Experience the difference professional design makes.

📞 (956) 624-2463

#HomeTheater #SmartHome #Luxury""",
        "offer": "Free smart home assessment this month",
        "cta": "Schedule consultation",
        "colors": {"bg": "#0A0A0C", "accent": "#D4AF37"}
    },

    "optimum_clinic": {
        "business_name": "Optimum Health & Wellness Clinic",
        "location": "Pharr, TX",
        "angle": "After-Hours Care When You Need It",
        "image_prompt": "Modern, welcoming medical clinic interior, warm lighting, friendly staff interaction, patient comfort focus, clean professional environment, bilingual signage visible, professional photography, 4k",
        "copy": """Open tonight. Walk in right now.

Kids get sick at 8 PM? Your back goes out on Saturday? Optimum Clinic stays open 5–10 PM every single day. No appointment needed. No insurance required.

Sick visit starts at just $75. Cash or card. Bilingual care. Real people helping neighbors.

📞 (956) 627-3258
3912 N Jackson Rd, Pharr

#AftterHoursCare #Pharr #RGV""",
        "offer": "Sick visits starting at $75",
        "cta": "Walk in tonight",
        "colors": {"bg": "#F5F5F5", "accent": "#0066CC"}
    },

    "optimum_foundation": {
        "business_name": "Optimum Health and Wellness Foundation",
        "location": "Rio Grande Valley",
        "angle": "Community Health Matters",
        "image_prompt": "Diverse RGV families in community gathering, warm community center lighting, bilingual health education, hopeful atmosphere, neighbors helping neighbors, warm tones, professional photography, 4k",
        "copy": """Your neighbors deserve healthcare access. Help us build it.

28,000 RGV residents go without insurance. The Optimum Health and Wellness Foundation is here to close that gap—health education, free screenings, and care access for families who need it most.

Your donation changes a life. Your time changes a community.

Learn more. Donate. Volunteer.

#CommunityHealth #RGV #HealthAccess""",
        "offer": "Every donation funds real care",
        "cta": "Donate now / Volunteer",
        "colors": {"bg": "#F0F8FF", "accent": "#228B22"}
    }
}


def generate_preview_html(client_key: str, client_data: dict) -> str:
    """Generate Facebook-style preview HTML for the ad."""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ad Preview - {client_data['business_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: #f0f2f5;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}

        .container {{
            max-width: 550px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            overflow: hidden;
        }}

        .header {{
            padding: 12px 16px;
            background: #f0f2f5;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: {client_data['colors']['accent']};
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }}

        .header-text {{
            display: flex;
            flex-direction: column;
        }}

        .business-name {{
            font-weight: 600;
            font-size: 14px;
            color: #050505;
        }}

        .location {{
            font-size: 12px;
            color: #65676b;
        }}

        .image {{
            width: 100%;
            aspect-ratio: 16 / 9;
            background: linear-gradient(135deg, {client_data['colors']['bg']} 0%, {client_data['colors']['accent']} 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 14px;
            text-align: center;
            padding: 40px;
        }}

        .content {{
            padding: 16px;
        }}

        .angle {{
            font-size: 13px;
            color: #65676b;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .copy {{
            font-size: 15px;
            line-height: 1.5;
            color: #050505;
            margin-bottom: 12px;
            white-space: pre-wrap;
        }}

        .hashtags {{
            font-size: 14px;
            color: #0a66c2;
            margin-bottom: 16px;
        }}

        .offer-box {{
            background: {client_data['colors']['bg']};
            border-left: 4px solid {client_data['colors']['accent']};
            padding: 12px;
            border-radius: 4px;
            margin: 12px 0;
            font-size: 14px;
            font-weight: 600;
            color: #050505;
        }}

        .cta-button {{
            display: block;
            width: 100%;
            padding: 12px;
            background: {client_data['colors']['accent']};
            color: white;
            text-align: center;
            border: none;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            margin-top: 12px;
            transition: opacity 0.2s;
        }}

        .cta-button:hover {{
            opacity: 0.9;
        }}

        .footer {{
            padding: 12px 16px;
            background: #f0f2f5;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #65676b;
        }}

        .metadata {{
            margin-top: 20px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="avatar">{client_data['business_name'][0]}</div>
            <div class="header-text">
                <div class="business-name">{client_data['business_name']}</div>
                <div class="location">{client_data['location']}</div>
            </div>
        </div>

        <div class="image">
            [Image: {client_data['angle']} Ad]
        </div>

        <div class="content">
            <div class="angle">📍 {client_data['angle'].upper()}</div>
            <div class="copy">{client_data['copy']}</div>
            <div class="offer-box">💰 {client_data['offer']}</div>
            <button class="cta-button">{client_data['cta']}</button>
        </div>

        <div class="footer">
            Sponsored | Learn more
        </div>
    </div>

    <div class="metadata">
        <strong>Ad Details:</strong><br>
        Client: {client_key}<br>
        Angle: {client_data['angle']}<br>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        <br>
        <strong>Next Steps:</strong><br>
        1. Review preview (this page)<br>
        2. Generate image (fal.ai)<br>
        3. Get approval<br>
        4. Post to GBP + Facebook
    </div>
</body>
</html>"""

    return html


def main():
    """Generate all ad previews."""

    output_dir = Path("C:/Users/mario/ad_previews_2026_04_28")
    output_dir.mkdir(exist_ok=True)

    preview_links = []

    for client_key, client_data in CLIENTS_ADS.items():
        # Generate preview HTML
        html_content = generate_preview_html(client_key, client_data)

        # Save to file
        html_path = output_dir / f"preview_{client_key}.html"
        html_path.write_text(html_content, encoding='utf-8')

        preview_links.append({
            "client": client_key,
            "business": client_data["business_name"],
            "angle": client_data["angle"],
            "preview_path": str(html_path),
            "image_prompt": client_data["image_prompt"],
            "copy": client_data["copy"]
        })

        print(f"[OK] {client_key}: {client_data['angle']}")

    # Save manifest
    manifest_path = output_dir / "ad_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(preview_links, f, indent=2, ensure_ascii=False)

    print(f"\n[DIR] All previews saved to: {output_dir}")
    print(f"[JSON] Manifest: {manifest_path}")

    # Print links for user
    print("\n" + "="*70)
    print("PREVIEW LINKS — Click to view each ad")
    print("="*70)
    for link in preview_links:
        print(f"\n{link['business']}")
        print(f"  Angle: {link['angle']}")
        print(f"  Preview: file:///{link['preview_path']}")

    return preview_links


if __name__ == "__main__":
    preview_links = main()
