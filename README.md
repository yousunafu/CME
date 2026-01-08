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

1. `~/Library/LaunchAgents/com.cme.scraper.plist` というファイルを作成
2. 以下の内容をコピー（パスを自分の環境に合わせて調整）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cme.scraper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/suzukiyuu/Desktop/CME/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>15</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>21</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>3</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/suzukiyuu/Desktop/CME/logs/output.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/suzukiyuu/Desktop/CME/logs/error.log</string>
</dict>
</plist>
```

3. ログディレクトリを作成：

```bash
mkdir -p ~/Desktop/CME/logs
```

4. launchdに登録：

```bash
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

5. 登録を解除する場合：

```bash
launchctl unload ~/Library/LaunchAgents/com.cme.scraper.plist
```

## 注意事項

- このツールはローカルPCから実行する必要があります（クラウドサーバーからのアクセスはCMEによってブロックされます）
- PCが起動している必要があります（スリープ中は実行されません）
- `headless=False` に設定されているため、ブラウザが表示されます。バックグラウンドで実行したい場合は、`main.py`の`headless=False`を`headless=True`に変更してください
