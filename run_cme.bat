@echo off
REM 定期実行（タスクスケジューラ）用。ログを logs フォルダに残します。
cd /d "%~dp0"
if not exist logs mkdir logs
call venv\Scripts\activate.bat
python main.py >> logs\output.log 2>> logs\error.log
