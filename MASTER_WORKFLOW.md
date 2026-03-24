# ANTIGRAVITY DIGITAL — MASTER WORKFLOW REFERENCE
> **Every new Claude session should read this file first.**
> Location: `C:/Users/mario/.gemini/antigravity/tools/execution/MASTER_WORKFLOW.md`
> Last updated: 2026-03-23

---

## MORNING START SEQUENCE (Every Session)

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# 1. Kill any stale Chrome processes + clear locks
powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"
rm -f facebook_sniffer_profile/SingletonLock facebook_mario_profile/SingletonLock

# 2. Verify all Facebook sessions are healthy
python fb_health_check.py
# ALL GREEN → proceed   |   ANY RED → see FACEBOOK_SESSION_GUIDE.md

# 3. Read overnight intel (free, instant, no API)
python morning_brief.py --open
```

---

## SYSTEM ARCHITECTURE MAP

```
═══════════════════════════════════════════════════════════════════════
           ANTIGRAVITY DIGITAL — AUTOMATION SYSTEM
           Root: C:/Users/mario/.gemini/antigravity/
═══════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────┐
  │                     THREE PUBLISHING CHANNELS                    │
  ├──────────────────┬───────────────────────┬───────────────────────┤
  │   FACEBOOK       │   GOOGLE BUSINESS     │   WEBSITE / SEO BLOG  │
  │   POSTING        │   PROFILE (GBP)       │   PIPELINE            │
  ├──────────────────┼───────────────────────┼───────────────────────┤
  │ facebook_        │ gbp_post_*.py         │ blog_writer.py        │
  │   marketer.py    │ _gbp_custom_designs   │   ↓                   │
  │ fb_campaign_     │   _with_image.py      │ fal.ai images (4x)    │
  │   runner.py      │ reauth_mario_gbp.py   │   ↓                   │
  │ fb_health_       │                       │ Telegram review       │
  │   check.py       │ Profiles:             │   ↓                   │
  │                  │  gbp_mario_profile/   │ --publish → GBP +     │
  │ Profiles:        │  gbp_sniffer_profile/ │   FB + website push   │
  │  sniffer_profile │                       │                       │
  │  mario_profile   │                       │ Repos:                │
  │                  │                       │  custom_designs_tx →  │
  │                  │                       │  mar2181/custom-designs│
  └──────────────────┴───────────────────────┴───────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   INTELLIGENCE      │
                    │   LAYER             │
                    ├─────────────────────┤
                    │ competitor_monitor  │  overnight scrape
                    │ morning_brief.py    │  daily synthesis
                    │ keyword_rank_tracker│  SEO positions
                    │ engagement_logger   │  ad performance
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   TELEGRAM BOT      │
                    │   notify_mario()    │
                    │   telegram_bot.py   │
                    └─────────────────────┘
```

---

## THE 8 CLIENTS — COMPLETE REFERENCE

| Client Key | Business | Location | Type | FB Auth | FB Page URL | GBP | Website |
|---|---|---|---|---|---|---|---|
| `sugar_shack` | The Sugar Shack | South Padre Island, TX | Retail – candy | **Yehuda** (`facebook_sniffer_profile`) | `profile.php?id=61557735298128` | ✅ Active | — |
| `island_arcade` | Island Arcade | South Padre Island, TX | Entertainment | **Yehuda** (`facebook_sniffer_profile`) | `profile.php?id=100090911360621` | ⚠️ Duplicate | — |
| `island_candy` | Island Candy | Inside Island Arcade, SPI | Retail – ice cream | **Mario** (`facebook_mario_profile`) | `profile.php?id=100090560413893` | ✅ Active (Yehuda `gbp_sniffer_profile`) | — |
| `juan` | Juan Elizondo RE/MAX Elite | Rio Grande Valley, TX | Real estate | **Mario** (`facebook_mario_profile`) | `JuanElizondoRemax/` | ⚠️ Suspended (Mario `gbp_mario_profile`) | juanjoseelizondo.com (Lovable/React — repo TBD) |
| `spi_fun_rentals` | SPI Fun Rentals | South Padre Island, TX | Rentals | **Yehuda** (`facebook_sniffer_profile`) | `spifunrentals` | ⚠️ Duplicate (Mario `gbp_mario_profile`, ID: `12018623800655095562`) | — |
| `custom_designs_tx` | Custom Designs TX | McAllen, TX | Home tech / security | **⚠️ TBD** | **⚠️ Not confirmed** | ✅ Mario (`gbp_mario_profile`, ID: `02979998023027904297`) | customdesignstx.com (Lovable/React, repo: `mar2181/custom-designs`) |
| `optimum_clinic` | Optimum Health & Wellness Clinic | Pharr, TX | Medical – night clinic | **Mario** (`facebook_mario_profile`) | `profile.php?id=61588407637377` | ✅ **VERIFIED** Mario (`gbp_mario_profile`, ID: `16753182239006365635`) | optimumhealthrx.com (Lovable/React — repo TBD) |
| `optimum_foundation` | Optimum H&W Foundation | Pharr, TX | Nonprofit (501c3) | **⚠️ TBD** | **⚠️ PENDING** | — | — |

### Auth Quick Reference

| Account | Email | Chrome Profile | Manages |
|---|---|---|---|
| **Yehuda** | `quepadre@live.com` | `facebook_sniffer_profile/` | Sugar Shack, Island Arcade, SPI Fun Rentals |
| **Mario (FB)** | `marioelizondo81@gmail.com` (phone: 9563937828) | `facebook_mario_profile/` | Island Candy, Juan Elizondo, Optimum Clinic |
| **Mario (GBP)** | same | `gbp_mario_profile/` | Custom Designs TX ✅, Optimum Clinic ✅ (verified `16753182239006365635`), Juan (suspended), SPI Fun Rentals (duplicate) |
| **Yehuda (GBP)** | `quepadre@live.com` | `gbp_sniffer_profile/` | Sugar Shack ✅, Island Candy ✅, Island Arcade (duplicate) |

> ⚠️ **Island Candy uses MARIO's Facebook profile, NOT Yehuda's.** This is the most common mistake.
> ⚠️ **If wrong profile is loaded: fix profile selection, NOT selectors.**

---

## FACEBOOK AD PIPELINE — STEP BY STEP

```
STEP 0 — SESSION HEALTH (every session, no exceptions)
────────────────────────────────────────────────────────
  Kill Chrome + clear locks + python fb_health_check.py
  ALL GREEN → proceed  |  ANY RED → FACEBOOK_SESSION_GUIDE.md

STEP 1 — SKILL LOOKUP (always check first)
────────────────────────────────────────────────────────
  Does a dedicated skill exist for this client?
  → /sugar-shack-facebook, /island-arcade-facebook,
    /island-candy-facebook, /juan-elizondo-remax-elite-facebook,
    /spi-fun-rentals-facebook, /custom-designs-facebook,
    /optimum-clinic-facebook, /optimum-foundation-facebook
  YES → invoke skill and follow it exactly
  NO  → use raw reasoning + /local-biz-facebook-ad-campaign template

STEP 2 — READ CONTEXT BEFORE WRITING
────────────────────────────────────────────────────────
  cat {client}/program.md            ← brand voice, current priorities, posting log
  cat competitor_reports/YYYY-MM-DD.md  ← overnight competitor intel

STEP 3 — GENERATE STRATEGY + COPY (Phase 1)
────────────────────────────────────────────────────────
  - Angles + post copy + fal.ai image prompts
  - Phase 1.5 Validation Gate (HARD RULES):
    ✗ No text overlays in images (ever)
    ✗ No unverified testimonials
    ✗ Max 3 hashtags per post
    ✗ Max 300 words per post
    ✗ SPI Fun Rentals: NO golf carts on sand (illegal)
    ✗ Island Arcade: NO recognizable interior shots
    ✗ Island Candy: NO specific serving vessels (glass bowls, etc.)

STEP 4 — IMAGE GENERATION (Phase 2)
────────────────────────────────────────────────────────
  Model: fal-ai/flux-pro/v1.1-ultra
  Size:  landscape_16_9 (Facebook feed)
  Key:   FAL_KEY in scratch/gravity-claw/.env
  Run:   python fb_campaign_runner.py --business {X} --mode full

STEP 5 — PREVIEW HTML (REQUIRED BEFORE POSTING)
────────────────────────────────────────────────────────
  Generate preview HTML for EACH ad (Facebook-style card + image embedded)
  Serve: python serve.py (port 8000)
  Provide: [Preview Ad #1](file:///C:/...) link
  WAIT for explicit user approval before posting

STEP 6 — POST (Phase 3)
────────────────────────────────────────────────────────
  python facebook_marketer.py \
    --action image --page {page_key} \
    --image {path} --message "{copy}"
  OR: python fb_campaign_runner.py --business {X} --mode post

STEP 7 — LOG RESULTS
────────────────────────────────────────────────────────
  python engagement_logger.py {client}
  Update {client}/program.md → Posting Log section
```

### Facebook Failure Recovery

```
"Composer did not open" error:
  1. Kill Chrome
  2. rm -f facebook_sniffer_profile/SingletonLock
  3. python fb_inspector.py → read fb_buttons.txt
  4. Update _open_composer() selectors in facebook_marketer.py
  Confirmed working selector (2026-03-12):
    div[role='button']:has-text('Create post')

Session expired (login wall):
  Yehuda: python reauth_facebook_sniffer.py → login as quepadre@live.com
  Mario:  python reauth_mario_facebook.py   → login as marioelizondo81@gmail.com
```

---

## GOOGLE BUSINESS PROFILE (GBP) PIPELINE

```
Scripts:
  gbp_post_custom_designs.py          → Custom Designs TX (text only)
  _gbp_custom_designs_with_image.py   → Custom Designs TX + image upload ← USE THIS
  gbp_post_sugar_shack.py             → Sugar Shack
  gbp_morning_check.py                → Daily ratings/review counts

GBP Post Modal Flow (Playwright — how it works):
  1. Navigate: business.google.com/locations
  2. JS evaluate → find business row → click "create post" / "Add update" button
     Fallback: click 3rd icon in the row
  3. Wait for iframe: .../promote/updates/add
  4. Upload image → page.expect_file_chooser() → "Select images and videos"
     Fallback: modal_frame.locator('input[type="file"]').first
  5. Fill textarea (placeholder="Description" or first generic textarea)
  6. Click Post → button:has-text("Post").last
  7. Wait 5s → close browser
     ⚠️ "Copy post" dialog may appear after success — closes with browser, nothing copied

Re-auth (if needed):
  Mario GBP: python reauth_mario_gbp.py  (uses passkey, no password)
```

---

## SEO BLOG PIPELINE — blog_writer.py

```
FULL PIPELINE:
  keyword → triage → competitor scrape → Claude (blog + GBP + FB + 4 image prompts)
  → quality score (Haiku, 4 dimensions × 25 pts) → rewrite if score < 70
  → fal.ai (hero 16:9 + 3 sections square_hd) → save files → Telegram (5 msgs) → approve → publish

CLI COMMANDS:
  python blog_writer.py --client custom_designs_tx --list
  python blog_writer.py --client custom_designs_tx --keyword "security camera installation mcallen tx"
  python blog_writer.py --client custom_designs_tx --keyword "..." --preview
  python blog_writer.py --client custom_designs_tx --keyword "..." --publish
  python blog_writer.py --client custom_designs_tx --keyword "..." --publish --channels gbp,facebook

OUTPUT (in blog_posts/{client}/):
  {date}_{slug}.md                  ← markdown source
  {date}_{slug}.html                ← internal review (score breakdown, dark header)
  {date}_{slug}_PUBLISH.html        ← publication page (self-contained, hero + inline images)
  {date}_{slug}_meta.json           ← metadata + publish status
  {date}_{slug}_GBP_POST.html       ← GBP post preview
  {date}_{slug}_FB_POST.html        ← Facebook post preview
  images/{date}_{slug}/hero.png     ← landscape_16_9
  images/{date}_{slug}/section_1-3.png ← square_hd

TELEGRAM DELIVERY (5 messages per keyword):
  1. _PUBLISH.html as document
  2. GBP post text
  3. Facebook post copy
  4. Hero image (sendPhoto)
  5. Publish command reminder

ACTIVE WEBSITE REPOS:
  custom_designs_tx → mar2181/custom-designs → customdesignstx.com
    Platform: Lovable.dev (React + Vite + TypeScript + Tailwind + shadcn)
    Blog TSX: src/pages/blog/static/{ComponentName}.tsx
    Router:   src/pages/blog/StaticBlogRouter.tsx
    Registry: src/data/staticBlogs.ts
    SPA fix:  vercel.json pushed 2026-03-18 (rewrites all routes → index.html)
    How to add new blog: clone repo → generate TSX → patch router + staticBlogs → commit + push
```

---

## INTELLIGENCE TOOLS

```bash
# ── NIGHTLY PIPELINE (run all 4 scripts in sequence) ──────────────────────────
python nightly_intelligence.py                    # GBP + Ad Library + AI analysis (~8 min)
python nightly_intelligence.py --with-reviews     # + Google review mining (~18 min, run weekly)
python nightly_intelligence.py --headful          # show browser (debug)
python nightly_intelligence.py --business X       # one business only
# Sends Telegram notification when done with link to morning brief

# ── INDIVIDUAL SCRIPTS (if you need to re-run one step) ───────────────────────
# Step 1 — GBP ratings, review counts, hours changes
python competitor_monitor.py                      # all 8 clients
python competitor_monitor.py --business X         # single client
# Output: competitor_reports/YYYY-MM-DD.md + state.json

# Step 2 — Facebook Ad Library (who's spending money, ad copy intel)
python competitor_fb_adlibrary.py                 # all businesses
python competitor_fb_adlibrary.py --business X    # single
# Output: competitor_reports/adlibrary_YYYY-MM-DD.json + .md

# Step 3 — AI analysis (themes, winning content, 3 counter-angles per client)
python competitor_ai_analyzer.py                  # reads latest fb + adlibrary reports
python competitor_ai_analyzer.py --business X     # single
# Output: competitor_reports/ai_analysis_YYYY-MM-DD.json + .md
# Side effect: prints 15 ready-to-run ad_copy_optimizer.py commands

# Step 4 — Google review text mining (run weekly — ~10 min)
python competitor_review_miner.py                 # all businesses
python competitor_review_miner.py --business X    # single
# Output: competitor_reports/reviews_YYYY-MM-DD.json + .md

# Morning brief (synthesizes ALL intel + Screenpipe time breakdown + where-you-left-off)
python morning_brief.py --open
python morning_brief.py --business sugar_shack    # single client

# End-of-day Screenpipe report (time-breakdown + day-recap + top-of-mind + ai-habits)
python screenpipe_pipe_runner.py --daily
python screenpipe_pipe_runner.py --daily --telegram   # with Telegram notification
python screenpipe_pipe_runner.py time-breakdown       # single pipe

# Screenpipe idea scout (competitor intelligence from browsing)
python screenpipe_idea_scout.py                       # last 8 hours
python screenpipe_idea_scout.py --client sugar_shack  # filter to one client

# Ad copy optimizer (any client, any angle)
python ad_copy_optimizer.py sugar_shack --angle "road trip families"
python ad_copy_optimizer.py optimum_clinic --angle "skip the ER"
python ad_copy_optimizer.py optimum_clinic --angle "el medico de la noche" --language es

# Engagement logger (close the feedback loop)
python engagement_logger.py sugar_shack                          # interactive
python engagement_logger.py sugar_shack --analyze               # pattern analysis
python engagement_logger.py sugar_shack --add "angle" --likes 87 --reach 3200

# MLS listing optimizer (Juan only)
python listing_optimizer.py --address "123 Main St, McAllen TX" --price 285000 --beds 3 --baths 2

# SEO keyword tracking
python keyword_rank_tracker.py
```

---

## DEDICATED FACEBOOK AD SKILLS

Each skill runs the full 3-phase pipeline (strategy → images → post) for one client.
**Always invoke the dedicated skill before falling back to raw reasoning.**

| Skill | Client | Auth | Status |
|---|---|---|---|
| `/sugar-shack-facebook` | The Sugar Shack | Yehuda | ✅ Ready |
| `/island-arcade-facebook` | Island Arcade | Yehuda | ✅ Ready |
| `/island-candy-facebook` | Island Candy | **Mario** | ✅ Ready |
| `/juan-elizondo-remax-elite-facebook` | Juan Elizondo RE/MAX | **Mario** | ✅ Ready |
| `/spi-fun-rentals-facebook` | SPI Fun Rentals | Yehuda | ✅ Ready |
| `/custom-designs-facebook` | Custom Designs TX | TBD | ⚠️ Phase 3 pending (no FB page yet) |
| `/optimum-clinic-facebook` | Optimum Clinic | **Mario** | ⚠️ Phase 3 pending (page URL unconfirmed) |
| `/optimum-foundation-facebook` | Optimum Foundation | TBD | ⚠️ Phase 3 pending (page URL pending) |
| `/local-biz-facebook-ad-campaign` | Any business | — | ✅ Generic template |

---

## SKILLS 2.0 VAULT (841 skills)

```bash
cd "C:/Users/mario/.gemini/antigravity/scratch/jack_automations_vault"

# Find the right skill before starting any task
python skill_executor.py top "your intent here"
# Score > 1 → read SKILL.md and follow it exactly
# Score = 0 → proceed with raw reasoning

# Self-improvement tools (run overnight)
python skill_scanner.py --top 20               # find 20 weakest skills
python skill_improver.py <skill-id> --iterations 3
python skill_batch_runner.py --limit 50 --min-weakness 50
```

---

## TELEGRAM — NOTIFY MARIO FROM ANY SCRIPT

```python
import json, urllib.parse, urllib.request
from pathlib import Path

def notify_mario(text: str) -> bool:
    env = {}
    for line in Path("C:/Users/mario/.gemini/antigravity/scratch/gravity-claw/.env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN",""), env.get("TELEGRAM_USER_ID","")
    if not token or not chat_id: return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4096]}).encode()
    resp = urllib.request.urlopen(
        urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=10)
    return json.loads(resp.read()).get("ok", False)
```

- Interactive bot (Mario sends commands TO it): `python telegram_bot.py` (must be running)
- Outbound `notify_mario()`: works any time machine is online, no bot process needed
- Credentials: `scratch/gravity-claw/.env` (TELEGRAM_BOT_TOKEN + TELEGRAM_USER_ID)

---

## KEY FILE LOCATIONS

```
tools/execution/                           ← MAIN WORKING DIRECTORY
├── MASTER_WORKFLOW.md                     ← THIS FILE
├── BLOG_WORKFLOW.md                       ← Blog pipeline SOP (detailed)
├── FACEBOOK_SESSION_GUIDE.md              ← FB failure recovery decision tree
├── blog_writer.py                         ← SEO content pipeline
├── facebook_marketer.py                   ← Core FB posting engine
├── fb_campaign_runner.py                  ← Full 3-stage campaign pipeline
├── fb_health_check.py                     ← Session health check
├── morning_brief.py                       ← Daily intel synthesis (reads all 4 reports)
├── nightly_intelligence.py               ← 🆕 Master pipeline runner (chains all 4 scripts)
├── competitor_monitor.py                  ← Step 1: GBP ratings/hours scrape
├── competitor_fb_adlibrary.py            ← 🆕 Step 2: Facebook Ad Library scraper
├── competitor_ai_analyzer.py             ← 🆕 Step 3: AI analysis + counter-angles
├── competitor_review_miner.py            ← 🆕 Step 4: Google review text mining (weekly)
├── engagement_logger.py                   ← Ad performance tracker (+ --screenpipe OCR mode)
├── ad_copy_optimizer.py                   ← AI copy optimizer
├── screenpipe_verifier.py                ← Shared Screenpipe REST API functions
├── screenpipe_pipe_runner.py            ← 🆕 Screenpipe analysis pipes (time-breakdown, day-recap, top-of-mind, ai-habits)
├── screenpipe_idea_scout.py             ← 🆕 Competitor intelligence from browsing activity
├── daily_wrap.py                         ← 🆕 6 PM daily summary → Telegram
├── follow_up_checker.py                  ← 🆕 Email follow-up alerts → Telegram
├── weekly_changelog.py                   ← 🆕 Monday git changelog → Telegram
├── time_tracker.py                       ← 🆕 Friday client screen time → Telegram
├── activity_audit.py                     ← 🆕 Sunday cross-channel audit → Telegram
├── meeting_prep.py                       ← 🆕 Client meeting brief → Telegram
├── test_ocr_insights.py                  ← 🆕 OCR accuracy test for FB Insights
├── AGENT_TEAMS_GUIDE.md                  ← 🆕 5 parallel workflow templates
├── telegram_bot.py                        ← Bidirectional Telegram bot
├── fb_pages_config.json                   ← Page URLs + auth profile mapping
├── facebook_sniffer_profile/              ← Yehuda's Chrome session
├── facebook_mario_profile/                ← Mario's Chrome session
├── gbp_mario_profile/                     ← Mario's GBP Chrome session
├── gbp_sniffer_profile/                   ← Yehuda's GBP Chrome session
├── blog_posts/{client}/                   ← Generated blog content + images
├── competitor_reports/                    ← All intelligence reports (JSON + MD)
│   ├── YYYY-MM-DD.md                      ← GBP competitor report
│   ├── adlibrary_YYYY-MM-DD.json/md       ← Facebook Ad Library report
│   ├── ai_analysis_YYYY-MM-DD.json/md     ← AI analysis report
│   ├── reviews_YYYY-MM-DD.json/md         ← Google review mining report
│   ├── ai_angles_queue.json               ← Ready-to-run optimizer commands
│   └── state.json                         ← Change tracking baseline
├── morning_briefs/                        ← YYYY-MM-DD.md + .html
├── screenpipe_reports/                    ← 🆕 Screenpipe pipe outputs (YYYY-MM-DD/*.md + .html)
└── {client}/program.md  (×8)             ← Per-client steering docs (READ EACH SESSION)

scratch/gravity-claw/.env                  ← TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, FAL_KEY
scratch/jack_automations_vault/            ← Skills 2.0 (841 skills)
C:/Users/mario/.claude/CLAUDE.md           ← Global rules for all Claude sessions
C:/Users/mario/.claude/projects/.../memory/ ← Persistent memory files
C:/Users/mario/missioncontrol/dashboard   ← Next.js 14 dashboard (npm run dev -- --port 3001)
```

---

## SCREENPIPE + AUTOMATION TOOLS (Added 2026-03-23)

Screenpipe runs locally, captures screen OCR + audio transcription, queryable via REST API.

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# ── SCREENPIPE VERIFICATION ──────────────────────────────────────────────────
curl http://localhost:3030/health                       # check Screenpipe is running

# ── AUTOMATED REPORTS (Windows Task Scheduler) ───────────────────────────────
python daily_wrap.py --dry-run                          # 6 PM daily: FB + GBP + git + email summary
python follow_up_checker.py --dry-run                   # 9 AM + 2 PM: unanswered emails >24h
python weekly_changelog.py --dry-run --days 7           # Monday 8 AM: git changelog across repos
python time_tracker.py --dry-run --days 7               # Friday 5 PM: client screen time report
python activity_audit.py --dry-run --days 7             # Sunday 7 PM: cross-channel activity audit

# ── MEETING PREP ─────────────────────────────────────────────────────────────
python meeting_prep.py sugar_shack --dry-run            # client brief before calls
python meeting_prep.py optimum_clinic --days 14         # 14-day lookback

# ── ENGAGEMENT OCR CAPTURE ───────────────────────────────────────────────────
python test_ocr_insights.py                             # test OCR on FB Insights (run once)
python engagement_logger.py sugar_shack --screenpipe    # auto-capture from screen (if OCR viable)

# ── AGENT TEAMS (parallel workflows — use from Claude CLI) ───────────────────
# See AGENT_TEAMS_GUIDE.md for 5 ready-to-use workflow prompts
```

**Scheduled Tasks:**
| Task | Schedule | Script |
|---|---|---|
| Daily Wrap | 6 PM daily | `daily_wrap.py` |
| Follow-Up AM | 9 AM daily | `follow_up_checker.py` |
| Follow-Up PM | 2 PM daily | `follow_up_checker.py` |
| Weekly Changelog | Monday 8 AM | `weekly_changelog.py` |
| Time Tracker | Friday 5 PM | `time_tracker.py` |
| Activity Audit | Sunday 7 PM | `activity_audit.py` |

**Key module:** `screenpipe_verifier.py` — shared functions for all Screenpipe integrations
- `screenpipe_healthy()` — check if running
- `screenpipe_search(query, ...)` — search OCR/audio
- `verify_and_notify_fb(page_key, text_snippet)` — auto-verify FB posts
- `check_session_expired()` — detect login walls
- `get_screen_context_at_failure()` — grab OCR context for debugging

---

## PENDING — NEEDS RESOLUTION

| Item | Status | What's needed |
|---|---|---|
| Custom Designs TX Facebook page | ⚠️ Unconfirmed | User confirms page URL → add to `fb_pages_config.json`, set `page_key` in `blog_writer.py` |
| Optimum Foundation Facebook page | ⚠️ PENDING | User confirms page URL + which account manages it |
| Optimum Clinic Facebook page_id | ⚠️ Unconfirmed | Verify `61588407637377` is correct page ID |
| GBP Places API intel | ⚠️ Partial | Wire into `morning_brief.py` (Huayu question unanswered) |

---

## KNOWN BROKEN — DO NOT USE WITHOUT FIXING

| Script | Problem | Fix Plan |
|---|---|---|
| `commercial_comps.db` | Contains 8 FAKE properties | Delete + rebuild from real hidalgoad.org data |
| `county_records_scraper_v4.py` | Wrong form field → "No Rows To Show" | Fix form selector targeting |
| `loopnet_commercial_scraper.py` | CSS selectors outdated | Re-inspect current LoopNet HTML |
| `zillow_commercial_browser_scraper.py` | Uses residential selectors on commercial page | Use correct commercial URL + selectors |
| `master_commercial_comp_builder.py` | Stub only — never calls any scraper | Wire up real scrapers |

Full fix plan: `C:/Users/mario/.claude/plans/enumerated-honking-crane.md`

---

## MISSION CONTROL DASHBOARD

```bash
cd "C:/Users/mario/missioncontrol/dashboard"
npm run dev -- --port 3001
# URL: http://localhost:3001
# Sidebar: "Mission Control / SEO Command Center"
```

Routes: `/website-factory` · `/content/ad-library` · `/rankings` · `/competitors` · `/automation`

**Website Factory:** Generates complete Next.js sites in ~10-16 min for ~$0.60-1.15
- 3 themes: `glass-dark` (home services/auto), `glass-aurora` (real estate/legal/medical), `glass-neon` (restaurant/fitness)
- 22-file pipeline → fal.ai images → Supabase seed → Vercel deploy
- See `memory/missioncontrol.md` for full architecture

---

## PER-CLIENT STEERING DOCS (READ BEFORE EVERY SESSION)

Each file contains: business identity, auth, brand voice, current priorities, posting log, known winning angles.
**Update after every session.**

```
tools/execution/sugar_shack/program.md
tools/execution/island_arcade/program.md
tools/execution/island_candy/program.md
tools/execution/juan/program.md
tools/execution/spi_fun_rentals/program.md
tools/execution/custom_designs_tx/program.md
tools/execution/optimum_clinic/program.md
tools/execution/optimum_foundation/program.md
```
