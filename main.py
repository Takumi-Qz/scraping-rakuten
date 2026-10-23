"""楽天商品検索API → Googleスプレッドシート追記ツール"""

import os
import time
from datetime import datetime

import gspread
import requests
from dotenv import load_dotenv

load_dotenv()

RAKUTEN_APP_ID = os.environ["RAKUTEN_APP_ID"]
RAKUTEN_ACCESS_KEY = os.environ["RAKUTEN_ACCESS_KEY"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SHEET_NAME = os.environ["SHEET_NAME"]
SERVICE_ACCOUNT_JSON = os.environ["SERVICE_ACCOUNT_JSON"]
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
HISTORY_SHEET_NAME = "履歴"

API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
# 楽天の「許可されたWebサイト」に登録したドメインに合わせる
ORIGIN = "https://github.com"
KEYWORDS = ["ゲーミングチェア", "ワイヤレスイヤホン", "ドリップコーヒー"]
HEADER = ["キーワード", "商品名", "価格", "レビュー数", "ショップ名", "商品URL", "取得日時"]


def fetch_rakuten(keyword: str, hits: int = 30) -> list[list]:
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "keyword": keyword,
        "hits": hits,
        "sort": "-updateTimestamp",
        "formatVersion": 2,
    }
    for _ in range(3):
        res = requests.get(API_URL, params=params, headers={"Origin": ORIGIN}, timeout=10)
        if res.status_code != 429:
            break
        time.sleep(5)  # レート制限時は待って再試行
    if not res.ok:
        # URLにはアプリID・アクセスキーが含まれるので出力しない
        raise RuntimeError(f"楽天API HTTP {res.status_code}: {res.text[:200]}")
    items = res.json().get("Items", [])

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        [
            keyword,
            item.get("itemName", ""),
            item.get("itemPrice", ""),
            item.get("reviewCount", ""),
            item.get("shopName", ""),
            item.get("itemUrl", "").split("?")[0],  # rafcid（アプリID入り）を除去
            fetched_at,
        ]
        for item in items
    ]


def get_sheet(name: str = SHEET_NAME) -> gspread.Worksheet:
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(HEADER))
        sheet.append_row(HEADER)
        return sheet


def to_price(value) -> int | None:
    try:
        return int(str(value).replace(",", "").replace("¥", "").strip())
    except ValueError:
        return None


def load_prices(rows: list[list]) -> dict[str, int]:
    """シートの行から {商品URL: 価格} を作る（同じURLは下の行＝新しい方を優先）"""
    prices = {}
    for row in rows:
        if len(row) < 6:
            continue
        price = to_price(row[2])
        if row[5] and price is not None:
            prices[row[5]] = price
    return prices


def detect_price_changes(prev_prices: dict[str, int], rows: list[list]) -> list[dict]:
    """前回と価格が変わった商品だけを返す（前回に無い商品は対象外）"""
    changes = []
    for row in rows:
        url, new_price = row[5], to_price(row[2])
        old_price = prev_prices.get(url)
        if old_price is not None and new_price is not None and old_price != new_price:
            changes.append({"name": row[1], "old": old_price, "new": new_price, "url": url})
    return changes


def notify_slack(changes: list[dict]) -> None:
    if not changes:
        return
    if not SLACK_WEBHOOK_URL:
        print("[SKIP] SLACK_WEBHOOK_URL 未設定のため通知しません")
        return
    lines = [f"価格変動 {len(changes)}件"]
    for c in changes:
        lines.append(f"{c['name']}／{c['old']:,}円→{c['new']:,}円／{c['url']}")
    res = requests.post(SLACK_WEBHOOK_URL, json={"text": "\n".join(lines)}, timeout=10)
    res.raise_for_status()


def main() -> None:
    latest_sheet = get_sheet(SHEET_NAME)
    history_sheet = get_sheet(HISTORY_SHEET_NAME)
    prev_rows = latest_sheet.get_all_values()[1:]
    prev_prices = load_prices(prev_rows)

    all_rows, failed = [], set()
    for keyword in KEYWORDS:
        try:
            rows = fetch_rakuten(keyword)
            all_rows.extend(rows)
            print(f"[OK] {keyword}: {len(rows)}件")
        except Exception as e:
            failed.add(keyword)
            print(f"[NG] {keyword}: {e}")
        time.sleep(1)

    if not all_rows:
        print("取得0件のためシートを更新しません")
        return

    history_sheet.append_rows(all_rows)
    latest_sheet.clear()
    # 失敗したキーワードは前回の行を残し、次回の比較元を失わないようにする
    kept = [r for r in prev_rows if r and r[0] in failed]
    latest_sheet.append_rows([HEADER] + all_rows + kept)

    changes = detect_price_changes(prev_prices, all_rows)
    print(f"価格変動: {len(changes)}件")
    try:
        notify_slack(changes)
    except Exception as e:
        print(f"[NG] Slack通知: {e}")


if __name__ == "__main__":
    main()
