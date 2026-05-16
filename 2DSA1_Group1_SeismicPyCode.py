import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

PHIVOLCS_URL = "https://earthquake.phivolcs.dost.gov.ph/"
SHEET_NAME  = "PHIVOLCS_Earthquake_Data"
WORKSHEET   = "Sheet1"
CREDS_FILE  = "credentials.json"

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

    # Get the largest table
    main_table = max(all_tables, key=lambda t: len(t.find_all("tr")))

    rows = []

    for tr in main_table.find_all("tr"):

        cells = [
            td.get_text(separator=" ", strip=True)
            for td in tr.find_all(["td", "th"])
        ]

        if len(cells) < 6:
            continue

        # Skip headers
        if any(h in cells[0].lower() for h in ["date", "time", "header"]):
            continue

        if cells[0] == "":
            continue

        location_value = cells[5] if len(cells) > 5 else ""

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

    # Extract text inside parentheses
    df["location_detail"] = (
        df["location"]
        .str.extract(r"\(([^()]*)\)", expand=False)
        .fillna("")
    )

    # Place new column beside location column
    location_idx = df.columns.get_loc("location")
    col = df.pop("location_detail")
    df.insert(location_idx + 1, "location_detail", col)

    # Add scrape timestamp
    df.insert(
        0,
        "scraped_at",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    # Convert numeric columns
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["depth_km"] = pd.to_numeric(df["depth_km"], errors="coerce")
    df["magnitude"] = pd.to_numeric(df["magnitude"], errors="coerce")

    print(f"Scraped {len(df)} records.")

    return df

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

    # Convert all values to string
    df_clean = df.astype(str)

    existing_data = sheet.get_all_values()

    # If sheet is empty
    if (
        not existing_data
        or existing_data == [[]]
        or len(existing_data) <= 1
    ):
        sheet.clear()

        sheet.append_row(df_clean.columns.tolist())

        sheet.append_rows(
            df_clean.values.tolist(),
            value_input_option="USER_ENTERED"
        )

        print(f"Wrote header + {len(df_clean)} rows.")
        return

    existing_df = pd.DataFrame(
        existing_data[1:],
        columns=existing_data[0]
    )

    # If headers changed, rebuild sheet
    if list(existing_df.columns) != list(df_clean.columns):

        print("Header mismatch detected. Rebuilding sheet...")

        sheet.clear()

        sheet.append_row(df_clean.columns.tolist())

        sheet.append_rows(
            df_clean.values.tolist(),
            value_input_option="USER_ENTERED"
        )

        print(f"Rebuilt sheet with {len(df_clean)} rows.")
        return

    # Prevent duplicate uploads
    existing_times = set(
        existing_df["date_time_pst"].tolist()
    )

    new_rows_df = df_clean[
        ~df_clean["date_time_pst"].isin(existing_times)
    ]

    if new_rows_df.empty:
        print("No new records. Sheet is already up to date.")
        return

    sheet.append_rows(
        new_rows_df.values.tolist(),
        value_input_option="USER_ENTERED"
    )

    print(f"Appended {len(new_rows_df)} new record(s).")

if __name__ == "__main__":

    df = scrape_phivolcs()

    upload_to_sheets(df)
