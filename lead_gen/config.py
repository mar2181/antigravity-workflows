"""
Lead Gen — No-Website Business Finder
Configuration: categories, cities, scoring, output.
"""

# ── RGV Cities ──────────────────────────────────────────────────────────────────
CITIES = [
    "McAllen",
    "Edinburg",
    "Mission",
    "Harlingen",
    "Brownsville",
    "Pharr",
    "Weslaco",
    "San Benito",
    "Donna",
    "Alamo",
    "Mercedes",
    "Los Fresnos",
    "Hidalgo",
    "Rio Grande City",
    "Port Isabel",
    "South Padre Island",
]

# ── Business Categories (high-value, website-dependent) ─────────────────────────
CATEGORIES = [
    # Medical
    "dentist",
    "orthodontist",
    "cosmetic dentist",
    "chiropractor",
    "physical therapist",
    "optometrist",
    "veterinarian",
    "urgent care",
    "dermatologist",
    # Legal
    "personal injury lawyer",
    "divorce attorney",
    "immigration lawyer",
    "criminal defense attorney",
    # Home Services
    "plumber",
    "electrician",
    "hvac contractor",
    "roofing contractor",
    "landscaping",
    "general contractor",
    "home remodeler",
    # Auto
    "auto repair shop",
    "auto body shop",
    # Beauty / Wellness
    "hair salon",
    "nail salon",
    "day spa",
    "massage therapist",
    # Professional Services
    "accountant",
    "insurance agent",
    "real estate agent",
    # Food / Hospitality
    "restaurant",
    "catering",
    # Fitness
    "gym",
    "personal trainer",
    "martial arts",
    # Other
    "cleaning service",
    "moving company",
    "photographer",
    "event planner",
    "towing service",
    "pest control",
    "pool contractor",
]

# ── Scoring ─────────────────────────────────────────────────────────────────────
SCORING = {
    # Base score by rank position (0-indexed within a single search)
    "rank_score": {0: 30, 1: 25, 2: 20},
    # Review count multipliers
    "reviews_bonus": [
        (5, 5),     # 5+ reviews → +5
        (20, 10),   # 20+ reviews → +10
        (50, 15),   # 50+ reviews → +15
        (100, 20),  # 100+ reviews → +20
        (200, 25),  # 200+ reviews → +25
    ],
    # Penalty for using Facebook/Instagram as website
    "social_website_penalty": 5,  # still a lead but slightly lower priority
    # Minimum score to include in output
    "min_score": 10,
}

# ── Query Variations (multiplied by each category × city) ───────────────────────
# Using multiple queries per category catches different businesses in each 3-pack.
# More variations = broader coverage = more likely to find businesses ranked 4-10.
QUERY_TEMPLATES = [
    "{} in {} tx",                    # generic: top 3 overall
    "best {} in {} texas",            # quality intent: different ranking signal
    "top rated {} near {} tx",        # proximity: different set
]

# Reduced from 6 to 3 for speed. Add more for deeper coverage.

# ── Neighborhood-level queries for larger cities ───────────────────────────────
# These surface businesses that don't appear in city-wide top 3 searches.
# Only used when --deep flag is passed (adds significant API calls).
NEIGHBORHOOD_QUERIES = [
    "{} near {{}} in {{}} tx",       # e.g. "dentist near Trenton Rd in McAllen tx"
    "{} {{}} area {{}} tx",          # e.g. "dentist Nolana area McAllen tx"
]

# Major roads / neighborhoods per city (for --deep mode)
CITY_NEIGHBORHOODS = {
    "McAllen": ["N 10th St", "Nolana Ave", "Ware Rd", "Trenton Rd", "N McColl Rd", "downtown"],
    "Edinburg": ["University Dr", "N Closner Blvd", "Freddy Gonzalez Dr", "downtown"],
    "Mission": ["Conway Ave", "Sharyland", "Bryan Rd", "downtown"],
    "Harlingen": ["Harrison Ave", "Dixieland Rd", "downtown"],
    "Brownsville": ["Boca Chica Blvd", "Paredes Line Rd", "Alton Gloor Blvd", "downtown"],
    "Pharr": ["Jackson Rd", "Cage Blvd", "downtown"],
}

# ── Output ──────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
MAX_RESULTS_PER_SEARCH = 20  # more variations = broader coverage
BRIGHT_DATA_DELAY = 0.5      # seconds between API calls
