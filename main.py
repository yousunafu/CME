import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from datetime import datetime

# --- 1. スプレッドシートの認証設定 ---
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# ★注意: ローカルで動かす場合は、環境変数設定が面倒なので
# JSONキーのファイル名を直接指定するのが一番簡単です
# GitHub Actions実行時は環境変数から読み込む
if os.environ.get("GCP_SA_KEY"):
    # GitHub Actionsの場合
    key_json = os.environ.get("GCP_SA_KEY")
    creds = Credentials.from_service_account_info(json.loads(key_json), scopes=scopes)
else:
    # ローカル実行の場合: 同じフォルダに service_account.json を置いてください
    SERVICE_ACCOUNT_FILE = 'service_account.json'
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    else:
        raise FileNotFoundError(f"認証ファイルが見つかりません: {SERVICE_ACCOUNT_FILE}")

gc = gspread.authorize(creds)

# --- 2. CME FedWatchからスクレイピング ---
def scrape_fed_data():
    with sync_playwright() as p:
        # headless=False にすると、実際にブラウザが動く様子が見えます（デバッグに最適）
        # 本番環境では headless=True に変更するとバックグラウンドで実行されます
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # CMEのサイトへ移動
        print("サイトへアクセス中...")
        page.goto("https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html", timeout=60000)
        
        # iframe（データが入っている箱）を探す
        # データの読み込みに時間がかかるので長めに待つ
        print("データを待機中...")
        frame = page.frame_locator("iframe[src*='quikstrike']")
        
        # 確率が表示されているセルを探す
        # セレクタは変わる可能性がありますが、まずはこれでトライ
        target = frame.locator("td.probability-cell").first
        target.wait_for(timeout=30000)
        
        prob_text = target.inner_text()
        print(f"取得できたデータ: {prob_text}")
        
        browser.close()
        return prob_text.replace('%', '').strip()

# --- 3. スプレッドシートへ書き込み ---
def update_sheet(new_val):
    sh = gc.open("CME定期調査").sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    all_values = sh.get_all_values()
    last_val = 0
    if len(all_values) > 1:
        try:
            last_val = float(all_values[-1][1])
        except:
            last_val = 0
    
    diff = float(new_val) - last_val
    sh.append_row([now, new_val, diff])
    print("スプレッドシートへの書き込み完了")

if __name__ == "__main__":
    try:
        data = scrape_fed_data()
        update_sheet(data)
        print(f"成功: データ {data} をスプレッドシートに書き込みました")
    except Exception as e:
        print(f"エラー: {e}")
        raise
