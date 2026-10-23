# scraping.rakuten

## 概要
楽天ウェブサービスの商品検索API（IchibaItem/Search/20220601）で複数キーワードを検索し、結果をGoogleスプレッドシートに追記するツールです。

取得項目：キーワード / 商品名 / 価格 / レビュー数 / ショップ名 / 商品URL / 取得日時

- Python 3.10+
- 検索キーワードは `main.py` の `KEYWORDS` で指定

## 1. 楽天ウェブサービスのアプリID取得
1. [Rakuten Developers](https://webservice.rakuten.co.jp/) に楽天会員でログイン
2. 「アプリID発行」からアプリ名・URLなどを入力して登録
3. 発行された **アプリID（applicationId）** を控える

## 2. Google Cloud でサービスアカウント作成〜JSONキー発行
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成（既存でも可）
2. 「APIとサービス」→「ライブラリ」で **Google Sheets API** を有効化
   - あわせて **Google Drive API** も有効化しておく（gspread がスプレッドシートを開く際に使用）
3. 「IAMと管理」→「サービスアカウント」→「サービスアカウントを作成」
   - 名前を入力して作成（ロールの付与は不要）
4. 作成したサービスアカウントを開き「鍵」タブ →「鍵を追加」→「新しい鍵を作成」→ **JSON**
5. ダウンロードされたJSONをプロジェクト直下に `service_account.json` として配置

## 3. スプレッドシートをサービスアカウントに共有
1. 書き込み先のGoogleスプレッドシートを作成（または既存のものを開く）
2. 右上「共有」→ サービスアカウントのメールアドレス（`xxx@<project>.iam.gserviceaccount.com`、JSON内の `client_email`）を入力
3. 権限を **編集者** にして共有
4. URL `https://docs.google.com/spreadsheets/d/<スプレッドシートID>/edit` の `<スプレッドシートID>` 部分を控える

## 4. .env の設定
```bash
cp .env.example .env
```

| 変数 | 内容 |
|---|---|
| `RAKUTEN_APP_ID` | 楽天アプリID |
| `SPREADSHEET_ID` | 書き込み先スプレッドシートID |
| `SHEET_NAME` | シート名（存在しなければヘッダー付きで自動作成。初期値：価格収集） |
| `SERVICE_ACCOUNT_JSON` | サービスアカウントJSONのパス |

## 5. 実行方法
### 仮想環境の作成
```bash
python -m venv .venv   # Mac で python がない場合は python3
```

### 有効化
Mac / Linux：
```bash
source .venv/bin/activate
```

Windows（コマンドプロンプト）：
```bat
.venv\Scripts\activate.bat
```

Windows（PowerShell）：
```powershell
.venv\Scripts\Activate.ps1
```
※ PowerShell で実行ポリシーエラーになる場合は `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` を一度実行

### 依存インストールと実行
```bash
pip install -r requirements.txt
python main.py
```

キーワードごとに `[OK] ゲーミングチェア: 30件` / `[NG] ...: エラー内容` が表示されます。

## 注意点
- `.env` と `service_account.json` は秘密情報です。Git にコミットしないでください（`.gitignore` で除外済み）
- API連打防止のため、1キーワードごとに1秒待機します。楽天APIの利用規約・リクエスト上限を守ってください
- 1キーワードの取得に失敗しても、他のキーワードの処理は続行します
- 実行のたびに行が **追記** されます（重複除去はしません）
- 1キーワードあたりの取得件数は最大30件（`hits` の上限）です
- 楽天APIの仕様変更（認証方式など）で401/403になる場合は、Rakuten Developers の最新ドキュメントを確認してください
