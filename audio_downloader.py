import configparser
import os
import yt_dlp
from urllib.parse import urlparse, parse_qs
from logging import getLogger, basicConfig, INFO

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 設定ファイルの読み込み（必要ならば config.ini を使う）
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

def get_video_id(url):
    """YouTubeのURLから動画IDを取得"""
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query).get("v", [""])[0]

def download_audio(url):
    logger.info("Start download of audio")
    video_id = get_video_id(url)
    audio_path = f"data/{video_id}"

    # data フォルダを作成（存在しない場合）
    os.makedirs("data", exist_ok=True)

    # yt-dlp 設定
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': audio_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,  # プレイリストのダウンロードを防ぐ
        'ffmpeg_location': '/usr/bin/ffmpeg',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    logger.info(f"Saved at: {audio_path}.mp3")
    return f"{audio_path}.mp3"

if __name__ == "__main__":
    download_audio("https://www.youtube.com/watch?v=5N7wwGoLrKs")
