import sys
from logging import basicConfig, INFO, getLogger
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（各モジュールのimport前に読み込む）
load_dotenv()

from audio_downloader import download_audio
from audio_transcript import summarize_audio
from config import load_config
from crawl_videos import fetch_channel_data
from file_handler import delete_all_files
from gmail_sender import GmailAuthError, get_gmail_service, send_email

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


def summarize_video(link, title, model):
    """動画をダウンロードして要約する。失敗した場合はNoneを返す"""
    try:
        # audioファイル(mp3)ダウンロード
        downloaded_title, audiofile_path = download_audio(link)
    except Exception as e:
        logger.error(f"ダウンロードをスキップしました: {link} - {e}")
        return None

    try:
        # 要約
        return summarize_audio(audiofile_path, title or downloaded_title, link, model=model)
    except Exception as e:
        logger.error(f"要約をスキップしました: {link} - {e}")
        return None


try:
    config = load_config()
except ValueError as e:
    logger.error(f"エラー: {e}")
    sys.exit(1)

# 動画の処理を始める前に、Gmailの認証が通るか確認する
try:
    get_gmail_service()
except GmailAuthError as e:
    logger.error(f"エラー: {e}")
    sys.exit(1)

for target in config.targets:
    if "/watch?" in target.url:
        result = summarize_video(target.url, "", config.model)

        if result:
            for address in target.recipients:
                # メール送信（genreをラベルとして使用）
                send_email(address, result.title, result.summary, label_name=result.genre or None)
                print(f'send_mail: {address}')

    else:
        logger.info("process start for %s", target.url)
        videos_info, channel_name = fetch_channel_data(
            f"{target.url}/videos",
            new_video_hours=config.new_video_hours,
            max_check_videos=config.max_check_videos,
        )

        msg = ''
        for video_info in videos_info:
            result = summarize_video(video_info.get("link"), video_info.get("title"), config.model)
            if result:
                msg += result.summary
                msg += '<hr>'

        if not msg:
            logger.info("送信する要約が無いため、メール送信をスキップしました: %s", channel_name)
        else:
            for address in target.recipients:
                # メール送信
                send_email(address, channel_name, msg)
                print(f'send_mail: {address}')

    delete_all_files()
