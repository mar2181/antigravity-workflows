---
template: ga4_audit
version: 1.0
last_updated: 2026-05-05
parameters:
  - business_name
  - website_url
  - service_area
  - target_keywords
  - primary_services
  - special_notes
usage: |
  Replace the {{business_name}}, {{website_url}}, {{service_area}},
  {{target_keywords}}, {{primary_services}}, and {{special_notes}}
  placeholders at the top of the prompt. Body of the audit (Phases 1–15) is
  property-agnostic and stays the same.
---

# Comprehensive GA4 Audit — {{business_name}}

**Business name:** {{business_name}}
**Website:** {{website_url}}
**Service area:** {{service_area}}
**Target keywords:** {{target_keywords}}
**Primary services:** {{primary_services}}
**Special notes:** {{special_notes}}

---

Perform a comprehensive Google Analytics 4 audit for the GA4 account/property currently open in front of you.

You are controlling my browser inside Google Analytics.

The audit must be based on the current Google Analytics property that is already open. Do not switch to another account or property unless I explicitly tell you to.

This is an audit only. Do not make changes.

BUSINESS CONTEXT:
I may provide the business name, website, service area, target keywords, primary services, and special notes separately. Use that information in the final report, but verify all analytics findings from what is visible in Google Analytics.

IMPORTANT EXECUTION RULES:

- Work in phases.
- After each phase, stop and summarize what you captured before continuing.
- Take screenshots for every major section.
- Do not create reports.
- Do not create explorations.
- Do not create events.
- Do not mark or unmark key events.
- Do not edit data streams.
- Do not change enhanced measurement settings.
- Do not connect or disconnect Google Ads.
- Do not connect or disconnect Search Console.
- Do not change attribution settings.
- Do not change audiences.
- Do not change conversions/key events.
- Do not change users, access, permissions, filters, data retention, or property settings.
- Do not click Save, Create, Submit, Publish, Link, Unlink, Delete, or Confirm unless I explicitly approve it.
- You may open sections to inspect what is configured, then close/cancel without saving.
- If a section is missing, hidden, unavailable, or says "No data," screenshot it and document that.
- If the UI is slow, wait at least 2 seconds before documenting.
- If a report gets stuck, refresh once. If it still fails, document "Section did not load" and move on.
- Do not assume findings from any previous client apply to this property.
- Do not fake numbers.
- Only report what is visible inside Google Analytics.
- Every major claim must be backed by visible evidence or screenshot evidence.
- If a table has too many rows, capture the top 10 visible rows and note that more exist.
- If you are unsure whether something matters, screenshot it and document it.
- If the left navigation differs from this prompt, use the visible GA4 navigation and document what is available.

DEFAULT DATE RANGE RULE:

Use the current visible date range unless I provide a different one.

If changing the date range is safe and does not require saving, use:
- Last 90 days for the main audit
- Compare to previous period if the comparison option is easily available

If the property has very little data, also check:
- Last 28 days
- Last 6 months if available

Always document the exact date range used for every report.

PHASE 1 — Confirm Current GA4 Property and Account

1. Identify the current Google Analytics account/property open in front of you.

Document:
- Account name
- Property name
- Property ID if visible
- Website/app being tracked
- Whether this appears to be a GA4 property
- Current starting page
- Current date range if visible
- Any visible warnings, alerts, recommendations, or setup notices
- Whether the property appears active or possibly not collecting data

Take screenshots of:
- Main GA4 Home page or current starting page
- Property selector area if visible
- Any warnings or setup notices

Critical checks:
- Are we in the correct client property?
- Does the property appear to be collecting data?
- Are there alerts about missing data, setup issues, or recommendations?
- Is this clearly GA4 and not old Universal Analytics?

Stop after Phase 1 and summarize what was captured.

PHASE 2 — Home / Reports Snapshot / Overall Traffic Health

2. Navigate to Home and/or Reports Snapshot.

Document:
- Total users
- New users
- Sessions
- Engaged sessions
- Engagement rate
- Average engagement time
- Event count
- Key events
- Total revenue if visible
- Top pages/screens if visible
- Top acquisition channels if visible
- Realtime users if visible
- Any automated insights shown
- Any unusual spikes, drops, or missing data

Take screenshots of:
- Home overview
- Reports snapshot
- Any visible insights or alerts

Critical checks:
- Is traffic healthy or very low?
- Are users increasing or decreasing?
- Are key events/conversions being recorded?
- Is engagement strong or weak?
- Does the data look suspiciously empty?
- Are there obvious tracking gaps?

Stop after Phase 2 and summarize what was captured.

PHASE 3 — Realtime Tracking Check

3. Navigate to Realtime.

Document:
- Users in last 30 minutes
- Users by source/medium if visible
- Users by audience if visible
- Users by page title/screen name
- Events in last 30 minutes
- Key events in last 30 minutes if visible
- User locations if visible
- Whether the site appears to be actively collecting data

Take screenshots of:
- Realtime overview
- Realtime users/events
- Realtime pages/screens if visible

Critical checks:
- Is the GA4 tag currently firing?
- Are there real users/events showing?
- Is Realtime completely empty?
- Do events look normal?
- Are page_view/session_start/user_engagement events present?
- Are important actions like phone clicks, form submissions, purchases, bookings, or lead events appearing?

Stop after Phase 3 and summarize what was captured.

PHASE 4 — Acquisition Audit

4. Navigate to Reports → Acquisition.

If the left navigation is different, find any reports named:
- Acquisition overview
- User acquisition
- Traffic acquisition
- User acquisition: First user default channel group
- Traffic acquisition: Session default channel group
- Source/medium reports
- Campaign reports

Document from Acquisition overview:
- Total users
- New users
- Sessions
- Engaged sessions
- Engagement rate
- Average engagement time
- Event count
- Key events
- Revenue if visible
- Top channels
- Top source/medium combinations
- Top campaigns if visible

5. Open User acquisition.

Document:
- Top first user default channel groups
- New users by channel
- Engagement by channel
- Key events by channel
- Whether new users are coming from organic search, paid search, direct, referral, organic social, paid social, email, or unassigned

6. Open Traffic acquisition.

Document:
- Top session default channel groups
- Sessions by channel
- Users by channel
- Engagement rate by channel
- Key events by channel
- Revenue by channel if visible
- Source/medium data if available
- Campaign data if available

Take screenshots of:
- Acquisition overview
- User acquisition table
- Traffic acquisition table
- Source/medium or campaign data if visible

Critical checks:
- Is organic search producing traffic?
- Is Google Business Profile likely sending traffic?
- Are paid campaigns present?
- Is traffic too dependent on Direct?
- Is there a lot of Unassigned traffic?
- Are UTMs missing or messy?
- Are important channels producing key events?
- Are social, email, referral, or paid channels underperforming?
- Is acquisition growing or declining?

Stop after Phase 4 and summarize what was captured.

PHASE 5 — Engagement / Pages / Landing Pages Audit

7. Navigate to Reports → Engagement.

Inspect visible reports such as:
- Engagement overview
- Events
- Key events
- Pages and screens
- Landing page
- Conversions if present in the interface
- File downloads if available
- Outbound clicks if available
- Site search if available

Document from Engagement overview:
- Average engagement time
- Engaged sessions
- Engagement rate
- Event count
- Key events
- Views
- Views per user
- Top events
- Top pages/screens

8. Open Pages and screens.

Document:
- Top pages by views
- Users by page
- Views per page
- Average engagement time by page
- Event count by page
- Key events by page if visible
- Whether traffic is concentrated on the homepage
- Whether important service/product/blog/location pages are receiving traffic
- Whether useless technical pages are showing
- Whether duplicate URLs, query parameters, hash URLs, or HTTP/WWW variants appear

9. Open Landing page if available.

Document:
- Top landing pages
- Sessions by landing page
- Engagement rate by landing page
- Key events by landing page
- Whether homepage dominates landing traffic
- Whether SEO landing pages are pulling in traffic
- Whether service/location/blog pages are working as landing pages

Take screenshots of:
- Engagement overview
- Events table
- Key events table
- Pages and screens table
- Landing page table if available

Critical checks:
- Are important pages getting traffic?
- Are service pages getting engagement?
- Are landing pages converting?
- Is the homepage doing all the work?
- Are blog pages getting users but no leads?
- Are pages with traffic missing key events?
- Are there duplicate URL tracking problems?
- Are page titles messy or unclear?
- Are hash URLs or query parameters splitting data?
- Are important lead pages missing from the reports?

Stop after Phase 5 and summarize what was captured.

PHASE 6 — Events and Key Events Audit

10. Navigate to Engagement → Events and Admin/Data Display → Events if available.

Do not create or edit events.

Document:
- Event names visible
- Event count for each major event
- Users for each event if visible
- Which events are marked as key events
- Whether important events are missing
- Whether enhanced measurement events appear, such as:
  - page_view
  - scroll
  - click
  - file_download
  - form_start
  - form_submit
  - video_start
  - video_progress
  - video_complete
  - view_search_results
- Whether custom lead events exist, such as:
  - generate_lead
  - form_submit
  - phone_click
  - email_click
  - booking_click
  - appointment_click
  - quote_request
  - purchase
  - add_to_cart
  - begin_checkout
  - sign_up
  - contact
  - submit_application

11. Navigate to Key events if available.

Document:
- Key event names
- Key event counts
- Whether important business actions are marked as key events
- Whether useless events are incorrectly marked as key events
- Whether key events are missing entirely

Take screenshots of:
- Events report
- Key events report
- Any visible event detail tables

Critical checks:
- Are lead form submissions tracked?
- Are phone clicks tracked?
- Are appointment clicks tracked?
- Are email clicks tracked?
- Are booking clicks tracked?
- Are purchases tracked if ecommerce applies?
- Are key events configured correctly?
- Is there a gap between traffic and conversions/key events?
- Are important actions happening on the website but not showing in GA4?
- Are events named clearly and consistently?

Stop after Phase 6 and summarize what was captured.

PHASE 7 — Monetization / Ecommerce / Revenue Audit

12. Navigate to Monetization if available.

If this is not an ecommerce business, document whether Monetization is unavailable or shows no data.

Inspect reports such as:
- Monetization overview
- Ecommerce purchases
- Purchase journey
- Checkout journey
- In-app purchases
- Publisher ads
- Promotions

Document:
- Total revenue
- Ecommerce purchases
- Items purchased
- Average purchase revenue
- Purchase conversion/key event data
- Product/item performance
- Cart/checkout funnel if visible
- Whether ecommerce tracking appears configured

Take screenshots of:
- Monetization overview
- Ecommerce purchases if available
- Purchase/checkout journey if available

Critical checks:
- Is ecommerce tracking needed for this business?
- If ecommerce exists, is revenue being tracked?
- Are purchases missing?
- Are product names missing or messy?
- Are cart/checkout steps being tracked?
- Are revenue and purchase events accurate?

Stop after Phase 7 and summarize what was captured.

PHASE 8 — Retention Audit

13. Navigate to Retention.

Document:
- Returning users
- New users
- User retention
- Cohort/retention chart if visible
- User engagement by cohort if visible
- Lifetime value if visible
- Whether people return to the site after first visit

Take screenshots of:
- Retention overview
- Retention charts/tables

Critical checks:
- Are users coming back?
- Is the site only getting one-time visits?
- Is there enough data to evaluate retention?
- Does the business need remarketing, email capture, or stronger follow-up?

Stop after Phase 8 and summarize what was captured.

PHASE 9 — Demographics / User Attributes Audit

14. Navigate to User attributes or Demographics.

Document:
- Country
- Region
- City
- Language
- Age if available
- Gender if available
- Interests if available
- Whether demographic data is unavailable because of privacy thresholds or Google Signals/settings

Take screenshots of:
- User attributes overview
- Country/region/city data
- Age/gender/interests if visible

Critical checks:
- Is traffic coming from the correct service area?
- Are users in the wrong cities/countries?
- Is there suspicious international traffic?
- Are local users engaging?
- Are important markets missing?
- Is demographic data too limited to evaluate?

Stop after Phase 9 and summarize what was captured.

PHASE 10 — Tech / Device Audit

15. Navigate to Tech.

Inspect reports such as:
- Tech overview
- Browser
- Device category
- Operating system
- Screen resolution
- Platform/device
- App version if relevant

Document:
- Mobile users
- Desktop users
- Tablet users
- Engagement by device
- Key events by device if visible
- Top browsers
- Top operating systems
- Any device/browser with unusually poor engagement
- Whether mobile dominates traffic
- Whether desktop traffic converts better
- Whether technical issues may exist on certain devices

Take screenshots of:
- Tech overview
- Device category table
- Browser/OS tables if visible

Critical checks:
- Is mobile performance weak?
- Are mobile users bouncing or not converting?
- Are important browsers/devices showing low engagement?
- Is the website probably broken or slow on a device type?
- Is mobile traffic high enough to prioritize mobile UX?

Stop after Phase 10 and summarize what was captured.

PHASE 11 — Advertising / Attribution Audit

16. Navigate to Advertising if available.

Do not connect or change ad accounts.

Inspect visible reports such as:
- Advertising snapshot
- Performance
- Attribution paths
- Conversion/key event paths
- Model comparison if available
- Google Ads campaigns if linked

Document:
- Whether Google Ads is linked
- Whether ad campaign data appears
- Key events/conversions attributed to ads
- Attribution paths
- Top channels assisting key events
- Whether paid traffic is producing results
- Whether attribution data is missing or limited

Take screenshots of:
- Advertising overview
- Attribution paths if visible
- Google Ads/campaign performance if visible

Critical checks:
- Is Google Ads linked?
- Are ads generating key events?
- Are attribution paths useful?
- Are paid campaigns getting traffic but no leads?
- Is ad reporting incomplete because linking or key events are missing?

Stop after Phase 11 and summarize what was captured.

PHASE 12 — Search Console Integration Audit

17. Check whether Search Console data is available inside GA4.

Look for reports such as:
- Search Console
- Queries
- Google organic search traffic
- Google organic search queries
- Google organic search landing page

Also inspect Admin → Product links → Search Console links if visible.

Do not create or edit links.

Document:
- Whether Search Console is linked
- Linked Search Console property if visible
- Linked web stream if visible
- Search query data availability
- Organic landing page data availability
- Whether the integration appears missing or broken

Take screenshots of:
- Search Console reports if visible
- Search Console links area if safely inspectable

Critical checks:
- Is GA4 connected to Search Console?
- Are organic queries visible?
- Are organic landing pages visible?
- Is the linked property the correct website?
- Is Search Console data missing because the link is not configured?

Stop after Phase 12 and summarize what was captured.

PHASE 13 — Admin / Data Stream / Tracking Setup Audit

18. Navigate to Admin.

Do not edit anything.

Inspect the property setup and data collection areas.

Look for:
- Property details
- Data streams
- Web stream
- Measurement ID
- Stream URL
- Enhanced measurement
- Google tag settings
- Events
- Key events
- Audiences
- Product links
- Google Ads links
- Search Console links
- BigQuery links if visible
- Data retention
- Data filters
- Internal traffic filters
- Referral exclusions / unwanted referrals
- Cross-domain measurement if visible
- Consent settings if visible
- User access, only if necessary and safe to view

19. Open the web data stream.

Document:
- Stream name
- Stream URL
- Measurement ID, but do not expose sensitive private details beyond what is necessary
- Whether enhanced measurement is enabled
- Which enhanced measurement options appear enabled if visible
- Whether the stream URL matches the actual website
- Whether the stream appears to be receiving data
- Whether there are multiple streams that might duplicate tracking
- Whether cross-domain measurement is configured if relevant
- Whether unwanted referrals are configured if visible
- Whether internal traffic filters exist if visible

Take screenshots of:
- Admin overview
- Data streams list
- Web stream details
- Enhanced measurement area
- Events/key events setup
- Product links
- Data filters or retention if visible

Critical checks:
- Is the data stream URL correct?
- Is the Measurement ID present?
- Is enhanced measurement enabled?
- Are multiple streams causing confusion?
- Is Search Console linked?
- Is Google Ads linked if ads are being used?
- Are key events configured?
- Are internal traffic filters missing?
- Are unwanted referrals causing bad attribution?
- Are cross-domain settings needed?
- Is the property setup incomplete?

Stop after Phase 13 and summarize what was captured.

PHASE 14 — Data Quality / Tracking Problem Diagnosis

20. Based on all reports inspected, diagnose tracking and data quality.

Check for:
- No data or very low data
- Realtime empty
- Missing page_view events
- Missing session_start events
- Missing user_engagement events
- Missing form_submit or lead events
- Missing phone click tracking
- Missing booking/appointment click tracking
- No key events
- Too many unassigned sessions
- Too much direct traffic
- Self-referrals
- Payment/referral gateway issues
- Cross-domain problems
- Duplicate page paths
- Query parameter clutter
- Hash URL clutter
- Incorrect stream URL
- Multiple properties/streams confusion
- Wrong website connected
- Google Ads not linked
- Search Console not linked
- Internal traffic polluting data
- Bot/spam-looking traffic
- Wrong geographic traffic
- Consent/banner issues possibly suppressing data

Take screenshots of any evidence supporting data quality issues.

Stop after Phase 14 and summarize what was captured.

PHASE 15 — Final GA4 Audit Report

21. Compile all findings into a professional Google Analytics 4 audit report.

The report must include:

A. Executive Summary
- Overall analytics health summary
- Biggest tracking problems
- Biggest marketing insights
- Biggest conversion/key event gaps
- Whether the property is ready for serious SEO/ads reporting or still has tracking blockers

B. Overall Grade
- Give an overall grade from A to F
- Explain the grade clearly
- Do not be generous if traffic is missing, key events are missing, Search Console/Google Ads links are missing, important events are not tracked, or data quality is weak

C. Property / Setup Summary
- Account name
- Property name
- Property ID if visible
- Data stream name
- Stream URL
- Measurement ID presence
- Date range audited
- Property/setup grade

D. Traffic Overview
- Users
- New users
- Sessions
- Engaged sessions
- Engagement rate
- Average engagement time
- Event count
- Key events
- Revenue if applicable
- Traffic trend
- Traffic overview grade

E. Realtime Tracking
- Users in last 30 minutes
- Realtime events
- Realtime pages/screens
- Whether tracking appears active
- Realtime tracking grade

F. Acquisition Analysis
- Top channels
- User acquisition
- Traffic acquisition
- Source/medium quality
- Campaign/UTM quality
- Organic search performance
- Direct traffic concerns
- Unassigned traffic concerns
- Acquisition grade

G. Engagement and Page Performance
- Top pages/screens
- Top landing pages
- Homepage dominance
- Important page traffic
- Engagement by page
- Duplicate URL/query/hash issues
- Page engagement grade

H. Events and Key Events
- Events present
- Key events configured
- Missing lead/conversion events
- Incorrect key events
- Recommended events to track
- Events/key events grade

I. Lead / Conversion Tracking
- Phone clicks
- Form submissions
- Email clicks
- Booking/appointment clicks
- Quote requests
- Purchases if relevant
- Whether business-critical actions are measured
- Lead tracking grade

J. Monetization / Ecommerce
- Revenue
- Purchases
- Product performance
- Checkout journey
- Whether ecommerce tracking is needed or correctly configured
- Monetization grade

K. Retention
- New vs returning users
- Returning user behavior
- Retention trends
- Follow-up/remarketing opportunities
- Retention grade

L. Demographics / Geography
- Countries
- Regions
- Cities
- Languages
- Age/gender/interests if visible
- Local market fit
- Suspicious location traffic
- Geography/demographics grade

M. Device / Tech
- Mobile/desktop/tablet split
- Device engagement
- Browser/OS issues
- Mobile conversion concerns
- Tech/device grade

N. Advertising / Attribution
- Google Ads link status
- Paid traffic performance
- Attribution paths
- Ad conversion/key event tracking
- Advertising grade

O. Search Console Integration
- Search Console link status
- Query report availability
- Organic landing page availability
- Whether linked property is correct
- Search Console integration grade

P. Admin / Data Quality
- Enhanced measurement status
- Data stream correctness
- Internal traffic filters
- Referral exclusions/unwanted referrals
- Cross-domain measurement
- Data retention
- Multiple streams/properties issues
- Data quality grade

Q. Critical Findings to Confirm or Reject Based on Evidence

Confirm whether each of these is true:
- GA4 is not collecting data
- Realtime is empty
- Website stream URL is wrong
- Measurement ID exists but may not be installed correctly
- Enhanced measurement is disabled
- Important events are missing
- No key events are configured
- Form submissions are not tracked
- Phone clicks are not tracked
- Booking/appointment clicks are not tracked
- Traffic is mostly Direct
- Unassigned traffic is high
- Organic search traffic is weak
- Important pages receive little or no traffic
- Homepage receives most traffic
- Search Console is not linked
- Google Ads is not linked
- Ecommerce tracking is missing or broken
- Mobile users perform poorly
- Local traffic is coming from the wrong cities/countries
- Internal traffic may be polluting data
- Duplicate URLs, query parameters, or hash fragments are splitting reports
- Attribution data is incomplete
- Data quality is not good enough for decision-making

R. Prioritized Action Plan

Create an 8–10 item action plan ranked by priority.

For each action item include:
- Priority level: Critical, High, Medium, or Low
- Timeline: Immediate, 1–3 days, 1 week, 2–4 weeks, or ongoing
- Exact issue
- Why it matters
- Specific fix
- Expected reporting or marketing impact

The action plan should include recommendations around:
- Fixing GA4 installation if tracking is weak or missing
- Verifying Google tag / GTM installation
- Enabling or correcting enhanced measurement
- Creating or correcting lead/key events
- Tracking phone clicks, forms, email clicks, booking clicks, quote requests, and purchases where relevant
- Linking Search Console
- Linking Google Ads if ads are used
- Cleaning up UTMs and channel attribution
- Reducing Unassigned traffic
- Fixing duplicate URL/query/hash reporting issues
- Adding internal traffic filters
- Configuring unwanted referrals
- Improving landing page performance tracking
- Setting up a simple monthly reporting dashboard
- Using GA4 insights to guide SEO, GBP, ads, and content decisions

S. Screenshot Checklist

Include a final checklist showing whether screenshots were captured for:
- GA4 Home
- Reports snapshot
- Realtime
- Acquisition overview
- User acquisition
- Traffic acquisition
- Engagement overview
- Events
- Key events
- Pages and screens
- Landing pages
- Monetization/ecommerce if available
- Retention
- Demographics/User attributes
- Tech/device
- Advertising/attribution
- Search Console reports or links
- Admin overview
- Data streams
- Web stream details
- Enhanced measurement
- Product links
- Data filters/retention if visible
- Any warnings or setup notices

Final output format:
- Professional Google Analytics 4 audit report
- Clear section headings
- Grades for each section
- Overall grade
- Screenshot checklist
- Prioritized action plan
- No unsupported claims
- No copied findings from any other client unless verified in the current GA4 property
