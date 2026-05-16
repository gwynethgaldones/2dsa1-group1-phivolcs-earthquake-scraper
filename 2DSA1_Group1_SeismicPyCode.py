import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib3
import warnings
from gspread_formatting import (
    format_cell_range,
    CellFormat,
    TextFormat,
    set_column_width
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

PHIVOLCS_URL = "https://earthquake.phivolcs.dost.gov.ph/"
SHEET_NAME = "PHIVOLCS_Earthquake_Data"
WORKSHEET = "Sheet1"
CREDS_FILE = "credentials.json"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def scrape_phivolcs():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    print("Fetching PHIVOLCS page...")

    response = requests.get(
        PHIVOLCS_URL,
        headers=headers,
        verify=False,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    all_tables = soup.find_all("table")

    if not all_tables:
        print("ERROR: No tables found.")
        return pd.DataFrame()

    main_table = max(
        all_tables,
        key=lambda t: len(t.find_all("tr"))
    )

    rows = []

    for tr in main_table.find_all("tr"):

        cells = [
            td.get_text(separator=" ", strip=True)
            for td in tr.find_all(["td", "th"])
        ]

        if len(cells) < 6:
            continue

        # Skip headers
        if any(
            h in cells[0].lower()
            for h in ["date", "time", "header"]
        ):
            continue

        if cells[0] == "":
            continue

        location_value = cells[5]

        rows.append({
            "date_time_pst": cells[0],
            "latitude": cells[1],
            "longitude": cells[2],
            "depth_km": cells[3],
            "magnitude": cells[4],
            "location": location_value,
        })

    df = pd.DataFrame(rows)

    if df.empty:
        print("WARNING: No rows parsed.")
        return df

    # Extract location detail from parentheses
    df["location_detail"] = (
        df["location"]
        .str.extract(r"\(([^()]*)\)", expand=False)
        .fillna("")
    )

    # Move location_detail beside location
    location_idx = df.columns.get_loc("location")

    location_detail_col = df.pop("location_detail")

    df.insert(
        location_idx + 1,
        "location_detail",
        location_detail_col
    )

    # Add scrape timestamp
    df.insert(
        0,
        "scraped_at",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    # Convert numeric columns
    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["depth_km"] = pd.to_numeric(
        df["depth_km"],
        errors="coerce"
    )

    df["magnitude"] = pd.to_numeric(
        df["magnitude"],
        errors="coerce"
    )

    print(f"Scraped {len(df)} records.")

    return df


def auto_resize_columns(sheet, df):

    for idx, column in enumerate(df.columns, start=1):

        max_length = max(
            df[column].astype(str).map(len).max(),
            len(column)
        )

        adjusted_width = (max_length + 4) * 9

        set_column_width(
            sheet,
            chr(64 + idx),
            adjusted_width
        )


def format_headers(sheet):

    header_format = CellFormat(
        textFormat=TextFormat(
            bold=True,
            fontSize=12
        )
    )

    format_cell_range(
        sheet,
        "1:1",
        header_format
    )


def rebuild_sheet(sheet, df_clean):

    print("Rebuilding worksheet...")

    # Clear sheet
    sheet.clear()

    # Resize sheet
    sheet.resize(
        rows=len(df_clean) + 5,
        cols=len(df_clean.columns)
    )

    # Upload headers
    sheet.update(
        "A1",
        [df_clean.columns.tolist()]
    )

    # Upload rows
    if not df_clean.empty:

        sheet.append_rows(
            df_clean.values.tolist(),
            value_input_option="USER_ENTERED"
        )

    # Format headers
    format_headers(sheet)

    # Resize columns
    auto_resize_columns(sheet, df_clean)

    print(f"Worksheet rebuilt with {len(df_clean)} rows.")


def upload_to_sheets(df):

    if df.empty:
        print("Nothing to upload.")
        return

    print("Connecting to Google Sheets...")

    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET)

    df_clean = df.astype(str)

    existing_data = sheet.get_all_values()

    # Empty sheet
    if (
        not existing_data
        or existing_data == [[]]
        or len(existing_data) == 0
    ):

        print("Empty sheet detected.")

        rebuild_sheet(sheet, df_clean)

        return

    existing_headers = existing_data[0]

    expected_headers = df_clean.columns.tolist()

    # Rebuild if headers mismatch
    if existing_headers != expected_headers:

        print("Header mismatch detected.")

        rebuild_sheet(sheet, df_clean)

        return

    existing_df = pd.DataFrame(
        existing_data[1:],
        columns=existing_headers
    )

    existing_times = set(
        existing_df["date_time_pst"]
        .astype(str)
        .tolist()
    )

    new_rows_df = df_clean[
        ~df_clean["date_time_pst"].isin(existing_times)
    ]

    if new_rows_df.empty:

        print("No new records.")

        return

    # Append new rows
    sheet.append_rows(
        new_rows_df.values.tolist(),
        value_input_option="USER_ENTERED"
    )

    # Re-apply formatting
    format_headers(sheet)

    auto_resize_columns(sheet, df_clean)

    print(f"Appended {len(new_rows_df)} new record(s).")


if __name__ == "__main__":

    try:

        print("Starting PHIVOLCS scraper...")

        df = scrape_phivolcs()

        upload_to_sheets(df)

        print("Script completed successfully.")

    except Exception as e:

        print(f"ERROR: {e}")

        raise
