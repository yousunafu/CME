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

# --- 2. QuikStrikeのデータエンドポイントから取得 ---
def get_fed_data():
    # CME本体ではなく、データ提供元のURLを直接使用
    url = "https://cmegroup-fedwatch.quikstrike.net/api/v1/fedwatch/probabilities/latest"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.cmegroup.com",
        "Referer": "https://www.cmegroup.com/"
    }
    
    # セッションを使用して、よりブラウザに近い挙動にする
    session = requests.Session()
    response = session.get(url, headers=headers, timeout=30)
    
    if response.status_code == 403:
        raise Exception("CME/QuikStrikeによりアクセスが拒絶されました(403)。")
        
    response.raise_for_status()
    data = response.json()
    
    # データのパース (QuikStrikeのデータ構造に合わせる)
    # data[0] は直近の会合。probabilitiesリストの最初の要素を取得
    try:
        first_meeting = data[0]
        prob = first_meeting['probabilities'][0]['probability']
        return float(prob) * 100
    except (KeyError, IndexError) as e:
        raise Exception(f"データ構造の解析に失敗しました: {e}")

# --- 3. スプレッドシートへ書き込み ---
def update_sheet(new_val):
    sh = gc.open("CME定期調査").sheet1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    all_values = sh.get_all_values()
    last_val = 0
    if len(all_values) > 1:
        try:
            # 最後の行のB列を取得
            last_val = float(all_values[-1][1])
        except (ValueError, IndexError):
            last_val = 0
    
    diff = round(new_val - last_val, 2)
    sh.append_row([now, round(new_val, 2), diff])

if __name__ == "__main__":
    try:
        val = get_fed_data()
        update_sheet(val)
        print(f"成功: 現在の確率は {val}% です。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        raise
