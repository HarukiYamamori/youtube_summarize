import os
import sys
from logging import basicConfig, INFO, getLogger
from dotenv import load_dotenv

from audio_downloader import download_audio
from audio_transcript import summary_response, transcript
from crawl_videos import fetch_channel_data
from file_handler import delete_all_files
from gmail_sender import send_email

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 環境変数から設定を取得
channel_urls = os.getenv('CHANNEL_URLS', '')
email_addresses = os.getenv('EMAIL_ADDRESSES', '')

if not channel_urls:
    logger.error("エラー: CHANNEL_URLS環境変数が設定されていません")
    sys.exit(1)

if not email_addresses:
    logger.error("エラー: EMAIL_ADDRESSES環境変数が設定されていません")
    sys.exit(1)

urls_array = [item.strip() for item in channel_urls.split(",")]
email_array = [item.strip() for item in email_addresses.split(",")]

for channel_url in urls_array:
    logger.info("process start for %s", channel_url)
    videos_info, channel_name = fetch_channel_data(f"{channel_url}/videos")

    msg = ''

    for i in range(len(videos_info)):
        video_info = videos_info[i]
        # audioファイル(mp3)ダウンロード
        audiofile_path = download_audio(video_info.get("link"))

        # 文字起こし & 要約
        result = summary_response(transcript(audiofile_path), video_info.get("title"), video_info.get("link"))

        msg += result.summary
        msg += '<hr>'

    for address in email_array:
        # メール送信
        send_email(address, channel_name, msg)
        print(f'send_mail: {address}')

    delete_all_files()
