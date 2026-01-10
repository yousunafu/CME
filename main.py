import os
import json
import time
import re
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
    max_retries = 3
    retry_delay = 10
    browsers_to_try = ['chromium', 'firefox']  # Chromiumが失敗したらFirefoxを試す
    
    for browser_type in browsers_to_try:
        for attempt in range(max_retries):
            try:
                with sync_playwright() as p:
                    # headless=True にすると、ブラウザが画面に表示されずバックグラウンドで実行されます
                    # デバッグ時は headless=False に変更すると、ブラウザの動作が見えます
                    if browser_type == 'chromium':
                        browser = p.chromium.launch(
                            headless=False,  # ブラウザを表示してデバッグ
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
                    else:  # firefox
                        browser = p.firefox.launch(
                            headless=False  # ブラウザを表示してデバッグ
                        )
                    # より現実的なブラウザ設定
                    if browser_type == 'chromium':
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        )
                    else:  # firefox
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
                        )
                    page = context.new_page()
                    
                    # CMEのサイトへ移動（日本語版）
                    print(f"サイトへアクセス中... ({browser_type}, 試行 {attempt + 1}/{max_retries})")
                    url = "https://www.cmegroup.com/ja/markets/interest-rates/cme-fedwatch-tool.html"
                    
                    try:
                        # domcontentloadedを使用してHTTP/2エラーを回避
                        page.goto(url, wait_until="domcontentloaded", timeout=120000)
                        print("ページ遷移成功")
                        # 追加の待機時間
                        time.sleep(3)
                    except Exception as e:
                        print(f"ページ遷移エラー（{browser_type}, 試行 {attempt + 1}/{max_retries}）: {e}")
                        try:
                            browser.close()
                        except:
                            pass
                        if attempt < max_retries - 1:
                            print(f"{retry_delay}秒待機して再試行します...")
                            time.sleep(retry_delay)
                            continue
                        # このブラウザタイプでの全試行が失敗した場合、次のブラウザタイプを試す
                        if browser_type == 'chromium' and 'firefox' in browsers_to_try:
                            print(f"Chromiumでの試行が失敗したため、Firefoxに切り替えます")
                            break
                        # 次のブラウザタイプもない場合は、外側のループで処理される
                        # （すべてのブラウザタイプを試し終わった後、最後に例外が発生する）
                    
                    # ページが完全に読み込まれるまで待機
                    print("ページの読み込みを待機中...")
                    time.sleep(5)
                    
                    # ページが読み込まれたか確認
                    print(f"ページタイトル: {page.title()}")
                    print(f"現在のURL: {page.url}")
                    
                    # iframe（データが入っている箱）を探す
                    print("iframeを探しています...")
                    # 複数のパターンでiframeを探す
                    iframe_selectors = [
                        "iframe[src*='quikstrike']",
                        "iframe[src*='fedwatch']",
                        "iframe"
                    ]
                    
                    frame = None
                    for selector in iframe_selectors:
                        try:
                            iframes = page.locator(selector).all()
                            if iframes:
                                print(f"iframeが見つかりました: {selector} ({len(iframes)}個)")
                                frame = page.frame_locator(selector).first
                                break
                        except:
                            continue
                    
                    if frame is None:
                        # ページのHTMLを確認（デバッグ用）
                        print("iframeが見つかりませんでした。ページの構造を確認します...")
                        page_content = page.content()
                        if "quikstrike" in page_content.lower() or "fedwatch" in page_content.lower():
                            print("ページ内に'quikstrike'または'fedwatch'の文字列が見つかりました")
                        else:
                            print("ページ内に'quikstrike'または'fedwatch'の文字列が見つかりませんでした")
                        raise Exception("iframeが見つかりませんでした")
                    
                    # iframe内のデータが読み込まれるまで待つ
                    print("iframe内のデータを待機中...")
                    time.sleep(5)
                    
                    # 左側の「Probabilities」をクリック
                    print("'Probabilities'をクリックしています...")
                    prob_clicked = False
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
                            if prob_link.is_visible(timeout=5000):
                                print(f"Probabilitiesリンクが見つかりました: {selector}")
                                prob_link.click()
                                prob_clicked = True
                                print("Probabilitiesをクリックしました")
                                break
                        except Exception as e:
                            print(f"セレクタ '{selector}' でエラー: {e}")
                            continue
                    
                    if not prob_clicked:
                        print("警告: Probabilitiesが見つかりませんでした。既に選択されている可能性があります。")
                    
                    # テーブルが表示されるまで待つ
                    print("テーブルの読み込みを待機中...")
                    time.sleep(5)
                    
                    # テーブル全体からデータを取得
                    print("テーブル全体からデータを取得中...")
                    
                    # より長い待機時間を設定
                    time.sleep(3)
                    
                    # テーブルを探す
                    table = None
                    table_selectors = ["table", "table tbody"]
                    
                    for selector in table_selectors:
                        try:
                            table_locator = frame.locator(selector).first
                            table_locator.wait_for(state="attached", timeout=10000)
                            table = table_locator
                            print(f"テーブルが見つかりました: {selector}")
                            break
                        except:
                            continue
                    
                    if table is None:
                        raise Exception("テーブルが見つかりませんでした")
                    
                    # ヘッダー行を取得
                    print("ヘッダー行を取得中...")
                    header_row = None
                    header_selectors = ["thead tr", "table tr:first-child", "tr:first-child"]
                    
                    for selector in header_selectors:
                        try:
                            header = frame.locator(selector).first
                            header.wait_for(state="attached", timeout=5000)
                            header_cells = header.locator("th, td").all()
                            if len(header_cells) > 0:
                                header_row = [cell.inner_text() for cell in header_cells]
                                print(f"ヘッダー行を取得: {header_row}")
                                break
                        except:
                            continue
                    
                    # データ行を取得（色情報も含む）
                    print("データ行を取得中...")
                    data_rows = []
                    cell_colors = []  # 各セルの色情報を保持（行×列の2次元配列）
                    row_selectors = ["tbody tr", "table tr"]
                    
                    for selector in row_selectors:
                        try:
                            rows = frame.locator(selector).all()
                            if len(rows) > 0:
                                # ヘッダー行を除く（最初の行がヘッダーの場合）
                                start_idx = 1 if header_row else 0
                                for row_idx, row in enumerate(rows[start_idx:]):
                                    try:
                                        cells = row.locator("td, th").all()
                                        row_data = []
                                        row_color_info = []  # この行の各セルの色情報
                                        
                                        for cell_idx, cell in enumerate(cells):
                                            cell_text = cell.inner_text()
                                            row_data.append(cell_text.strip())
                                            
                                            # 色情報を取得
                                            try:
                                                # 背景色を取得
                                                bg_color = cell.evaluate("""
                                                    el => {
                                                        const style = window.getComputedStyle(el);
                                                        return style.backgroundColor || style.background || 'transparent';
                                                    }
                                                """)
                                                
                                                # RGB値を抽出して16進数に変換
                                                rgb_color = None
                                                if bg_color and bg_color not in ['transparent', 'rgba(0, 0, 0, 0)', 'unknown', '']:
                                                    try:
                                                        # rgb(r, g, b) または rgba(r, g, b, a) 形式をパース
                                                        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', bg_color)
                                                        if match:
                                                            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                                                            rgb_color = {'red': r/255.0, 'green': g/255.0, 'blue': b/255.0}
                                                        else:
                                                            # 16進数形式 (#RRGGBB) の場合
                                                            if bg_color.startswith('#'):
                                                                hex_color = bg_color[1:]
                                                                if len(hex_color) == 6:
                                                                    r = int(hex_color[0:2], 16)
                                                                    g = int(hex_color[2:4], 16)
                                                                    b = int(hex_color[4:6], 16)
                                                                    rgb_color = {'red': r/255.0, 'green': g/255.0, 'blue': b/255.0}
                                                    except:
                                                        pass
                                                
                                                row_color_info.append(rgb_color)
                                            except Exception as e:
                                                row_color_info.append(None)
                                        
                                        if len(row_data) > 0 and any('%' in cell or cell.replace('.', '').replace('/', '').replace('-', '').isdigit() for cell in row_data):
                                            data_rows.append(row_data)
                                            # 取得日時列を考慮して、色情報にもNoneを追加（最初の列は日時なので色なし）
                                            cell_colors.append([None] + row_color_info)
                                            
                                    except Exception as e:
                                        print(f"  行 {row_idx + start_idx} の取得でエラー: {e}")
                                        continue
                                
                                if len(data_rows) > 0:
                                    print(f"データ行を{len(data_rows)}行取得しました（色情報も含む）")
                                    break
                        except Exception as e:
                            print(f"行取得エラー: {e}")
                            continue
                    
                    if len(data_rows) == 0:
                        raise Exception("データ行が見つかりませんでした")
                    
                    browser.close()
                    
                    # ヘッダーとデータ、色情報を返す
                    return {
                        'header': header_row if header_row else [],
                        'rows': data_rows,
                        'cell_colors': cell_colors  # 各セルの色情報（行×列）
                    }
                    
            except Exception as e:
                print(f"スクレイピングエラー（{browser_type}, 試行 {attempt + 1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    print(f"{retry_delay}秒待機して再試行します...")
                    time.sleep(retry_delay)
                    continue
                # このブラウザタイプでの全試行が失敗した場合、次のブラウザタイプを試す
                if browser_type == 'chromium' and 'firefox' in browsers_to_try:
                    print(f"Chromiumでの試行が失敗したため、Firefoxに切り替えます")
                    break
                raise Exception(f"スクレイピングに失敗しました（{browser_type}, {max_retries}回試行）: {e}")
    
    raise Exception("すべてのブラウザでのスクレイピングに失敗しました")

# --- 3. スプレッドシートへ書き込み（前回値比較 + 矢印 + 色情報も適用） ---
def update_sheet(table_data):
    spreadsheet = gc.open("CME定期調査")
    sh = spreadsheet.sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 前回値シートの準備
    previous_sheet_name = "前回値"
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
                        if abs(diff) > 0.1:  # 0.1%以上の変化がある場合
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
    
    print("スプレッドシートへの書き込み完了")

if __name__ == "__main__":
    try:
        table_data = scrape_fed_data()
        update_sheet(table_data)
        print(f"成功: テーブル全体（{len(table_data['rows'])}行）をスプレッドシートに書き込みました")
    except Exception as e:
        print(f"エラー: {e}")
        raise
