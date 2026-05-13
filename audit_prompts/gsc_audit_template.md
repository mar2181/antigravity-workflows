---
template: gsc_audit
version: 1.0
last_updated: 2026-05-05
parameters:
  - business_name
  - website_url
  - special_notes
usage: |
  Replace the {{business_name}}, {{website_url}}, and {{special_notes}}
  placeholders at the top of the prompt. Body of the audit (Phases 1–9) is
  property-agnostic and stays the same.
---

# Comprehensive GSC SEO Audit — {{business_name}}

**Business name:** {{business_name}}
**Website URL:** {{website_url}}
**Special notes:** {{special_notes}}

---

Perform a comprehensive Google Search Console SEO audit for the website/property currently open in front of you.

You are controlling my browser inside Google Search Console.

The audit must be based on the current GSC property/page that is already open. Do not switch to another property unless I explicitly tell you to.

Before starting, identify and document:
- The visible Google Search Console property name
- The website/domain being audited
- The current GSC section/page you are starting from
- The visible date range in the Performance report, once you reach Performance

Important execution rules:
- Work in phases.
- After each phase, stop and summarize what you captured before continuing.
- Do not rush through pages.
- Wait for GSC data tables to load before documenting them.
- Take screenshots for every major report.
- Do not click "Request indexing."
- Do not click "Start new validation."
- Do not submit, delete, remove, validate, change settings, or modify anything unless I explicitly approve it.
- This is an audit only.
- Do not assume findings from any previous client apply to this site.
- Do not fake numbers.
- Only report what is visible inside Google Search Console.
- Every major claim must be backed by screenshot evidence or visible GSC data.
- If a GSC report says "No data," screenshot it and move on.
- If a table has too many rows, capture the total count if visible, the top 10 visible rows, and a screenshot.
- If URL Inspection takes too long, wait once, refresh once, and try again. If it still does not load, document "URL Inspection did not complete" and move on.
- If you are unsure whether something is important, screenshot it and document it.

Business information:
I may provide the business name, website URL, and special notes separately. Use that information when writing the final report, but still verify all SEO findings inside GSC.

PHASE 1 — Confirm Starting Property and Overview

1. Confirm the current Google Search Console property visible in the browser.
2. Confirm the domain or website being audited.
3. Navigate to the Overview page if you are not already there.
4. Screenshot the Overview page showing:
   - Performance summary
   - Indexing summary
   - Core Web Vitals or Experience summary
   - Any visible alerts, warnings, or issues

Document:
- Visible property name
- Website/domain
- Total clicks shown on Overview, if visible
- Total impressions shown on Overview, if visible
- Indexed page count, if visible
- Not indexed page count, if visible
- Core Web Vitals summary, if visible
- Any visible warnings or errors

Stop after Phase 1 and summarize what was captured.

PHASE 2 — Performance Report

5. Navigate to the Performance section.

6. Document:
   - Date range used
   - Total clicks
   - Total impressions
   - Average CTR
   - Average position

7. Screenshot the full Performance chart.

8. Click the QUERIES tab and document:
   - Top 10+ queries
   - Clicks for each query
   - Impressions for each query
   - CTR and average position if visible
   - Screenshot the query table

9. Click the PAGES tab.
   - Wait at least 2 seconds for data to load.
   - Screenshot page-level data.
   - Document whether traffic is concentrated on the homepage or spread across multiple pages.
   - Identify unusual URLs, including:
     - Hash-based URLs such as #services, #contact, #menu, #visit, etc.
     - HTTP versions
     - HTTPS versions
     - WWW versions
     - Non-WWW versions
     - Redirect variants
     - Duplicate-looking URLs
   - Document clicks, impressions, CTR, and average position for top pages.

10. Click the COUNTRIES tab and document:
    - Country breakdown
    - Clicks and impressions by country
    - Screenshot the country data

11. Click the DEVICES tab and document:
    - Mobile clicks/impressions
    - Desktop clicks/impressions
    - Tablet clicks/impressions
    - Device split percentage if visible
    - Screenshot the device data

Stop after Phase 2 and summarize what was captured.

PHASE 3 — Page Indexing

12. Navigate to Pages under the Indexing section.

13. Document:
    - Total indexed pages
    - Total not indexed pages
    - Overall indexing rate percentage
    - Screenshot the indexing graph
    - Whether the site has a serious indexing problem

14. Scroll to the "Why pages aren't indexed" section and identify every listed reason, including but not limited to:
    - Page with redirect
    - Discovered - currently not indexed
    - Crawled - currently not indexed
    - Alternate page with proper canonical tag
    - Duplicate without user-selected canonical
    - Not found 404
    - Soft 404
    - Excluded by noindex tag
    - Blocked by robots.txt

15. For each visible "not indexed" reason:
    - Click into the reason
    - Screenshot the detail page
    - Document the affected page count
    - Capture the top 10 affected URLs
    - Document last crawled dates where visible
    - Count how many visible examples show "Last crawled: N/A"
    - Identify whether affected URLs are:
      - Important pages
      - Service pages
      - Blog pages
      - Redirect variants
      - Duplicate URLs
      - Technical URLs
      - Hash-based URLs
    - If there are more than 10 URLs, note that additional URLs exist and recommend exporting the full report for deeper review.

Stop after Phase 3 and summarize what was captured.

PHASE 4 — Sitemaps

16. Navigate to the Sitemaps section.

17. Document:
    - Submitted sitemap URL
    - Submission date
    - Last read date
    - Sitemap status
    - Discovered pages count
    - Discovered videos count if visible
    - Screenshot the sitemap table

Critical sitemap checks:
- Specifically look for "Couldn't fetch."
- If sitemap status shows "Couldn't fetch," flag this as a critical SEO issue.
- If no sitemap is submitted, flag that as a critical SEO issue.
- If the sitemap is successful, document that clearly.
- Check whether sitemap URLs match the preferred domain version.
- Note whether sitemap URLs conflict with canonical or redirect behavior.

Stop after Phase 4 and summarize what was captured.

PHASE 5 — Core Web Vitals, HTTPS, Manual Actions, and Security

18. Navigate to Core Web Vitals and document:
    - Mobile status
    - Desktop status
    - Whether there is enough field data
    - Any Poor, Needs Improvement, or Good URLs
    - Screenshot mobile and desktop status
    - If the site shows no field data, document "No Core Web Vitals field data available yet."

19. Navigate to HTTPS and document:
    - HTTPS URL count
    - Non-HTTPS URL count
    - Any HTTPS issues
    - Screenshot the HTTPS report
    - Identify whether HTTP, WWW, or non-WWW redirect variants are causing problems

20. Navigate to Manual Actions and document:
    - Whether any manual penalties exist
    - Screenshot the Manual Actions screen

21. Navigate to Security Issues and document:
    - Whether any hacks, malware, phishing, or security issues are detected
    - Screenshot the Security Issues screen

Stop after Phase 5 and summarize what was captured.

PHASE 6 — Links

22. Navigate to the Links section.

23. Document:
    - Total external links/backlinks
    - Top linking sites
    - Extract and list linking domain names
    - Top linked pages externally
    - Top linking text
    - Total internal links
    - Top internally linked pages
    - Screenshot each relevant Links section

Critical links checks:
- If external backlinks are zero or extremely low, flag this as a visibility/authority issue.
- If internal link count is very low, especially 1 or less, flag this as a critical internal linking issue.
- Document whether important pages have internal links.
- Document whether the homepage is receiving almost all internal links.

Stop after Phase 6 and summarize what was captured.

PHASE 7 — URL Inspection

24. Navigate to URL Inspection using the search bar at the top of Google Search Console.

25. Inspect the main homepage URL for the current property.

Use the canonical homepage URL visible from the site or GSC data. If unsure, use the version shown most consistently in GSC Performance Pages or Sitemaps.

Document:
- Exact URL inspected
- Whether the URL is on Google
- Page indexing status
- Discovery method, such as sitemap or referring page
- Last crawl date
- Crawled as device type
- Crawl allowed status
- Page fetch status
- Indexing allowed status
- User-declared canonical tag
- Google-selected canonical tag if visible
- Screenshot the full indexing details

26. Inspect the alternate homepage version if applicable.

Examples:
- If homepage is https://www.example.com/, inspect https://example.com/
- If homepage is https://example.com/, inspect https://www.example.com/
- If HTTP variants appear in GSC, inspect the HTTP version too if useful.

Document:
- Whether it redirects
- Whether the URL is on Google
- Page indexing status
- Last crawl date
- User-declared canonical
- Google-selected canonical
- Screenshot the full indexing details

27. Inspect one important interior page.

Use a real URL discovered from:
- Website navigation
- GSC Performance Pages report
- Sitemap
- Page Indexing report

Good candidates include:
- Service page
- Product page
- Blog page
- About page
- Contact page
- Location page

Do not make up a URL.

Document:
- Exact URL inspected
- Whether the URL is on Google
- Page indexing status
- Discovery method
- Referring page if visible
- Last crawl date
- Crawled as device type
- Crawl allowed status
- Page fetch status
- Indexing allowed status
- User-declared canonical tag
- Google-selected canonical tag if visible
- Screenshot the full indexing details

Stop after Phase 7 and summarize what was captured.

PHASE 8 — Structured Data / Enhancements

28. Check for structured data and enhancements inside GSC.

Navigate through any visible Enhancements sections, such as:
- Breadcrumbs
- FAQ
- Organization
- Local business
- Products
- Videos
- Sitelinks searchbox
- Review snippets
- Merchant listings
- Any other available enhancement reports

Document:
- Which enhancements are present
- Which enhancements are missing
- Whether structured data appears to be detected
- Any validation errors or warnings
- Screenshot available enhancement sections

Recommended schema opportunities to consider:
- LocalBusiness schema
- Organization schema
- Website schema
- Breadcrumb schema
- FAQ schema where appropriate
- Service schema for service businesses
- Product schema for product-based businesses
- Article or BlogPosting schema for blogs
- Review schema only if compliant and legitimately displayed on the website

Stop after Phase 8 and summarize what was captured.

PHASE 9 — Final SEO Audit Report

29. Compile all findings into a professional SEO audit report for the current website/property.

The report must include:

A. Executive Summary
- Overall SEO health summary
- Biggest problems found
- Biggest opportunities
- Whether the site is ready for SEO growth or still has technical blockers

B. Overall Grade
- Give an overall grade from A to F
- Explain the grade clearly
- Do not be too generous if there are sitemap, indexing, internal linking, backlink, canonical, HTTPS, or structured data problems

C. Performance Analysis
- Total clicks
- Total impressions
- CTR
- Average position
- Date range
- Top queries
- Top pages
- Countries
- Devices
- Performance grade
- Screenshots referenced

D. Page Indexing Analysis
- Total indexed pages
- Total not indexed pages
- Indexing rate percentage
- Main reasons pages are not indexed
- Specific affected URLs
- Last crawled dates
- Count of pages with "Last crawled: N/A"
- Identify important pages not indexed
- Indexing grade

E. Sitemap Analysis
- Submitted sitemap URL
- Status
- Submission date
- Last read date
- Discovered pages/videos
- Flag "Couldn't fetch" as critical if present
- Sitemap grade

F. Core Web Vitals Analysis
- Mobile status
- Desktop status
- Field data availability
- Core Web Vitals grade

G. HTTPS Analysis
- HTTPS URLs
- Non-HTTPS URLs
- HTTP/WWW/non-WWW redirect issues
- HTTPS grade

H. Structured Data / Enhancements Analysis
- Enhancements detected
- Missing schema opportunities
- Recommended schema for this type of business
- Structured data grade

I. Manual Actions
- Confirm whether penalties exist
- Manual actions grade

J. Security Issues
- Confirm whether security issues exist
- Security grade

K. Links Analysis
- Total external backlinks
- Top linking sites
- Top linking text
- Total internal links
- Internal linking weaknesses
- Backlink authority issues
- Links grade

L. URL Inspection Findings
Include findings for:
1. Main homepage URL
2. Alternate homepage version, such as WWW/non-WWW or HTTP/HTTPS if applicable
3. One important interior page

For each inspected URL, include:
- Exact URL
- Index status
- Page indexing status
- Discovery method
- Last crawl date
- Crawled as
- Crawl allowed
- Page fetch
- Indexing allowed
- User-declared canonical
- Google-selected canonical
- Screenshot reference

M. Critical Findings to Confirm or Reject Based on Evidence

Check whether the following are true for the current property. Do not assume them. Confirm each one with GSC evidence:

- Only a small percentage of pages are indexed
- Sitemap shows "Couldn't fetch"
- Multiple pages show "Last crawled: N/A"
- Clicks go mostly or entirely to the homepage
- Internal link count is very low
- External backlinks are zero or minimal
- Hash-based URLs appear as separate URLs in GSC
- HTTP, WWW, or non-WWW redirect variants appear in "Page with redirect"
- Canonical tags are missing or unclear
- Structured data is missing
- Important pages are discovered but not indexed
- Important pages are not receiving impressions/clicks
- Preferred domain version is inconsistent between WWW and non-WWW
- Sitemap URLs do not match the preferred canonical version

N. Prioritized Action Plan

Create an 8–10 item action plan ranked by priority.

For each action item include:
- Priority level: Critical, High, Medium, or Low
- Timeline: Immediate, 1–3 days, 1 week, 2–4 weeks, or ongoing
- Exact issue
- Why it matters
- Specific fix
- Expected SEO impact

The action plan should include recommendations around:
- Fixing sitemap submission/fetching problems
- Getting important pages indexed
- Improving internal linking
- Adding or correcting canonical tags
- Fixing HTTP/WWW/non-WWW redirect variants
- Removing or handling hash-based URL problems if present
- Adding structured data/schema
- Building local backlinks
- Improving homepage-to-important-page link flow
- Creating or improving location/service/product/blog pages depending on the business
- Submitting priority URLs for indexing after fixes, but only after I approve it

O. Screenshot Checklist

Include a final checklist showing whether screenshots were captured for:
- Overview
- Performance chart
- Queries
- Pages
- Countries
- Devices
- Page Indexing graph
- Each not-indexed reason detail page
- Sitemaps
- Core Web Vitals
- HTTPS
- Manual Actions
- Security Issues
- Links
- URL Inspection: main homepage
- URL Inspection: alternate homepage version
- URL Inspection: important interior page
- Enhancements / structured data reports

P. Comparison to Previous Audit

If previous audit data is available, compare only SEO patterns, not business details.

Compare:
- Indexing rate
- Sitemap status
- Internal links
- Backlinks
- Homepage dominance
- Hash URL issues
- Structured data issues
- Manual/security status
- WWW/non-WWW consistency

If no previous audit data is available, say:
"No previous audit data was available for comparison."

Final output format:
- Professional SEO audit report
- Clear section headings
- Grades for each section
- Overall grade
- Screenshot checklist
- Prioritized action plan
- No unsupported claims
- No copied findings from any other client unless verified in the current GSC property
