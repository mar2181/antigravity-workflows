# Facebook Posting — Session Start Guide
> Run this at the start of EVERY session before attempting any posts.
> If it passes, you can post immediately. If it fails, follow the fix below.

---

## 30-Second Session Start (Do This Every Time)

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"

# Step 1: Kill any leftover Chrome from last session
powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"

# Step 2: Clear profile locks
rm -f facebook_sniffer_profile/SingletonLock
rm -f facebook_mario_profile/SingletonLock

# Step 3: Run health check
python fb_health_check.py
```

If health check shows all GREEN — you're ready to post. Skip to "Posting Commands" below.

---

## Posting Commands (Copy-Paste Ready)

### Yehuda's Pages (facebook_sniffer_profile)
```bash
# Sugar Shack
python facebook_marketer.py --action text --page sugar_shack --message "YOUR MESSAGE"

# Island Arcade
python facebook_marketer.py --action text --page island_arcade --message "YOUR MESSAGE"

# SPI Fun Rentals
python facebook_marketer.py --action text --page spi --message "YOUR MESSAGE"
```

### Mario's Pages (facebook_mario_profile — auto-detected, no --profile needed)
```bash
# Optimum Clinic
python facebook_marketer.py --action text --page optimum_clinic --message "YOUR MESSAGE"

# Juan Elizondo
python facebook_marketer.py --action text --page juan --message "YOUR MESSAGE"
```

> **Note:** The `--profile` flag is NOT needed. The marketer auto-reads the correct profile
> from `fb_pages_config.json` per page. Fixed 2026-03-14.

---

## Account → Page Mapping (Reference)

| Profile Directory | Account | Pages |
|---|---|---|
| `facebook_sniffer_profile` | Yehuda Azoulay (quepadre@live.com) | sugar_shack, island_arcade, spi |
| `facebook_mario_profile` | Mario Elizondo (marioelizondo81@gmail.com) | optimum_clinic, juan |

---

## If a Post Fails — Decision Tree

```
Post failed?
│
├─ "[CONFIG] Using per-page auth profile: facebook_mario_profile" NOT in output?
│   └─ FIX: The config entry is missing auth_profile. Check fb_pages_config.json
│      and add "auth_profile": "facebook_mario_profile" to the page entry.
│
├─ "TargetClosedError" or browser crashes immediately?
│   └─ FIX: Profile is locked. Run:
│      powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"
│      rm -f facebook_mario_profile/SingletonLock
│      rm -f facebook_sniffer_profile/SingletonLock
│      Then retry.
│
├─ Pages list shows WRONG account (e.g. "Pages Yehuda manages" when posting to optimum_clinic)?
│   └─ FIX: The wrong profile was used. Check fb_pages_config.json for the page's auth_profile.
│      The marketer now auto-detects this — but if missing, it defaults to sniffer_profile.
│
├─ "Composer did not open" after pages-list fallback also fails?
│   └─ FIX: Session expired. Re-authenticate:
│      # For Yehuda's pages:
│      cd C:\Users\mario\.gemini\antigravity\scratch
│      python reauth_facebook_sniffer.py
│      # For Mario's pages:
│      python reauth_mario_facebook.py
│
├─ "Could not find text input in dialog"?
│   └─ FIX: A "Switch profiles" modal opened instead of the post composer.
│      The marketer now dismisses this automatically (fixed 2026-03-14).
│      If still failing, check debug_snap_04_composer_open.png — what dialog is on screen?
│
└─ Post button not found / timeout on submit?
    └─ FIX: Facebook UI changed. Run the inspector to remap selectors:
       cd C:\Users\mario\.gemini\antigravity\scratch
       python fb_inspector.py
       Open fb_buttons.txt and find current button labels.
       Update _open_composer() selectors in facebook_marketer.py.
```

---

## Debug Snapshots — Always Check These First

When a post fails, look at these files BEFORE debugging code:

```
C:\Users\mario\.gemini\antigravity\tools\execution\
  debug_snap_01_page_loaded.png      — What page loaded?
  debug_snap_02_after_switch.png     — Did profile switch happen?
  debug_snap_fallback_pages_list.png — Pages list: whose account? Right pages listed?
  debug_snap_04_composer_open.png    — What "dialog" opened? Post composer or Switch modal?
  debug_snap_pre_post_click.png      — What was on screen before clicking Post?
```

**The single fastest diagnosis:** open `debug_snap_fallback_pages_list.png`.
- Shows "Pages Mario Elizondo manages" + Optimum Clinic? → correct profile, proceed.
- Shows "Pages Yehuda Azoulay manages"? → wrong profile. Fix auth_profile in config.
- Shows login page? → session expired. Run reauth script.

---

## Known Fixed Bugs (Do NOT Re-Debug These)

| Bug | Symptom | Fix Applied | Date |
|-----|---------|-------------|------|
| Wrong profile default | Marketer used sniffer_profile for mario's pages | `main()` now reads per-page `auth_profile` from config | 2026-03-14 |
| Switch profiles modal blocking | "Could not find text input" — modal was the "dialog", not the composer | Fallback verifies textbox exists in dialog before confirming composer open | 2026-03-14 |
| JS evaluate charmap error | `'charmap' codec can't encode \u2713` | Replaced JS evaluate with Playwright `:has()` locator | 2026-03-14 |
| Switch Now button unreliable | Admin banner doesn't appear on direct page URL | Pages-list fallback added — navigates to `/pages/?category=your_pages` first | 2026-03-14 |

---

## Option: Build fb_health_check.py (Recommended Next Step)

Running `python fb_health_check.py` should do in 15 seconds what took 30 minutes today:
1. Launch each profile (mario + sniffer) — verify session is authenticated
2. Navigate to each page's pages list — verify correct account
3. Verify "Create post" button is reachable for each page
4. Print GREEN/RED per page

**Ask Claude Code to build this.** Once built, add it to your morning startup alongside `morning_brief.py`.

---

## Session End Checklist

After every successful session:
- [ ] Update `program.md` Posting Log for each page you posted to
- [ ] Kill Chrome: `powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"`
- [ ] Note anything that broke in the "Known Fixed Bugs" table above

---

*Last updated: 2026-03-14 — after fixing the 3-hour wrong-profile debugging incident.*
