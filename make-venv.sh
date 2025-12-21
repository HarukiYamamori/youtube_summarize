#!/bin/bash

# Python 3.12で仮想環境を作成
echo "Python 3.12で仮想環境を作成中..."
python3.12 -m venv venv

# 仮想環境内のPythonバージョンを確認
echo "仮想環境内のPythonバージョン:"
venv/bin/python --version

# 有効化コマンドをログ出力
echo ""
echo "仮想環境を有効化するには、以下のコマンドを実行してください:"
echo "source venv/bin/activate"

