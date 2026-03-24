# Agent Teams — Ready-to-Use Workflow Patterns

> Claude Code Agent Teams lets you run multiple Claude Code instances in parallel,
> coordinating via shared task lists and messaging. Already enabled in your settings.

## Quick Start

From the **Claude Code CLI** (not VS Code — use Windows Terminal or PowerShell):

```bash
claude
```

Then type one of the workflow prompts below. Claude will spawn teammates automatically.

**Windows note:** Must use in-process mode. Press `Shift+Down` to cycle between teammates.

---

## Workflow 1: Parallel Client Posting

> Best for: Posting to multiple clients at once (saves 15+ min vs sequential)

```
Create an agent team with 3 teammates for parallel Facebook posting.

Before starting: run fb_health_check.py to verify sessions.

Teammate 1: Post to Sugar Shack
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Read sugar_shack/program.md for current priorities
  - Generate ad copy following the sugar-shack-facebook skill
  - Post using: python facebook_marketer.py --action image --page sugar_shack --message "<copy>" --image-path "<path>"
  - Verify the post screenshot, update posting log

Teammate 2: Post to Island Arcade
  - Same flow but read island_arcade/program.md
  - Use island-arcade-facebook skill patterns
  - Post to island_arcade page

Teammate 3: Post to Optimum Clinic
  - Same flow but read optimum_clinic/program.md
  - IMPORTANT: Only mention $75 sick visit pricing
  - Post using facebook_mario_profile (not sniffer)

Each teammate: verify your post screenshot before marking done.
Coordinate: if any session fails, alert the team lead immediately.
```

## Workflow 2: Morning Operations Blitz

> Best for: Starting the day with all intel gathered in parallel (~3 min vs ~10 min)

```
Create an agent team with 3 teammates for morning operations.

Teammate 1: Health Check + Brief
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Run: python fb_health_check.py
  - Run: python morning_brief.py --open
  - Report: which sessions are GREEN, which are RED

Teammate 2: Competitor Intelligence
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Check competitor_reports/ for latest reports
  - If older than 24h, run: python nightly_intelligence.py
  - Summarize: any new competitor ads or GBP changes?

Teammate 3: Email + Follow-ups
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Run: python follow_up_checker.py --dry-run
  - Check for urgent client emails
  - Report: any emails needing immediate response?

Team lead: compile all three reports into a single morning status.
```

## Workflow 3: Campaign Blitz (Full Pipeline)

> Best for: Generating a complete campaign (images + copy + scheduling) fast

```
Create an agent team with 3 teammates for a Sugar Shack campaign blitz.

Teammate 1: Ad Copy Generation
  - Read sugar_shack/program.md
  - Generate 5 ad angles with copy (max 300 words each)
  - No text overlays in images, max 3 hashtags
  - Save as sugar_shack_ADS_FINAL.md

Teammate 2: Image Generation
  - Wait for Teammate 1 to finish at least 2 ads
  - For each ad, generate fal.ai Flux Pro image (landscape_16_9)
  - Save to C:/Users/mario/sugar_shack_ad_images/
  - Create manifest.json with paths

Teammate 3: Scheduling Calendar
  - Plan a 7-day posting schedule (1 ad per day)
  - Optimal times: 10 AM, 2 PM, or 6 PM CT
  - Alternate between new content and reshares
  - Save schedule to sugar_shack/posting_calendar.md

Team lead: when all done, generate preview HTMLs for each ad.
```

## Workflow 4: Parallel Debugging

> Best for: When Playwright fails and you need to test multiple theories

```
Create an agent team with 2 teammates to debug this Playwright failure.

Context: facebook_marketer.py failed with "Composer did not open" on [PAGE].

Teammate 1: Selector Theory
  - cd C:/Users/mario/.gemini/antigravity/scratch
  - Run fb_inspector.py to capture current button text
  - Compare fb_buttons.txt against _open_composer() selectors
  - If different, identify the new selector

Teammate 2: Session Theory
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Kill Chrome, clear SingletonLock
  - Run fb_health_check.py
  - If session expired, run reauth script
  - Check Screenpipe for "Log in to Facebook" in recent OCR

Whoever finds the issue first: message the other teammate to stop.
Team lead: apply the fix and verify with a test post.
```

## Workflow 5: Blog Content Blitz

> Best for: Generating blog posts for multiple clients simultaneously

```
Create an agent team with 3 teammates for blog content generation.

Teammate 1: Custom Designs TX blog
  - cd C:/Users/mario/.gemini/antigravity/tools/execution
  - Run: python blog_writer.py --client custom_designs_tx --list
  - Pick the highest-priority keyword
  - Run: python blog_writer.py --client custom_designs_tx --keyword "<keyword>" --preview

Teammate 2: Sugar Shack blog
  - Same flow for sugar_shack

Teammate 3: Optimum Clinic blog
  - Same flow for optimum_clinic

Each teammate: generate blog + GBP post + FB post + 4 images.
Team lead: review all three and approve for publishing.
```

---

## Tips

- **Cost:** Each teammate is a separate Claude instance — use teams for genuinely parallel work, not simple sequential tasks
- **Navigation:** Press `Shift+Down` to cycle between teammates in Windows
- **No nested teams:** One team per session
- **Subagents vs Teams:** For focused tasks where only the result matters, use regular subagents (the Agent tool). Use teams when teammates need to communicate with each other.
- **Session:** After `/resume`, teammates don't resume — start a new team if needed

## All Scheduled Tasks (Current)

| Task | Schedule | Script |
|---|---|---|
| Daily Wrap | 6 PM daily | `daily_wrap.py` |
| Follow-Up AM | 9 AM daily | `follow_up_checker.py` |
| Follow-Up PM | 2 PM daily | `follow_up_checker.py` |
| Weekly Changelog | Monday 8 AM | `weekly_changelog.py` |
| Time Tracker | Friday 5 PM | `time_tracker.py` |
| Activity Audit | Sunday 7 PM | `activity_audit.py` |
