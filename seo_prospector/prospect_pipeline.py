#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-command RGV rank-5-to-10 lead pipeline.

Swap the profession and the city/cities -- it runs end to end:

    scrape (Places rank 5-10 + email/Facebook enrichment, one CSV per city)
        -> upload to Twenty CRM under a "<PROFESSION> LEADS |" group

This is the reusable skill entry point. Lawyers today, dentists tomorrow,
roofers next week -- only --profession and the cities change.

Examples:
    python prospect_pipeline.py --profession "attorney" --cities "Harlingen,McAllen,Mission"
    python prospect_pipeline.py --profession "dentist"  --city "McAllen"
    python prospect_pipeline.py --profession "roofing contractor" \\
        --cities "Brownsville,Edinburg" --dry-run
    python prospect_pipeline.py --profession "chiropractor" --city "Pharr" --no-upload

Steps:
    1. rank_prospector.py        Places text search, slice rank 5-10, enrich
                                 phone/website/email/Facebook, score,
                                 write output/<slug>_<City>_<ts>.csv per city.
    2. upload_leads_to_twenty.py Create one Twenty CRM company per firm under
                                 the "<PROFESSION> LEADS |" prefix (its own
                                 group, separate from "HS |" and "SEO |").

Flags:
    --profession NAME   (required) trade to prospect -- drives the Google
                        search term, the CSV name, and the CRM group name.
    --city NAME         single city.
    --cities "A,B,C"    comma-separated list of cities.
                        (one of --city / --cities is required.)
    --no-enrich         skip the email/Facebook enrichment step (faster).
    --rank-min N        low end of the rank band (default 5).
    --rank-max N        high end of the rank band (default 10).
    --no-upload         stop after the CSVs -- do not touch Twenty CRM.
    --dry-run           run the scrape for real, then PREVIEW the upload
                        (lists the companies, makes no CRM writes).

Note: --dry-run only previews the upload step; the scrape still calls the
Places API and costs money. To preview the search plan with zero API calls,
run rank_prospector.py --dry-run directly.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PY = sys.executable


def run_step(label: str, cmd: list[str]) -> None:
    print("\n" + "=" * 70)
    print(f"  {label}")
    print(f"  $ {' '.join(cmd)}")
    print("=" * 70 + "\n", flush=True)
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"\n[FATAL] {label} failed (exit {result.returncode}). "
              "Pipeline stopped.", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="RGV rank-5-10 lead pipeline: scrape -> Twenty CRM, "
                    "for any profession.")
    parser.add_argument("--profession", required=True,
                        help='Trade to prospect, e.g. "attorney", "dentist", '
                             '"roofing contractor".')
    parser.add_argument("--city", help="Single city.")
    parser.add_argument("--cities", help='Comma-separated cities, e.g. '
                                         '"Harlingen,McAllen,Mission".')
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip email/Facebook enrichment.")
    parser.add_argument("--rank-min", type=int, help="Rank band low end (default 5).")
    parser.add_argument("--rank-max", type=int, help="Rank band high end (default 10).")
    parser.add_argument("--no-upload", action="store_true",
                        help="Stop after the CSVs -- do not upload to Twenty CRM.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview the upload step instead of writing to the CRM.")
    args = parser.parse_args()

    if not args.city and not args.cities:
        parser.error("provide --city or --cities (a full 16-city sweep is a "
                     "deliberate choice -- run rank_prospector.py directly for that).")

    where = args.cities or args.city
    print(f"RGV rank-5-10 lead pipeline")
    print(f"  Profession : {args.profession}")
    print(f"  Cities     : {where}")
    print(f"  Enrichment : {'OFF' if args.no_enrich else 'ON (email + Facebook)'}")
    print(f"  Upload     : {'PREVIEW (dry-run)' if args.dry_run else ('OFF' if args.no_upload else 'ON')}")
    print(f"  CRM group  : {args.profession.strip().upper()} LEADS |")

    # ---- Step 1: scrape -------------------------------------------------
    scrape = [PY, "rank_prospector.py", "--category", args.profession,
              "--separate-by-city"]
    if args.cities:
        scrape += ["--cities", args.cities]
    elif args.city:
        scrape += ["--city", args.city]
    if args.no_enrich:
        scrape.append("--no-enrich")
    if args.rank_min is not None:
        scrape += ["--rank-min", str(args.rank_min)]
    if args.rank_max is not None:
        scrape += ["--rank-max", str(args.rank_max)]
    run_step("STEP 1/2  Scrape rank 5-10 + enrich", scrape)

    # ---- Step 2: upload -------------------------------------------------
    if args.no_upload:
        print("\n" + "=" * 70)
        print("  --no-upload set: CSVs written to output/, Twenty CRM untouched.")
        print("  Upload later with:")
        print(f'    python upload_leads_to_twenty.py --profession "{args.profession}"')
        print("=" * 70)
        return

    upload = [PY, "upload_leads_to_twenty.py", "--profession", args.profession]
    if args.dry_run:
        upload.append("--dry-run")
    label = ("STEP 2/2  Preview upload to Twenty CRM" if args.dry_run
             else "STEP 2/2  Upload to Twenty CRM")
    run_step(label, upload)

    print("\n" + "=" * 70)
    print("  Pipeline complete.")
    if args.dry_run:
        print("  That was a preview. Re-run without --dry-run to write the CRM.")
    else:
        print(f"  Open Twenty CRM: http://localhost:3000/objects/companies")
        print(f"  Search '{args.profession.strip().upper()} LEADS |' to see the group.")
    print("=" * 70)


if __name__ == "__main__":
    main()
