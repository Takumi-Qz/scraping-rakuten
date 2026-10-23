"""楽天商品検索API → Googleスプレッドシート追記ツール"""

import os
import time
from datetime import datetime

import gspread
import requests
from dotenv import load_dotenv

load_dotenv()

RAKUTEN_APP_ID = os.environ["RAKUTEN_APP_ID"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SHEET_NAME = os.environ["SHEET_NAME"]
SERVICE_ACCOUNT_JSON = os.environ["SERVICE_ACCOUNT_JSON"]

API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
KEYWORDS = ["ゲーミングチェア", "ワイヤレスイヤホン", "ドリップコーヒー"]
HEADER = ["キーワード", "商品名", "価格", "レビュー数", "ショップ名", "商品URL", "取得日時"]


def fetch_rakuten(keyword: str, hits: int = 30) -> list[list]:
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "keyword": keyword,
        "hits": hits,
        "sort": "-updateTimestamp",
        "formatVersion": 2,
    }
    res = requests.get(API_URL, params=params, timeout=10)
    res.raise_for_status()
    items = res.json().get("Items", [])

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        [
            keyword,
            item.get("itemName", ""),
            item.get("itemPrice", ""),
            item.get("reviewCount", ""),
            item.get("shopName", ""),
            item.get("itemUrl", ""),
            fetched_at,
        ]
        for item in items
    ]


def get_sheet() -> gspread.Worksheet:
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    try:
        return spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(HEADER))
        sheet.append_row(HEADER)
        return sheet


def main() -> None:
    sheet = get_sheet()
    for keyword in KEYWORDS:
        try:
            rows = fetch_rakuten(keyword)
            if rows:
                sheet.append_rows(rows)
            print(f"[OK] {keyword}: {len(rows)}件")
        except Exception as e:
            print(f"[NG] {keyword}: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
