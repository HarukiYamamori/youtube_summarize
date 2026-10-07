import html
import sys
from logging import basicConfig, INFO, getLogger
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（各モジュールのimport前に読み込む）
load_dotenv()

from audio_downloader import download_audio
from audio_transcript import summarize_audio, synthesize_summaries
from config import load_config
from crawl_videos import fetch_channel_data
from file_handler import delete_all_files
from gmail_sender import GmailAuthError, get_gmail_service, send_email

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


def summarize_video(link, title, config):
    """動画をダウンロードして要約する。失敗した場合はNoneを返す"""
    try:
        # audioファイル(mp3)ダウンロード
        downloaded_title, audiofile_path = download_audio(link)
    except Exception as e:
        logger.error(f"ダウンロードをスキップしました: {link} - {e}")
        return None

    try:
        # 要約
        return summarize_audio(audiofile_path, title or downloaded_title, link, model=config.model, fallback_model=config.fallback_model)
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

def summarize_target(url, config):
    """URL（単一動画またはチャンネル）の動画を要約し、(名前, [(要約結果, 動画のリンク), ...])を返す

    名前は、単一動画なら動画タイトル、チャンネルならチャンネル名。
    """
    if "/watch?" in url:
        result = summarize_video(url, "", config)
        return (result.title if result else url), ([(result, url)] if result else [])

    logger.info("process start for %s", url)
    videos_info, channel_name = fetch_channel_data(
        f"{url}/videos",
        new_video_hours=config.new_video_hours,
        max_check_videos=config.max_check_videos,
    )

    results = []
    for video_info in videos_info:
        result = summarize_video(video_info.get("link"), video_info.get("title"), config)
        if result:
            results.append((result, video_info.get("link")))
    return channel_name, results


for target in config.targets:
    name, results = summarize_target(target.url, config)

    if "/watch?" in target.url:
        for result, _ in results:
            for address in target.recipients:
                # メール送信（genreをラベルとして使用）
                send_email(address, result.title, result.summary, label_name=result.genre or None)
                print(f'send_mail: {address}')

    elif not results:
        logger.info("送信する要約が無いため、メール送信をスキップしました: %s", name)
    else:
        msg = ''.join(result.summary + '<hr>' for result, _ in results)
        for address in target.recipients:
            # メール送信
            send_email(address, name, msg)
            print(f'send_mail: {address}')

    delete_all_files()

for group in config.groups:
    logger.info("group start for %s", group.name)
    results = []
    for url in group.urls:
        try:
            _, url_results = summarize_target(url, config)
        except Exception as e:
            logger.error(f"URLの処理をスキップしました: {url} - {e}")
            url_results = []
        results.extend(url_results)
        delete_all_files()

    if not results:
        logger.info("送信する要約が無いため、メール送信をスキップしました: %s", group.name)
        continue

    summaries = [result.summary for result, _ in results]
    # 要約が1件ならまとめる必要が無いので、ダイジェストは作らない
    digest = synthesize_summaries(summaries, group.focus, config.model, config.fallback_model) if len(summaries) > 1 else None

    # 件名：ダイジェストで生成したタイトル。無ければ（要約が1件なら）動画タイトル、それも無ければグループ名
    if digest and digest.title:
        subject = digest.title
    elif len(results) == 1:
        subject = results[0][0].title
    else:
        subject = group.name

    msg = ''
    if digest:
        # 動画のリンクはGeminiに書かせず、ダイジェストの下に一覧で付ける
        sources = ''.join(f'<li><a href="{html.escape(link, quote=True)}">{html.escape(result.title)}</a></li>' for result, link in results)
        msg += f'<h1>ダイジェスト</h1>{digest.digest}<h2>参照した動画</h2><ul>{sources}</ul><hr><h1>個別の要約</h1>'
    elif len(summaries) > 1:
        msg += '<p>ダイジェストの生成に失敗したため、個別の要約のみを送ります。</p><hr>'
    msg += ''.join(summary + '<hr>' for summary in summaries)

    for address in group.recipients:
        # メール送信
        send_email(address, subject, msg)
        print(f'send_mail: {address}')
