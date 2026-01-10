# CME FedWatch データ取得ツール

CME FedWatchのデータを自動的に取得し、Googleスプレッドシートに書き込むツールです。

## ローカル実行の準備

### 1. 必要なライブラリのインストール

```bash
pip install gspread google-auth playwright
playwright install chromium
```

または、`pip3`を使用する場合：

```bash
pip3 install gspread google-auth playwright
playwright install chromium
```

### 2. 認証ファイルの準備

1. Google Cloud ConsoleからダウンロードしたサービスアカウントのJSONキーファイルを取得
2. そのファイルを `service_account.json` という名前に変更
3. `main.py` と同じフォルダ（`/Users/suzukiyuu/Desktop/CME`）に配置

### 3. 実行

```bash
python main.py
```

または：

```bash
python3 main.py
```

ブラウザが起動し、CMEのページが開いてデータを取得します。

## 自動実行の設定（macOS）

macOSでは `launchd` を使用して自動実行を設定できます。

### 手順

1. **ログディレクトリを作成：**

```bash
mkdir -p ~/Desktop/CME/logs
```

2. **plistファイルをLaunchAgentsにコピー：**

```bash
cp ~/Desktop/CME/com.cme.scraper.plist ~/Library/LaunchAgents/com.cme.scraper.plist
```

3. **launchdに登録：**

```bash
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

4. **登録の確認：**

```bash
launchctl list | grep com.cme.scraper
```

### 実行スケジュール

- **日本時間 9:00** (UTC 0:00)
- **日本時間 15:00** (UTC 6:00)
- **日本時間 21:00** (UTC 12:00)
- **日本時間 3:00** (UTC 18:00)

### 便利なコマンド

**登録を解除する場合：**

```bash
launchctl unload ~/Library/LaunchAgents/com.cme.scraper.plist
```

**手動で実行する場合：**

```bash
cd ~/Desktop/CME
source venv/bin/activate
python main.py
```

**ログを確認する場合：**

```bash
# 出力ログ
tail -f ~/Desktop/CME/logs/output.log

# エラーログ
tail -f ~/Desktop/CME/logs/error.log
```

## 注意事項

- このツールはローカルPCから実行する必要があります（クラウドサーバーからのアクセスはCMEによってブロックされます）
- PCが起動している必要があります（スリープ中は実行されません）
- `headless=True` に設定されているため、ブラウザは表示されずバックグラウンドで実行されます
- デバッグ時は `main.py`の`headless=True`を`headless=False`に変更すると、ブラウザの動作が見えます
