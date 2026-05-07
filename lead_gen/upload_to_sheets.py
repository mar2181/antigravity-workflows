#!/usr/bin/env python3
"""Populate Google Sheet with all leads via Sheets API (no Drive API needed)."""

import csv
import json
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).parent
CRED_PATH = SCRIPT_DIR.parent / "gcp-credentials" / "antigravity-487918-indexing-api.json"
CSV_PATH = SCRIPT_DIR / "output" / "rgv_no_website_only_2026-05-06.csv"

# The sheet created earlier via Drive MCP (owned by hssolutions2181@gmail.com)
# We'll create a new one since we can't access that
SHEET_TITLE = f"RGV No-Website Leads 2026-05-06"

def main():
    creds = Credentials.from_service_account_file(
        str(CRED_PATH),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    # Read CSV
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    print(f"Read {len(rows)} rows ({len(rows)-1} data rows)")

    # Create sheet directly via Sheets API
    sheets_service = build("sheets", "v4", credentials=creds)

    spreadsheet = sheets_service.spreadsheets().create(
        body={"properties": {"title": SHEET_TITLE}},
        fields="spreadsheetId,spreadsheetUrl"
    ).execute()

    sheet_id = spreadsheet["spreadsheetId"]
    sheet_url = spreadsheet["spreadsheetUrl"]
    print(f"Created: {sheet_url}")

    # Write all data in one batch update
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows}
    ).execute()
    print(f"Wrote {len(rows)} rows")

    # Format header
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"bold": True},
                                "backgroundColorStyle": {
                                    "rgbColor": {"red": 0.12, "green": 0.12, "blue": 0.12}
                                },
                            }
                        },
                        "fields": "textFormat.bold,backgroundColorStyle",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": 0,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
            ]
        },
    ).execute()
    print("Header formatted")

    print(f"\nDone! {len(rows)-1} leads uploaded")
    print(f"Sheet URL: {sheet_url}")


if __name__ == "__main__":
    main()
