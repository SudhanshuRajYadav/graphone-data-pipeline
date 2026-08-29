"""Pushes all vertical CSVs into a Google Sheet, one tab per vertical."""
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def export_to_sheets(service_account_json_path, sheet_id, files_and_tabs):
    creds = Credentials.from_service_account_file(service_account_json_path, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    try:
        sh.del_worksheet(sh.worksheet("Sheet1"))
    except Exception:
        pass

    for tab_name, csv_file in files_and_tabs.items():
        df = pd.read_csv(csv_file).fillna("")
        ws = sh.add_worksheet(title=tab_name, rows=len(df) + 10, cols=len(df.columns) + 2)
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"{tab_name}: {len(df)} rows uploaded")

    return sh.url

if __name__ == "__main__":
    FILES_AND_TABS = {
        "Startups": "startups.csv", "Products": "products.csv",
        "Research Papers": "research_papers.csv", "Jobs": "jobs.csv",
        "News": "news.csv", "Entity Mapping Log": "entity_mapping_log.csv",
    }
    url = export_to_sheets("service_account.json", "YOUR_SHEET_ID", FILES_AND_TABS)
    print("Sheet URL:", url)
