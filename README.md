# CME FedWatch データ取得ツール

CME FedWatch のデータを自動で取得し、Google スプレッドシートに書き込むツールです。  
**初めて使う方**は、この README を上から順に進めればセットアップから定期実行まで一通りできます。

---

## 目次

1. [このツールでできること](#このツールでできること)
2. [準備するもの](#準備するもの)
3. [セットアップの流れ（全体像）](#セットアップの流れ全体像)
4. [ステップ1: プロジェクトを手元に用意する](#ステップ1-プロジェクトを手元に用意する)
5. [ステップ2: Python の環境を整える](#ステップ2-python-の環境を整える)
6. [ステップ3: Google の設定（スプレッドシート・認証）](#ステップ3-google-の設定スプレッドシート認証)
7. [ステップ4: 動作確認（手動で1回実行）](#ステップ4-動作確認手動で1回実行)
8. [ステップ5: 定期実行の設定（任意）](#ステップ5-定期実行の設定任意)
9. [Windows で使う場合](#windows-で使う場合)
10. [よく使う操作](#よく使う操作)
11. [トラブルシューティング](#トラブルシューティング)
12. [注意事項・セキュリティ](#注意事項セキュリティ)

---

## このツールでできること

- **CME FedWatch** のサイトから金利予測の確率データを取得する
- 取得したデータを **Google スプレッドシート「CME定期調査」** に書き込む
- 前回のデータとの比較（増減率・矢印）と、元サイトの色を再現して表示する
- 実行のたびに **最新データが上、過去データが下** に蓄積され、時系列で比較できる
- **指定時刻に自動実行**（9:00 / 15:00 / 21:00 / 3:00・日本時間）できる（PC の起動中のみ。Mac は launchd、Windows はタスクスケジューラで設定）。Mac の定期実行は **ターミナルを開かず**実行され、手動実行と同様に **ブラウザ（Chromium）が表示**されて取得します。

---

## 準備するもの

- **PC**: **Mac（macOS）** または **Windows** のいずれか（手順はそれぞれ下記を参照）
- **Python 3.8 以上**（未導入の場合は後述の手順で確認・インストール）
- **インターネット接続**
- **Google アカウント** と、**Google Cloud でプロジェクトを作成できる権限**
- ツールを置く **フォルダ**（例: デスクトップ、ドキュメント）

---

## セットアップの流れ（全体像）

| 順番 | やること | 目安時間 |
|------|----------|----------|
| 1 | プロジェクトを取得（Git または ZIP） | 1分 |
| 2 | Python の仮想環境を作り、ライブラリをインストール | 3分 |
| 3 | Google Cloud でサービスアカウントを作り、スプレッドシートを共有 | 10分 |
| 4 | 手動で1回実行して動作確認 | 2分 |
| 5 | （任意）定期実行の設定 | 3分 |

**初回は合計でおおよそ 20 分程度**を想定してください。

**※ 以下のステップ1〜5は Mac（macOS）向けの手順です。Windows の方は [Windows で使う場合](#windows-で使う場合) のセクションから進めてください。**

---

## ステップ1: プロジェクトを手元に用意する

### 方法A: Git を使う場合（推奨）

ターミナルを開き、次のように入力して Enter で実行します。

```bash
git clone https://github.com/yousunafu/CME.git
cd CME
```

`CME` フォルダができ、その中に `main.py` などが入っていれば OK です。

### 方法B: ZIP で渡された場合

1. 受け取った ZIP を解凍する
2. フォルダ名が `CME` になっていることを確認する
3. ターミナルで「アプリケーション」→「ユーティリティ」→「ターミナル」を開き、次のように **プロジェクトの場所** に移動する（パスは実際の場所に合わせて書き換えてください）

```bash
cd /Users/あなたのユーザー名/Desktop/CME
```

例: デスクトップの CME なら

```bash
cd ~/Desktop/CME
```

**ここまでのパス（例: `/Users/あなたのユーザー名/Desktop/CME`）をメモしておくと、あとで定期実行の設定で使います。**

---

## ステップ2: Python の環境を整える

すべて **ターミナル** で、プロジェクトのフォルダ（`CME`）にいる状態で実行します。

### 2-1. Python のバージョン確認

```bash
python3 --version
```

`Python 3.8` 以上と表示されれば問題ありません。  
表示されない、または 3.8 未満の場合は、[python.org](https://www.python.org/downloads/) から macOS 用の Python をインストールしてください。

### 2-2. 仮想環境の作成

```bash
python3 -m venv venv
```

### 2-3. 仮想環境の有効化

```bash
source venv/bin/activate
```

先頭に `(venv)` と出れば有効化できています。

### 2-4. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2-5. ブラウザ（Chromium）のインストール

```bash
playwright install chromium
```

ここまでエラーなく終われば、Python 環境の準備は完了です。

---

## ステップ3: Google の設定（スプレッドシート・認証）

ツールは **Google スプレッドシート** にデータを書き込むため、  
「サービスアカウント」を作り、そのアカウントにスプレッドシートを共有する必要があります。

### 3-1. Google Cloud の準備

1. ブラウザで [Google Cloud Console](https://console.cloud.google.com/) を開く
2. プロジェクトを選択するか、**「新しいプロジェクト」** で作成する（名前は例: `CME Scraper`）

### 3-2. API の有効化

1. 左メニュー **「APIとサービス」** → **「ライブラリ」**
2. **「Google Sheets API」** を検索 → 開く → **「有効にする」**
3. 同様に **「Google Drive API」** を検索 → **「有効にする」**

### 3-3. サービスアカウントの作成

1. 左メニュー **「APIとサービス」** → **「認証情報」**
2. **「認証情報を作成」** → **「サービスアカウント」**
3. 名前（例: `cme-scraper`）を入力 → **「作成して続行」**
4. ロールは **「編集者」** など適宜選択（またはスキップ）→ **「完了」**

### 3-4. 認証キー（JSON）のダウンロード

1. 一覧に出た **サービスアカウント名** をクリック
2. **「キー」** タブ → **「キーを追加」** → **「新しいキーを作成」**
3. **「JSON」** を選んで **「作成」**  
   → JSON ファイルがダウンロードされます

### 3-5. 認証ファイルの配置

1. ダウンロードした JSON ファイルの名前を **`service_account.json`** に変更する
2. そのファイルを **`main.py` と同じフォルダ（CME の中）** に置く

例: ダウンロードから移動する場合（ユーザー名やフォルダ名は環境に合わせて書き換えてください）

```bash
mv ~/Downloads/プロジェクト名-xxxxx.json ~/Desktop/CME/service_account.json
```

**重要:** `service_account.json` は機密情報です。他人に渡したり、Git にコミットしたりしないでください。

### 3-6. スプレッドシートの作成と共有

1. [Google スプレッドシート](https://sheets.google.com/) を開く
2. **新しいスプレッドシート** を作成
3. タイトルを **「CME定期調査」** に変更する  
   （別名にしたい場合は、後述の「スプレッドシート名を変えたい場合」を参照）
4. 右上 **「共有」** をクリック
5. **共有相手** に、さきほど作ったサービスアカウントの **メールアドレス** を入力  
   （形式: `xxxx@プロジェクト名.iam.gserviceaccount.com`）  
   認証情報のページや、JSON 内の `client_email` で確認できます
6. 権限を **「編集者」** にして **「送信」**

ここまでで、Google 側の設定は完了です。

---

## ステップ4: 動作確認（手動で1回実行）

ターミナルで、プロジェクトのフォルダに移動し、仮想環境を有効にしてから実行します。

```bash
cd /Users/あなたのユーザー名/Desktop/CME
source venv/bin/activate
python main.py
```

**正常に動いている場合:**

- ブラウザ（Chromium）が自動で開く
- CME FedWatch のページが表示され、データが取得される
- 終了後、Google スプレッドシート「CME定期調査」を開くと、データと色が反映されている
- 「前回値」というシートが自動作成されている

ここまで問題なければ、**手動実行は完了**です。  
次は、必要に応じて「指定時刻に自動で実行される」設定に進みます。

---

## ステップ5: 定期実行の設定（任意）

Mac が起動している間だけ、**日本時間 9:00 / 15:00 / 21:00 / 3:00** に自動実行する設定です。

### 5-1. ログ用フォルダの作成

```bash
cd /Users/あなたのユーザー名/Desktop/CME
mkdir -p logs
```

### 5-2. plist のパスを自分の環境に合わせる

- すでに **`com.cme.scraper.plist`** がある場合: そのファイルを編集する
- ない場合は、**`com.cme.scraper.plist.template`** をコピーして **`com.cme.scraper.plist`** という名前で保存してから編集する  
  ```bash
  cp com.cme.scraper.plist.template com.cme.scraper.plist
  ```

1. **`com.cme.scraper.plist`** をテキストエディタで開く
2. 次の **4 箇所** に出てくるパスを、**あなたのプロジェクトの実際のパス** に書き換える  
   例: デスクトップの `CME` なら `/Users/あなたのユーザー名/Desktop/CME`  
   テンプレートの場合は `YOUR_USERNAME` を自分のユーザー名に、`YOUR_PROJECT_PATH` を例: `Desktop/CME` のように置き換える

書き換え箇所:

- **ProgramArguments** の 2 つの `<string>`（Python のパスと main.py のパス）  
  → 例: `/Users/あなたのユーザー名/Desktop/CME/venv/bin/python3` と `/Users/あなたのユーザー名/Desktop/CME/main.py`
- `<key>WorkingDirectory</key>` の次の `<string>...</string>`（プロジェクトのフルパス）
- `<key>StandardOutPath</key>` の次の `<string>.../logs/output.log</string>`
- `<key>StandardErrorPath</key>` の次の `<string>.../logs/error.log</string>`

### 5-3. launchd への登録

ターミナルで次を実行します（パスは自分の環境に合わせてください）。

```bash
cp /Users/あなたのユーザー名/Desktop/CME/com.cme.scraper.plist ~/Library/LaunchAgents/com.cme.scraper.plist
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

指定時刻になると **ターミナルは開かず**実行され、**ブラウザが表示**されて手動実行と同じ流れで取得します。ログは `logs/output.log` と `logs/error.log` に追記されます。

### 5-4. 登録できているか確認

```bash
launchctl list com.cme.scraper
```

何かしら表示されれば登録されています。  
あとは指定時刻（9:00 / 15:00 / 21:00 / 3:00）に、Mac が起動していれば自動で実行されます。

---

## Windows で使う場合

**Windows** でも同じツールを利用できます。  
「ステップ1（プロジェクトの取得）」「ステップ3（Google の設定）」は Mac とほぼ同じです。  
以下は **Windows での違い** だけをまとめています。  
（コマンドは **コマンドプロンプト** または **PowerShell** で実行します。）

### Windows: ステップ1 — プロジェクトを手元に用意する

**Git を使う場合**

```cmd
git clone https://github.com/yousunafu/CME.git
cd CME
```

**ZIP で渡された場合**

1. ZIP を解凍して `CME` フォルダを作る
2. コマンドプロンプトまたは PowerShell を開き、そのフォルダに移動する  
   例: デスクトップの CME なら  
   ```cmd
   cd %USERPROFILE%\Desktop\CME
   ```
3. この **フォルダのパス**（例: `C:\Users\あなたのユーザー名\Desktop\CME`）をメモしておく（定期実行の設定で使います）

### Windows: ステップ2 — Python の環境を整える

プロジェクトのフォルダ（`CME`）にいる状態で実行します。

**Python のバージョン確認**

```cmd
py -3 --version
```

または

```cmd
python --version
```

`3.8` 以上と表示されれば OK です。未インストールの場合は [python.org](https://www.python.org/downloads/) から Windows 用をインストールし、**「Add Python to PATH」** にチェックを入れてください。

**仮想環境の作成**

```cmd
py -3 -m venv venv
```

または

```cmd
python -m venv venv
```

**仮想環境の有効化**

```cmd
venv\Scripts\activate
```

先頭に `(venv)` と出れば有効化できています。

**ライブラリのインストール**

```cmd
pip install -r requirements.txt
```

**ブラウザ（Chromium）のインストール**

```cmd
playwright install chromium
```

### Windows: ステップ3 — Google の設定

Mac と同じです。  
「[ステップ3: Google の設定（スプレッドシート・認証）](#ステップ3-google-の設定スプレッドシート認証)」の手順に従い、  
サービスアカウントを作成し、`service_account.json` を **`main.py` と同じフォルダ（CME の中）** に置き、  
スプレッドシート「CME定期調査」をサービスアカウントのメールアドレスで「編集者」として共有してください。

### Windows: ステップ4 — 動作確認（手動で1回実行）

```cmd
cd C:\Users\あなたのユーザー名\Desktop\CME
venv\Scripts\activate
python main.py
```

（`cd` の後のパスは、実際に CME を置いた場所に合わせて書き換えてください。）

ブラウザが開き、スプレッドシートにデータが反映されれば OK です。

### Windows: ステップ5 — 定期実行の設定（タスクスケジューラ）

Windows では **タスクスケジューラ** で指定時刻に実行します。プロジェクトに同梱の **`run_cme.bat`** を使うと、実行結果が **`logs\output.log`** と **`logs\error.log`** に残ります（`run_cme.bat` 実行時に `logs` フォルダがなければ自動作成されます）。

1. **タスクスケジューラ** を開く  
   「スタート」メニューで「タスクスケジューラ」と検索して起動
2. 右側の **「タスクの作成」** をクリック（「基本タスクの作成」ではなく「タスクの作成」）
3. **「全般」タブ**
   - 名前: 例として `CME FedWatch 取得`
   - 「ユーザーがログオンしている場合にのみ実行する」を選ぶ（手動実行に近い環境で動かすため）
4. **「トリガー」タブ** → **「新規」**
   - 「タスクの開始」: **「スケジュールに従う」**
   - 「設定」: **「毎日」**
   - 開始: 例として **9:00**（日本時間で使う場合は、Windows の時刻を「東京」にしておくか、実行したい日本時間に合わせる）
   - 「有効」にチェック → **OK**
   - 同様に **15:00 / 21:00 / 3:00** 用のトリガーを追加する（「新規」で毎日 15:00、毎日 21:00、毎日 3:00 を追加）
5. **「操作」タブ** → **「新規」**
   - 操作: **「プログラムの開始」**
   - プログラム/スクリプト:  
     **`C:\Users\あなたのユーザー名\Desktop\CME\run_cme.bat`**  
     （CME を置いたフォルダの **`run_cme.bat`** のフルパスに書き換える）
   - 引数の追加: 空のままでよい
   - 開始: **`C:\Users\あなたのユーザー名\Desktop\CME`**  
     （`main.py` があるフォルダのパス。run_cme.bat と同じ場所）
   - **OK**
6. **「条件」タブ**  
   - 「コンピューターを AC 電源で使用している場合のみタスクを実行する」のチェックを **外す**（ノートPC でも実行されるようにする）
7. **「設定」タブ**  
   - 必要に応じて「タスクがスケジュールに従って実行されない場合でも、要求時に実行する」にチェック
8. **OK** でタスクを作成する

これで、指定した時刻（PC が起動していれば）に自動実行されます。  
ログはプロジェクト内の **`logs\output.log`**（標準出力）と **`logs\error.log`**（標準エラー）に追記されます。

### Windows: よく使う操作

**手動で1回実行**

```cmd
cd C:\Users\あなたのユーザー名\Desktop\CME
venv\Scripts\activate
python main.py
```

**定期実行を止めたい・変えたい**

タスクスケジューラを開き、作成したタスク（例: `CME FedWatch 取得`）を右クリック → **「無効」** で停止。  
再開する場合は **「有効」** に戻す。時刻を変える場合はタスクをダブルクリックして「トリガー」を編集する。

**ログを確認する**（定期実行で `run_cme.bat` を使っている場合）

```cmd
type C:\Users\あなたのユーザー名\Desktop\CME\logs\output.log
type C:\Users\あなたのユーザー名\Desktop\CME\logs\error.log
```

（パスは CME を置いた場所に合わせて書き換えてください。直近だけ見る場合は、メモ帳で該当ファイルを開いてもかまいません。）

---

## よく使う操作

**※ 以下は Mac（macOS）向けのコマンドです。Windows の場合は「[Windows で使う場合](#windows-で使う場合)」内の「Windows: よく使う操作」を参照してください。**

### 手動で1回だけ実行する（Mac）

```bash
cd /Users/あなたのユーザー名/Desktop/CME
source venv/bin/activate
python main.py
```

### 定期実行を止めたいとき

```bash
launchctl unload ~/Library/LaunchAgents/com.cme.scraper.plist
```

### 定期実行を再開したいとき

```bash
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

### plist を編集したあと（パスや時刻を変えたあと）

```bash
launchctl unload ~/Library/LaunchAgents/com.cme.scraper.plist
cp /Users/あなたのユーザー名/Desktop/CME/com.cme.scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cme.scraper.plist
```

### ログを確認する（Mac）

```bash
# 直近の出力ログ
tail -30 /Users/あなたのユーザー名/Desktop/CME/logs/output.log

# 直近のエラーログ
tail -30 /Users/あなたのユーザー名/Desktop/CME/logs/error.log
```

Windows の場合は「[Windows で使う場合](#windows-で使う場合)」内の「Windows: よく使う操作」のログ確認を参照してください。

---

## トラブルシューティング

### 「認証ファイルが見つかりません」と出る

- `service_account.json` が **`main.py` と同じフォルダ** にあるか確認する
- ファイル名が **`service_account.json`** になっているか確認する（拡張子が `.json` のままでも可）

### 「スプレッドシートが見つかりません」と出る

- スプレッドシートの名前が **「CME定期調査」** になっているか確認する
- サービスアカウントのメールアドレスで **「編集者」として共有** されているか確認する

### ブラウザが起動しない

**Mac:** 次のコマンドで Chromium を入れ直します。

```bash
cd /Users/あなたのユーザー名/Desktop/CME
source venv/bin/activate
playwright install chromium
```

**Windows:** コマンドプロンプトまたは PowerShell で、プロジェクトのフォルダに移動して仮想環境を有効化したあと、同様に `playwright install chromium` を実行してください。

### 定期実行されているか分からない

**Mac:** 指定時刻のあとに `logs/output.log` を開き、実行時刻あたりにログが追記されているか確認する。`launchctl list com.cme.scraper` で登録されているか確認する。

**Windows:** タスクスケジューラで該当タスクが「有効」か確認する。指定時刻のあとに `logs\output.log` を開き、実行時刻あたりにログが追記されているか確認する。

### そのほかエラーが出たとき

- **Mac:** `logs/output.log` と `logs/error.log` の最後の方を確認する
- **Windows:** `logs\output.log` と `logs\error.log` の最後の方を確認する
- 出ているエラーメッセージをそのままコピーして、サポート担当者に共有すると原因を特定しやすいです

---

## 注意事項・セキュリティ

- **PC の電源**  
  定期実行は **PC が起動している間だけ** 動きます。スリープやシャットダウン中は実行されません。（Mac / Windows 共通）

- **インターネット**  
  実行時はインターネット接続が必要です。

- **`service_account.json`**  
  このファイルは **機密情報** です。  
  他人に送らない、Git にコミットしない、公開する場所に置かないでください。

- **スプレッドシート名を変えたい場合**  
  `main.py` を開き、`SPREADSHEET_NAME = "CME定期調査"` の部分を、使いたいスプレッドシート名に書き換えてください。

---

初めての方は、**ステップ1 → 2 → 3 → 4** まで進めれば手動実行まで完了します。  
定期実行が必要な場合だけ **ステップ5** を追加してください。
