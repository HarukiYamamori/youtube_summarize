import configparser
import os
import google.generativeai as genai
from logging import getLogger, basicConfig, INFO

from audio_downloader import download_audio

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

GOOGLE_API_KEY = config.get('ai_setting', 'GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash-001")

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

