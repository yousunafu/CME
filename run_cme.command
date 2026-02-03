#!/bin/zsh
# 定期実行（launchd）用: open -a Terminal で開かれる。
# 手動でターミナルから実行するのと同じ流れ・同じ環境で動くため、ブラウザも表示される。

cd "$(dirname "$0")"
./venv/bin/python3 main.py
echo ""
echo "※ 実行終了時にこのターミナルを自動で閉じたい場合:"
echo "   Terminal > 設定 > プロファイル > シェル で「シェルが正常に終了したら閉じる」にチェックを入れてください。"
exit 0
