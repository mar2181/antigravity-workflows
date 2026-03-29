# CLAW Bridge Instructions

> **Purpose:** Push generated content from Genspark CLAW cloud computer to Mario's local machine via Supabase.
> **Table:** `claw_pending_items` in Supabase project `svgsbaahxiaeljmfykzp`

---

## For CLAW (paste this into your CLAW workspace)

### Quick Push — Copy this function into any CLAW script

```python
import json, urllib.parse, urllib.request

SUPABASE_URL = "https://svgsbaahxiaeljmfykzp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN2Z3NiYWFoeGlhZWxqbWZ5a3pwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEyODc2ODksImV4cCI6MjA1Njg2MzY4OX0.S80GrL92vr2F-dwzWZqaz3Gt8RgttRi8ccC9y6sRQfI"

def push_to_mario(item_type, client_key, title, content="", metadata=None):
    """Push a pending item for Mario's approval.

    item_type: 'review_response' | 'ad_copy' | 'blog_draft' | 'image' | 'social_post'
    client_key: 'sugar_shack' | 'island_arcade' | 'island_candy' | 'juan' |
                'spi_fun_rentals' | 'custom_designs_tx' | 'optimum_clinic' | 'optimum_foundation'
    title: short summary (shown in approval list)
    content: full text content
    metadata: dict with extra info (optional)
    """
    body = json.dumps({
        "item_type": item_type,
        "client_key": client_key,
        "title": title,
        "content": content,
        "metadata": json.dumps(metadata or {}),
        "source": "claw",
        "status": "pending",
    }).encode()

    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/claw_pending_items",
        data=body,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())
```

### Example Pushes

```python
# Review response
push_to_mario(
    "review_response", "sugar_shack",
    "Reply to 5-star review from Sarah M.",
    "Thank you so much Sarah! We're so glad you loved our homemade fudge.",
    {"review_rating": 5, "platform": "google", "reviewer": "Sarah M."}
)

# Ad copy
push_to_mario(
    "ad_copy", "island_arcade",
    "Spring Break Family Fun angle",
    "Spring Break is HERE and Island Arcade is the place to be! Bring the whole family...",
    {"angle": "spring_break_family", "hashtags": ["#SPIFun", "#SpringBreak"]}
)

# Blog draft
push_to_mario(
    "blog_draft", "custom_designs_tx",
    "5 Signs Your Security Camera System Needs an Upgrade",
    "Full blog text goes here...",
    {"keyword": "security camera upgrade mcallen", "word_count": 850}
)

# Social post
push_to_mario(
    "social_post", "optimum_clinic",
    "Night clinic open 6PM-10PM tonight",
    "Feeling sick tonight? Skip the ER wait. Optimum Health is open until 10PM...",
    {"channel": "facebook", "schedule": "2026-03-25T18:00:00"}
)
```

### Batch Push — Push all pending review responses at once

```python
import os, json

review_dir = "/home/work/.openclaw/workspace/automation/review_response/"
for filename in os.listdir(review_dir):
    if filename.endswith(".json"):
        with open(os.path.join(review_dir, filename)) as f:
            data = json.load(f)
        push_to_mario(
            "review_response",
            data.get("client_key", "unknown"),
            f"Reply to {data.get('reviewer', 'unknown')} ({data.get('rating', '?')} stars)",
            data.get("response_text", ""),
            {"reviewer": data.get("reviewer"), "rating": data.get("rating"), "file": filename}
        )
        print(f"Pushed: {filename}")
```

---

## For Mario's Local Machine

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# See all pending items
python claw_bridge.py

# Quick count (used by morning brief)
python claw_bridge.py --count

# Approve or reject
python claw_bridge.py --approve 5
python claw_bridge.py --reject 5 --notes "wrong tone"

# Approve all from a client
python claw_bridge.py --approve-all --client sugar_shack

# Export approved items to local files
python claw_bridge.py --export

# Send pending count to Telegram
python claw_bridge.py --count --telegram
```

---

## Table Schema

| Column | Type | Description |
|---|---|---|
| id | BIGSERIAL | Auto-increment primary key |
| item_type | TEXT | review_response, ad_copy, blog_draft, image, social_post |
| client_key | TEXT | sugar_shack, island_arcade, juan, etc. |
| title | TEXT | Short summary shown in approval list |
| content | TEXT | Full content body |
| metadata | JSONB | Extra structured data (ratings, angles, keywords) |
| status | TEXT | pending, approved, rejected, posted |
| source | TEXT | claw, manual, automation |
| created_at | TIMESTAMPTZ | Auto-set on insert |
| reviewed_at | TIMESTAMPTZ | Set when approved/rejected |
| notes | TEXT | Mario's review notes |
