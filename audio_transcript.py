import configparser
import os
import google.generativeai as genai
from logging import getLogger, basicConfig, INFO

from audio_downloader import download_audio

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 環境変数から取得
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.error("エラー: GOOGLE_API_KEY環境変数が設定されていません")
    raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")
client = genai.Client(api_key=GOOGLE_API_KEY)
model = "gemini-2.5-flash"

def transcript(audio_path):
    logger.info(f"Transcribe file:{audio_path}")
    audio_file = genai.upload_file(path=audio_path)

    # プロンプトの準備
    response = model.generate_content(
        [
            "次の音声ファイルの内容を文字起こししてください。",
            audio_file
        ]
    )
    logger.info(f"Transcription result: {response.text}")
    return response.text


def summary_response(txt, title, link):
    logger.info("Summarize")
    prompt = f"次のテキストの内容を日本語で要約し、HTML形式で出力してください。<h1>にはリンクとして「{link}」を埋め込んでください。\n動画タイトル「{title}」\n本文「{txt}」"
    response = model.generate_content(prompt).text
    if '```html' in response:
        response = response.replace('```html', '')
    if '```' in response:
        response = response.replace('```', '')
    logger.info(f"Summary result:\n{response}")
    return response


if __name__ == "__main__":
    audio_file = download_audio("https://www.youtube.com/watch?v=5N7wwGoLrKs")
    summary_response(transcript(audio_file), "", "")

