import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from datetime import datetime

# --- 1. スプレッドシートの認証設定 ---
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
key_json = os.environ.get("GCP_SA_KEY")
if not key_json:
    raise ValueError("GCP_SA_KEY is not set in environment variables")

creds = Credentials.from_service_account_info(json.loads(key_json), scopes=scopes)
gc = gspread.authorize(creds)

# --- 2. CME FedWatchからスクレイピング ---
def scrape_fed_data():
    max_retries = 3
    
    with sync_playwright() as p:
        # Chromiumを使用（ボット検知回避設定付き）
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        for attempt in range(max_retries):
            try:
                # CMEサイトへ移動
                page.goto("https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html", 
                          wait_until="networkidle", timeout=60000)
                
                # QuikStrikeのiframeを探す
                frame_element = page.frame_locator("iframe[src*='quikstrike']")
                # 確率が載っているテーブルが表示されるまで待機
                target_cell = frame_element.locator("td.probability-cell").first
                target_cell.wait_for(timeout=30000)
                
                prob_text = target_cell.inner_text()
                browser.close()
                return prob_text.replace('%', '').strip()

            except Exception as e:
                print(f"試行 {attempt + 1} 失敗: {e}")
                time.sleep(10)
                if attempt == max_retries - 1:
                    browser.close()
                    raise e

# --- 3. スプレッドシートへ書き込み ---
def update_sheet(new_val):
    # スプレッドシート名が正しいか確認してください
    sh = gc.open("CME定期調査").sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    all_values = sh.get_all_values()
    last_val = 0
    if len(all_values) > 1:
        # 前回の数値を取得
        try:
            last_val = float(all_values[-1][1])
        except:
            last_val = 0
    
    diff = float(new_val) - last_val
    sh.append_row([now, new_val, diff])

if __name__ == "__main__":
    try:
        data = scrape_fed_data()
        update_sheet(data)
        print(f"更新成功: {data}")
    except Exception as e:
        print(f"最終エラー: {e}")
        raise
