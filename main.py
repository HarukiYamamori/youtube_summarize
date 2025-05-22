import configparser
import sys
from logging import basicConfig, INFO, getLogger

from audio_downloader import download_audio
from audio_transcript import summary_response, transcript
from crawl_videos import fetch_channel_data
from file_handler import delete_all_files
from gmail_sender import send_email

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# メールアドレスなどのsetting
args = sys.argv[1:]

if not args:
    logger.error("エラー: 設定名が指定されていません")
    sys.exit(1)

config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

channel_urls = config.get(args[0], 'channel_urls')
email_addresses = config.get(args[0], 'email_addresses')
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
        news_summary = summary_response(transcript(audiofile_path), video_info.get("title"), video_info.get("link"))

        msg += news_summary
        msg += '<hr>'

    for address in email_array:
        # メール送信
        send_email(address, channel_name, msg)
        print(f'send_mail: {address}')

    delete_all_files()
