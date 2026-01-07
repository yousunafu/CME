import os
import json
import time
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
    max_retries = 3
    retry_delay = 5
    browsers_to_try = ['chromium', 'firefox']  # Chromiumが失敗したらFirefoxを試す
    
    for browser_type in browsers_to_try:
        for attempt in range(max_retries):
            try:
                with sync_playwright() as p:
                    # ブラウザ起動（HTTP/2を無効化、より現実的な設定）
                    if browser_type == 'chromium':
                        browser = p.chromium.launch(
                            headless=True,
                            args=[
                                '--disable-blink-features=AutomationControlled',
                                '--disable-http2',  # HTTP/2を無効化
                                '--disable-dev-shm-usage',
                                '--no-sandbox',
                                '--disable-setuid-sandbox',
                                '--disable-web-security',
                                '--disable-features=IsolateOrigins,site-per-process',
                            ]
                        )
                    else:  # firefox
                        browser = p.firefox.launch(
                            headless=True
                        )
                
                # コンテキスト作成（ユーザーエージェントとビューポートを設定）
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate',  # brを削除（HTTP/2関連）
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                    ignore_https_errors=True  # HTTPSエラーを無視
                )
                
                page = context.new_page()
                
                # ページ遷移（domcontentloadedを使用、HTTP/2エラーを回避）
                try:
                    page.goto(
                        "https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html",
                        wait_until="domcontentloaded",  # networkidleから変更
                        timeout=60000
                    )
                except Exception as e:
                    print(f"ページ遷移エラー（{browser_type}、試行 {attempt + 1}/{max_retries}）: {e}")
                    browser.close()
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    # このブラウザタイプでの全試行が失敗した場合、次のブラウザタイプを試す
                    if browser_type == 'chromium' and 'firefox' in browsers_to_try:
                        print(f"Chromiumでの試行が失敗したため、Firefoxに切り替えます")
                        break
                    raise
                
                # 少し待機してページが完全に読み込まれるのを待つ
                time.sleep(3)
                
                # クイックストライクのiframe（データ本体）を待機して取得
                # セレクタは会合日の確率テーブルを指定（※サイト構造変更で要調整）
                try:
                    frame = page.frame_locator("iframe[src*='quikstrike']")
                    frame.locator(".grid-container").wait_for(timeout=30000) # 表が出るまで待つ
                except Exception as e:
                    print(f"iframe読み込みエラー（{browser_type}、試行 {attempt + 1}/{max_retries}）: {e}")
                    # ページのHTMLを確認（デバッグ用）
                    print("ページタイトル:", page.title())
                    print("ページURL:", page.url)
                    browser.close()
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    # このブラウザタイプでの全試行が失敗した場合、次のブラウザタイプを試す
                    if browser_type == 'chromium' and 'firefox' in browsers_to_try:
                        print(f"Chromiumでの試行が失敗したため、Firefoxに切り替えます")
                        break
                    raise
                
                # 例：次回の会合日の「据え置き」確率を取得
                # ※以下のセレクタはイメージです。実際のサイト構造に合わせて微調整が必要です。
                try:
                    prob_unchanged = frame.locator("td.probability-cell").first.inner_text(timeout=10000)
                except Exception as e:
                    print(f"データ取得エラー（試行 {attempt + 1}/{max_retries}）: {e}")
                    # 代替セレクタを試す
                    try:
                        # より一般的なセレクタを試す
                        prob_unchanged = frame.locator("td").first.inner_text(timeout=10000)
                    except:
                        browser.close()
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        raise
                
                browser.close()
                return prob_unchanged.replace('%', '').strip() # 数字だけ抜き出す
                
            except Exception as e:
                print(f"スクレイピングエラー（{browser_type}、試行 {attempt + 1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                # このブラウザタイプでの全試行が失敗した場合、次のブラウザタイプを試す
                if browser_type == 'chromium' and 'firefox' in browsers_to_try:
                    print(f"Chromiumでの試行が失敗したため、Firefoxに切り替えます")
                    break
                raise Exception(f"スクレイピングに失敗しました（{browser_type}、{max_retries}回試行）: {e}")
    
    raise Exception("すべてのブラウザでのスクレイピングに失敗しました")

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
    try:
        data = scrape_fed_data()
        update_sheet(data)
        print(f"成功: データ {data} をスプレッドシートに書き込みました")
    except Exception as e:
        print(f"エラー: {e}")
        # エラーをスプレッドシートに記録（オプション）
        try:
            sh = gc.open("CME定期調査").sheet1
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            sh.append_row([now, f"エラー: {str(e)[:100]}", "N/A"])
        except:
            pass
        raise  # GitHub Actionsでエラーとして記録されるように
