#!/bin/bash

# Python 3.12がインストールされているか確認
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12が見つかりません。"
    read -p "HomebrewでPython 3.12をインストールしますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Python 3.12をインストール中..."
        brew install python@3.12
        if [ $? -ne 0 ]; then
            echo "エラー: Python 3.12のインストールに失敗しました。"
            exit 1
        fi
        echo "Python 3.12のインストールが完了しました。"
    else
        echo "インストールをキャンセルしました。"
        exit 1
    fi
fi

# Python 3.12で仮想環境を作成
echo "Python 3.12で仮想環境を作成中..."
python3.12 -m venv venv

# 仮想環境内のPythonバージョンを確認
echo "仮想環境内のPythonバージョン:"
venv/bin/python --version

# 仮想環境を有効化して依存パッケージをインストール
echo ""
echo "依存パッケージをインストール中..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ffmpegのインストール確認（macOSの場合）
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v ffmpeg &> /dev/null; then
        echo ""
        echo "ffmpegが見つかりません。"
        read -p "Homebrewでffmpegをインストールしますか？ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "ffmpegをインストール中..."
            brew install ffmpeg
            if [ $? -ne 0 ]; then
                echo "エラー: ffmpegのインストールに失敗しました。"
                exit 1
            fi
            echo "ffmpegのインストールが完了しました。"
        else
            echo "ffmpegのインストールをスキップしました。後で手動でインストールしてください。"
        fi
    else
        echo "ffmpegは既にインストールされています。"
    fi
fi

# 有効化コマンドをログ出力
echo ""
echo "セットアップが完了しました！"
echo "仮想環境を有効化するには、以下のコマンドを実行してください:"
echo "source venv/bin/activate"

