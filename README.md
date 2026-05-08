# 🌏 Seismic Risk Mapping in the Philippines
### DS4155 - Artificial Intelligence | 2DSA1 Group 1

A fully automated, zero-cost data pipeline that scrapes live earthquake bulletins from PHIVOLCS, stores them in Google Sheets, and visualizes them on a Tableau Public dashboard — updated every 6 hours automatically.

---

## Data Source

| | |
|---|---|
| **Provider** | Philippine Institute of Volcanology and Seismology (PHIVOLCS), DOST |
| **URL** | https://earthquake.phivolcs.dost.gov.ph/ |
| **Method** | Python web scraper (BeautifulSoup + requests) |
| **Update Frequency** | Every 6 hours via GitHub Actions |

### Columns Collected
| Column | Description |
|---|---|
| `scraped_at` | Timestamp of when the data was collected (UTC) |
| `date_time_pst` | Date and time of earthquake (Philippine Standard Time) |
| `latitude` | Latitude coordinate of the epicenter |
| `longitude` | Longitude coordinate of the epicenter |
| `depth_km` | Depth of the earthquake in kilometers |
| `magnitude` | Earthquake magnitude |
| `location` | Descriptive location of the earthquake |

---

## Tech Stack (100% Free)

| Layer | Tool |
|---|---|
| Extraction | Python 3.11 + BeautifulSoup4 + requests |
| Storage | Google Sheets (via Google Sheets API) |
| Automation | GitHub Actions (cron: every 6 hours) |
| Visualization | Tableau Public (Google Drive connector, 24-hr sync) |

---

## Cleaning Logic

- `latitude`, `longitude`, `depth_km`, `magnitude` are cast to numeric using `pd.to_numeric(..., errors='coerce')` — unreadable values become `NULL`
- Duplicate records are removed by checking `date_time_pst` before appending to Google Sheets
- Extra whitespace in location names is stripped during scraping

---

## Repository Structure
├── 2DSA1_Group1_SeismicPyCode.py   # Main scraper + Google Sheets upload script
├── requirements.txt                 # Python dependencies
├── .github/
│   └── workflows/
│       └── scrape.yml               # GitHub Actions automation (runs every 6 hours)
└── README.md                        # This file 

---

## Group Members
2DSA1 - A.Y 2025-2026 
- FELICIANO, Gia Lawrein
- GALDONES, Gwyneth M.
- MENDIOLA, Ma. Joliana Bernise
- PALAD, Juan Miguel
- RUAMAR, Adrienne Mae
- VELILLA, Ethan Chelsea

## Course
Information Presentation and Visualization 
