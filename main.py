import os
import json
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from datetime import datetime

# --- 1. スプレッドシートの認証設定 ---
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# GitHubのSecretsからJSONキーを読み込む設定
key_json = os.environ.get("GCP_SA_KEY")
if not key_json:
    raise ValueError("GCP_SA_KEY is not set in environment variables")

creds = Credentials.from_service_account_info(json.loads(key_json), scopes=scopes)
gc = gspread.authorize(creds)

# --- 2. CME FedWatchからスクレイピング ---
def scrape_fed_data():
    with sync_playwright() as p:
        # ブラウザ起動
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html")
        
        # クイックストライクのiframe（データ本体）を待機して取得
        # セレクタは会合日の確率テーブルを指定（※サイト構造変更で要調整）
        frame = page.frame_locator("iframe[src*='quikstrike']")
        frame.locator(".grid-container").wait_for() # 表が出るまで待つ
        
        # 例：次回の会合日の「据え置き」確率を取得
        # ※以下のセレクタはイメージです。実際のサイト構造に合わせて微調整が必要です。
        prob_unchanged = frame.locator("td.probability-cell").first.inner_text() 
        
        browser.close()
        return prob_unchanged.replace('%', '') # 数字だけ抜き出す

# --- 3. スプレッドシートへ書き込み ---
def update_sheet(new_val):
    sh = gc.open("CME定期調査").sheet1
    
    # 現在の日時
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 最後の行の値を取得して変化を計算
    all_values = sh.get_all_values()
    last_val = 0
    if len(all_values) > 1:
        last_val = float(all_values[-1][1]) # B列（最新値）を取得
    
    diff = float(new_val) - last_val
    
    # 新しい行を追加 [日時, 最新値, 変化]
    sh.append_row([now, new_val, diff])

if __name__ == "__main__":
    data = scrape_fed_data()
    update_sheet(data)
