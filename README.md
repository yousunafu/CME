# CME FedWatch データ取得ツール

CME FedWatchのデータを自動的に取得し、Googleスプレッドシートに書き込むツールです。

## 📋 機能

- CME FedWatch Tool から確率データを自動取得
- Googleスプレッドシートに自動書き込み
- 前回値との比較（増減率と矢印表示）
- セルの背景色を元のサイトから取得して適用
- macOSでの自動実行（launchd使用）
- エラーハンドリングとリトライ機能

## 📚 はじめに

このツールを初めて使う方は、**`初回セットアップガイド.md`** を最初にご覧ください。詳細なセットアップ手順が記載されています。

## 🚀 クイックスタート

### 前提条件

- Python 3.8以上
- macOS（自動実行機能を使用する場合）
- GoogleアカウントとGoogle Cloud Projectへのアクセス権限

### 1. プロジェクトの取得

```bash
# Gitリポジトリからクローン
git clone https://github.com/yousunafu/CME.git
cd CME

# または、ZIPファイルを解凍して配置
```

### 2. 仮想環境のセットアップ

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 必要なライブラリをインストール
pip install -r requirements.txt

# Playwrightブラウザをインストール
playwright install chromium
```

### 3. Googleスプレッドシートの設定

詳細は **`初回セットアップガイド.md`** の「ステップ3」を参照してください。

1. Google Cloud Console でサービスアカウントを作成
2. 認証キー（JSON）をダウンロード
3. `service_account.json` という名前に変更して、プロジェクトディレクトリに配置
4. Googleスプレッドシート「CME定期調査」を作成し、サービスアカウントと共有

### 4. 実行

```bash
# 仮想環境を有効化（まだの場合）
source venv/bin/activate

# スクリプトを実行
python main.py
```

ブラウザが起動し、CMEのページが開いてデータを取得します。

## ⏰ 自動実行の設定（macOS）

macOSでは `launchd` を使用して自動実行を設定できます。

詳細な手順は **`自動化セットアップ手順.md`** を参照してください。

### クイックセットアップ

1. **plistファイルを編集**
   
   `com.cme.scraper.plist` ファイルを開き、以下のパスを自分の環境に合わせて変更：
   - `YOUR_USERNAME` を自分のユーザー名に変更
   - `YOUR_PROJECT_PATH` をプロジェクトの実際のパスに変更

2. **ログディレクトリを作成：**

```bash
# プロジェクトディレクトリに移動
cd /path/to/CME

# ログディレクトリを作成
mkdir -p logs
```

3. **plistファイルをLaunchAgentsにコピー：**

```bash
cp com.cme.scraper.plist ~/Library/LaunchAgents/com.cme.scraper.plist
```

4. **launchdに登録：**

```bash
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

5. **登録の確認：**

```bash
launchctl list | grep com.cme.scraper
```

### 実行スケジュール

デフォルトで以下の時刻に自動実行されます：

- **日本時間 9:00**
- **日本時間 15:00**
- **日本時間 21:00**
- **日本時間 3:00**

### よく使うコマンド

**自動実行を停止する：**

```bash
launchctl unload ~/Library/LaunchAgents/com.cme.scraper.plist
```

**自動実行を再開する：**

```bash
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

**手動で実行する：**

```bash
cd /path/to/CME
source venv/bin/activate
python main.py
```

**ログを確認する：**

```bash
# 出力ログをリアルタイムで確認
tail -f logs/output.log

# エラーログをリアルタイムで確認
tail -f logs/error.log

# 最新のログを確認
tail -20 logs/output.log
```

## ⚠️ 重要な注意事項

### セキュリティ

- **`service_account.json` は機密情報です**。他人と共有しないでください。
- このファイルは `.gitignore` で除外されているため、Gitリポジトリにコミットされることはありません。
- 誤ってコミットした場合は、GitHubでトークンを無効化してください。

### 動作環境

- このツールは**ローカルPCから実行する必要があります**（クラウドサーバーからのアクセスはCMEによってブロックされます）
- **PCが起動している必要があります**（スリープ中は実行されません）
- **インターネット接続**が必要です

### 設定について

- デフォルトでは `headless=False` に設定されており、ブラウザが表示されます
- バックグラウンドで実行したい場合は、`main.py` の `headless=True` に変更してください
- スプレッドシート名は `main.py` の312行目で設定されています（デフォルト: "CME定期調査"）

## 🔧 カスタマイズ

### スプレッドシート名を変更する

`main.py` の312行目を編集：

```python
spreadsheet = gc.open("あなたのスプレッドシート名")
```

### 実行スケジュールを変更する

`com.cme.scraper.plist` ファイルの `StartCalendarInterval` セクションを編集してください。

## 📖 関連ドキュメント

- **`初回セットアップガイド.md`** - 初めて使う方向けの詳細なセットアップ手順
- **`自動化セットアップ手順.md`** - macOSでの自動実行設定の詳細手順
- **`プログラムの仕組みと動作解説.md`** - プログラムがどのように動作するかの詳細な技術解説
  - データフロー図
  - 各機能の詳細説明
  - 使用している技術の解説
  - エラーハンドリングの仕組み

## 🐛 トラブルシューティング

よくある問題と解決方法は **`初回セットアップガイド.md`** の「トラブルシューティング」セクションを参照してください。

主な問題：
- 認証ファイルが見つからない
- スプレッドシートが見つからない
- ブラウザが起動しない
- 自動実行が動作しない
