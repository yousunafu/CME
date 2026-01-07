import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. スプレッドシートの認証設定 ---
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
key_json = os.environ.get("GCP_SA_KEY")
if not key_json:
    raise ValueError("GCP_SA_KEY is not set in environment variables")

creds = Credentials.from_service_account_info(json.loads(key_json), scopes=scopes)
gc = gspread.authorize(creds)

# --- 2. CMEの内部APIからデータを取得 ---
def get_fed_data():
    # ブラウザを介さず、CMEのデータエンドポイントを直接叩く
    url = "https://www.cmegroup.com/CmeWS/exp/v1/fedwatch/probabilities/latest"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    # 取得したデータから「次回の会合」の「据え置き」確率を抽出
    # データの構造：data[0] が直近の会合
    first_meeting = data[0]
    # 通常、probabilitiesの最初の要素が現在の金利維持（据え置き）の確率です
    prob = first_meeting['probabilities'][0]['probability']
    
    # 0.985 などの数値を 98.5 に変換して返す
    return float(prob) * 100

# --- 3. スプレッドシートへ書き込み ---
def update_sheet(new_val):
    sh = gc.open("CME定期調査").sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    all_values = sh.get_all_values()
    last_val = 0
    if len(all_values) > 1:
        try:
            # B列（前回の値）を取得
            last_val = float(all_values[-1][1])
        except:
            last_val = 0
    
    diff = new_val - last_val
    sh.append_row([now, new_val, diff])

if __name__ == "__main__":
    try:
        val = get_fed_data()
        update_sheet(val)
        print(f"成功: 現在の確率は {val}% です。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        raise
