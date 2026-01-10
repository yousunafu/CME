import os
import json
import time
import re
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from datetime import datetime

# ==================== 設定定数 ====================
# スクレイピング設定
MAX_RETRIES = 3
RETRY_DELAY = 10
PAGE_LOAD_TIMEOUT = 120000  # ミリ秒
ELEMENT_WAIT_TIMEOUT = 10000  # ミリ秒
HEADLESS_MODE = False  # デバッグ時はFalse、本番はTrue推奨

# 待機時間（秒）
WAIT_AFTER_PAGE_LOAD = 3
WAIT_AFTER_IFRAME_LOAD = 5
WAIT_AFTER_TABLE_LOAD = 5
WAIT_FOR_TABLE_DATA = 3

# 比較閾値
MIN_CHANGE_THRESHOLD = 0.1  # 0.1%以上の変化で矢印を表示

# スプレッドシート設定
SPREADSHEET_NAME = "CME定期調査"
PREVIOUS_SHEET_NAME = "前回値"
SERVICE_ACCOUNT_FILE = 'service_account.json'

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
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    else:
        raise FileNotFoundError(f"認証ファイルが見つかりません: {SERVICE_ACCOUNT_FILE}")

gc = gspread.authorize(creds)

# --- 2. CME FedWatchからスクレイピング ---

def _launch_browser(playwright):
    """Chromiumブラウザを起動してコンテキストとページを作成"""
    # 元のコードと同じく、channel指定なしでPlaywrightのChromiumを使用
    browser = playwright.chromium.launch(
        headless=HEADLESS_MODE,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-http2',  # HTTP/2を無効化（重要）
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    page = context.new_page()
    return browser, page

def _navigate_to_page(page, url, attempt):
    """指定されたURLにページを遷移（元のコードと同じ動作）"""
    print(f"サイトへアクセス中... (chromium, 試行 {attempt + 1}/{MAX_RETRIES})")
    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
    print("ページ遷移成功")
    # 追加の待機時間（元のコードと同じ）
    time.sleep(WAIT_AFTER_PAGE_LOAD)
    
    # ページが完全に読み込まれるまで待機（元のコードと同じ）
    print("ページの読み込みを待機中...")
    time.sleep(5)  # 元のコードと同じ固定時間待機
    
    # ページが読み込まれたか確認
    print(f"ページタイトル: {page.title()}")
    print(f"現在のURL: {page.url}")

def _find_iframe(page):
    """ページ内のiframeを検索"""
    print("iframeを探しています...")
    iframe_selectors = [
        "iframe[src*='quikstrike']",
        "iframe[src*='fedwatch']",
        "iframe"
    ]
    
    for selector in iframe_selectors:
        try:
            iframes = page.locator(selector).all()
            if iframes:
                print(f"iframeが見つかりました: {selector} ({len(iframes)}個)")
                return page.frame_locator(selector).first
        except Exception:
            continue
    
    # iframeが見つからない場合のデバッグ情報
    print("iframeが見つかりませんでした。ページの構造を確認します...")
    page_content = page.content()
    if "quikstrike" in page_content.lower() or "fedwatch" in page_content.lower():
        print("ページ内に'quikstrike'または'fedwatch'の文字列が見つかりました")
    else:
        print("ページ内に'quikstrike'または'fedwatch'の文字列が見つかりませんでした")
    raise Exception("iframeが見つかりませんでした")

def _click_probabilities(frame):
    """Probabilitiesタブをクリック"""
    print("'Probabilities'をクリックしています...")
    prob_selectors = [
        "text=Probabilities",
        "a:has-text('Probabilities')",
        "[data-item='Probabilities']",
        "li:has-text('Probabilities')",
        ".nav-item:has-text('Probabilities')"
    ]
    
    for selector in prob_selectors:
        try:
            prob_link = frame.locator(selector).first
            if prob_link.is_visible(timeout=ELEMENT_WAIT_TIMEOUT // 2):
                print(f"Probabilitiesリンクが見つかりました: {selector}")
                prob_link.click()
                print("Probabilitiesをクリックしました")
                return True
        except Exception as e:
            print(f"セレクタ '{selector}' でエラー: {e}")
            continue
    
    print("警告: Probabilitiesが見つかりませんでした。既に選択されている可能性があります。")
    return False

def _find_table(frame):
    """iframe内のテーブルを検索（元のコードと同じ）"""
    print("テーブル全体からデータを取得中...")
    
    table_selectors = ["table", "table tbody"]
    for selector in table_selectors:
        try:
            table_locator = frame.locator(selector).first
            table_locator.wait_for(state="attached", timeout=ELEMENT_WAIT_TIMEOUT)
            print(f"テーブルが見つかりました: {selector}")
            return table_locator
        except Exception:
            continue
    
    raise Exception("テーブルが見つかりませんでした")

def _extract_table_header(frame):
    """テーブルのヘッダー行を取得"""
    print("ヘッダー行を取得中...")
    header_selectors = ["thead tr", "table tr:first-child", "tr:first-child"]
    
    for selector in header_selectors:
        try:
            header = frame.locator(selector).first
            header.wait_for(state="attached", timeout=ELEMENT_WAIT_TIMEOUT // 2)
            header_cells = header.locator("th, td").all()
            if len(header_cells) > 0:
                header_row = [cell.inner_text() for cell in header_cells]
                print(f"ヘッダー行を取得: {header_row}")
                return header_row
        except Exception:
            continue
    
    return None

def _extract_table_rows(frame, header_row):
    """テーブルのデータ行と色情報を取得"""
    print("データ行を取得中...")
    data_rows = []
    cell_colors = []
    row_selectors = ["tbody tr", "table tr"]
    
    for selector in row_selectors:
        try:
            rows = frame.locator(selector).all()
            if len(rows) > 0:
                start_idx = 1 if header_row else 0
                for row_idx, row in enumerate(rows[start_idx:]):
                    try:
                        cells = row.locator("td, th").all()
                        row_data = []
                        row_color_info = []
                        
                        for cell in cells:
                            cell_text = cell.inner_text()
                            row_data.append(cell_text.strip())
                            
                            # 色情報を取得
                            try:
                                bg_color = cell.evaluate("""
                                    el => {
                                        const style = window.getComputedStyle(el);
                                        return style.backgroundColor || style.background || 'transparent';
                                    }
                                """)
                                rgb_color = _parse_color_to_rgb(bg_color)
                                row_color_info.append(rgb_color)
                            except Exception:
                                row_color_info.append(None)
                        
                        # データが有効な行か確認（%や数値が含まれる）
                        if len(row_data) > 0 and any('%' in cell or cell.replace('.', '').replace('/', '').replace('-', '').isdigit() for cell in row_data):
                            data_rows.append(row_data)
                            # 取得日時列を考慮して、色情報にもNoneを追加
                            cell_colors.append([None] + row_color_info)
                    except Exception as e:
                        print(f"  行 {row_idx + start_idx} の取得でエラー: {e}")
                        continue
                
                if len(data_rows) > 0:
                    print(f"データ行を{len(data_rows)}行取得しました（色情報も含む）")
                    return data_rows, cell_colors
        except Exception as e:
            print(f"行取得エラー: {e}")
            continue
    
    raise Exception("データ行が見つかりませんでした")

def _parse_color_to_rgb(bg_color):
    """背景色文字列をGoogleスプレッドシート用のRGB形式に変換"""
    if not bg_color or bg_color in ['transparent', 'rgba(0, 0, 0, 0)', 'unknown', '']:
        return None
    
    try:
        # rgb(r, g, b) または rgba(r, g, b, a) 形式をパース
        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', bg_color)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return {'red': r/255.0, 'green': g/255.0, 'blue': b/255.0}
        
        # 16進数形式 (#RRGGBB) の場合
        if bg_color.startswith('#'):
            hex_color = bg_color[1:]
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return {'red': r/255.0, 'green': g/255.0, 'blue': b/255.0}
    except (ValueError, AttributeError):
        pass
    
    return None

def scrape_fed_data():
    """CME FedWatchサイトからデータをスクレイピング（元のコードの動作を再現）"""
    url = "https://www.cmegroup.com/ja/markets/interest-rates/cme-fedwatch-tool.html"
    
    for attempt in range(MAX_RETRIES):
        try:
            with sync_playwright() as p:
                # Chromiumブラウザを起動
                browser, page = _launch_browser(p)
                
                try:
                    # ページに遷移
                    _navigate_to_page(page, url, attempt)
                    
                    # iframeを探す
                    frame = _find_iframe(page)
                    
                    # iframe内のデータが読み込まれるまで待つ（元のコードと同じ）
                    print("iframe内のデータを待機中...")
                    time.sleep(WAIT_AFTER_IFRAME_LOAD)
                    
                    # Probabilitiesをクリック
                    _click_probabilities(frame)
                    
                    # テーブルが表示されるまで待つ（元のコードと同じ）
                    print("テーブルの読み込みを待機中...")
                    time.sleep(5)  # 元のコードと同じ
                    
                    # テーブルを探す
                    _find_table(frame)  # テーブルが存在することを確認
                    
                    # より長い待機時間を設定（元のコードと同じ）
                    time.sleep(WAIT_FOR_TABLE_DATA)
                    
                    # ヘッダー行を取得
                    header_row = _extract_table_header(frame)
                    
                    # データ行と色情報を取得
                    data_rows, cell_colors = _extract_table_rows(frame, header_row)
                    
                    browser.close()
                    
                    # ヘッダーとデータ、色情報を返す
                    return {
                        'header': header_row if header_row else [],
                        'rows': data_rows,
                        'cell_colors': cell_colors
                    }
                    
                except Exception as e:
                    print(f"スクレイピングエラー（chromium, 試行 {attempt + 1}/{MAX_RETRIES}）: {e}")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    
                    if attempt < MAX_RETRIES - 1:
                        print(f"{RETRY_DELAY}秒待機して再試行します...")
                        time.sleep(RETRY_DELAY)
                        continue
                    
                    raise Exception(f"スクレイピングに失敗しました（chromium, {MAX_RETRIES}回試行）: {e}")
                    
        except Exception as e:
            # 外側の例外処理（ブラウザ起動失敗など）
            print(f"ブラウザ起動エラー（chromium, 試行 {attempt + 1}/{MAX_RETRIES}）: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"{RETRY_DELAY}秒待機して再試行します...")
                time.sleep(RETRY_DELAY)
                continue
            
            raise Exception(f"スクレイピングに失敗しました（chromium, {MAX_RETRIES}回試行）: {e}")
    
    raise Exception("スクレイピングに失敗しました（すべての試行が失敗）")

# --- 3. スプレッドシートへ書き込み（前回値比較 + 矢印 + 色情報も適用） ---
def update_sheet(table_data):
    spreadsheet = gc.open(SPREADSHEET_NAME)
    sh = spreadsheet.sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 前回値シートの準備
    previous_sheet_name = PREVIOUS_SHEET_NAME
    try:
        previous_sheet = spreadsheet.worksheet(previous_sheet_name)
        print(f"前回値シート '{previous_sheet_name}' が見つかりました")
    except gspread.exceptions.WorksheetNotFound:
        # 前回値シートが存在しない場合は作成
        previous_sheet = spreadsheet.add_worksheet(title=previous_sheet_name, rows=100, cols=20)
        print(f"前回値シート '{previous_sheet_name}' を作成しました")
    
    # 前回値を読み込む
    previous_data = None
    try:
        previous_values = previous_sheet.get_all_values()
        if len(previous_values) > 1:  # ヘッダー行以外にデータがある場合
            # ヘッダー行を除いて、データ部分のみ取得
            previous_data = previous_values[1:] if len(previous_values) > 1 else []
            print(f"前回値データを{len(previous_data)}行読み込みました")
    except Exception as e:
        print(f"前回値の読み込みでエラー: {e}")
        previous_data = None
    
    # 列番号を文字列に変換するヘルパー関数
    def col_num_to_letter(n):
        """列番号（1始まり）を列文字（A, B, C, ...）に変換"""
        result = ""
        while n > 0:
            n -= 1
            result = chr(65 + (n % 26)) + result
            n //= 26
        return result
    
    # 数値を抽出する関数（%記号や矢印を除去）
    def extract_number(value):
        """セルから数値を抽出（例: '88.4% ↑' → 88.4）"""
        if not value or not isinstance(value, str):
            return None
        try:
            # %記号と矢印を除去して数値を抽出
            match = re.search(r'(\d+\.?\d*)', value.replace('%', '').replace('↑', '').replace('↓', '').replace('→', '').strip())
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    # 現在のデータと前回値を比較して、矢印を決定
    all_data = []
    
    if table_data['header']:
        # 1行目にヘッダーを書き込み（取得日時列 + 空列を追加）
        header_with_date = ['取得日時', ''] + table_data['header']
        all_data.append(header_with_date)
        print(f"ヘッダー行: {header_with_date}")
    
    # データ行を書き込む（前回値と比較して矢印を追加）
    if table_data['rows']:
        for row_idx, row in enumerate(table_data['rows']):
            row_with_date = [now, '']  # 取得日時 + 空列
            
            for col_idx, current_val in enumerate(row):
                # 確率値（%を含む）の場合のみ矢印を付ける
                # 会合日（日付形式）やヘッダーには矢印を付けない
                arrow = ""
                change_text = ""  # 初期化
                
                # 確率値かどうかを判定（%記号を含み、数値であること）
                if current_val and '%' in str(current_val):
                    # 前回値と比較（取得日時 + 空列の2列分を考慮して col_idx + 2）
                    previous_val = None
                    if previous_data and row_idx < len(previous_data) and col_idx + 2 < len(previous_data[row_idx]):
                        previous_val_str = previous_data[row_idx][col_idx + 2] if len(previous_data[row_idx]) > col_idx + 2 else None
                        previous_val = extract_number(previous_val_str)
                    
                    current_num = extract_number(current_val)
                    
                    # 矢印と増減率を決定
                    if current_num is not None and previous_val is not None:
                        diff = current_num - previous_val
                        if abs(diff) > MIN_CHANGE_THRESHOLD:  # 閾値以上の変化がある場合
                            if diff > 0:
                                arrow = " ↑"
                                change_text = f" +{diff:.1f}%"
                            else:
                                arrow = " ↓"
                                change_text = f" {diff:.1f}%"  # 負の値なので"-"は自動で付く
                        else:
                            arrow = " →"
                            change_text = " ±0.0%"
                    # 前回値がない場合（初回実行など）は矢印・増減率なし
                
                # セルの値に矢印と増減率を追加（確率値の場合のみ）
                if current_val:
                    cell_value = current_val + arrow + change_text
                else:
                    cell_value = ""
                row_with_date.append(cell_value)
            
            all_data.append(row_with_date)
        
        print(f"データ行を{len(all_data) - 1}行準備しました（前回値と比較済み）")
    
    # 既存のデータをクリア（全て）
    sh.clear()
    
    # 一括で書き込み
    if len(all_data) > 0:
        sh.update(values=all_data, range_name='A1')
        print(f"スプレッドシートに{len(all_data)}行を書き込みました")
    
    # 背景色の自動設定は無効化（矢印のみ表示）
    # 変化に応じた色情報の適用は行わない
    # ただし、CMEサイトから取得した色情報は適用する
    
    # CMEサイトから取得した色情報を適用
    if 'cell_colors' in table_data and table_data['cell_colors']:
        print("CMEサイトから取得した色情報を適用中...")
        cell_colors = table_data['cell_colors']
        
        # ヘッダー行を考慮して、データ行の開始行番号を計算（2行目から）
        start_row = 2 if table_data['header'] else 1
        
        colored_cell_count = 0
        error_count = 0
        
        for row_idx, row_colors in enumerate(cell_colors):
            sheet_row = start_row + row_idx
            
            for col_idx, color_info in enumerate(row_colors):
                if color_info is not None:  # 色情報がある場合のみ
                    try:
                        # 取得日時(1列目) + 空列(2列目) + データ列(col_idx + 1) = col_idx + 3
                        col_letter = col_num_to_letter(col_idx + 3)
                        cell_range = f"{col_letter}{sheet_row}"
                        
                        # gspreadのformatメソッドで背景色を設定
                        sh.format(cell_range, {
                            "backgroundColor": color_info
                        })
                        colored_cell_count += 1
                    except Exception as e:
                        error_count += 1
                        if error_count <= 5:  # 最初の5つのエラーのみ表示
                            print(f"  セル {col_letter}{sheet_row} の色設定でエラー: {e}")
                        continue
        
        if colored_cell_count > 0:
            print(f"CMEサイトの色情報を{colored_cell_count}個のセルに適用しました")
        if error_count > 0:
            print(f"警告: {error_count}個のセルで色設定に失敗しました")
    
    # 現在のデータを「前回値」シートに保存
    try:
        previous_sheet.clear()
        previous_sheet.update(values=all_data, range_name='A1')
        print(f"現在のデータを「前回値」シートに保存しました")
    except Exception as e:
        print(f"前回値シートへの保存でエラー: {e}")
    
    print("スプレッドシートへの書き込み完了")

if __name__ == "__main__":
    try:
        table_data = scrape_fed_data()
        update_sheet(table_data)
        print(f"成功: テーブル全体（{len(table_data['rows'])}行）をスプレッドシートに書き込みました")
    except Exception as e:
        print(f"エラー: {e}")
        raise
