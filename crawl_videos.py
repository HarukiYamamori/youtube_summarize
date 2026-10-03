import time
from datetime import datetime
import yt_dlp
from playwright.sync_api import sync_playwright
from logging import getLogger, basicConfig, INFO

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 新着とみなす期間（時間）
NEW_VIDEO_HOURS = 24
# チャンネルごとに新着を確認する動画数の上限
MAX_CHECK_VIDEOS = 15

def fetch_channel_data(channel_url):
    """チャンネルの動画一覧から、直近NEW_VIDEO_HOURS時間以内に公開された動画を取得する"""
    video_info_list = []
    cutoff = time.time() - NEW_VIDEO_HOURS * 60 * 60

    # 動画一覧（新しい順）をIDとタイトルだけ取得
    flat_opts = {
        'extract_flat': 'in_playlist',
        'playlistend': MAX_CHECK_VIDEOS,
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(flat_opts) as ydl:
        channel_info = ydl.extract_info(channel_url, download=False)

    channel_name = channel_info.get("channel") or channel_info.get("uploader") or "チャンネル名が見つかりません"

    # 1本ずつ詳細を取得して、公開日時・公開範囲を判定
    with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
        for entry in channel_info.get("entries") or []:
            link = f"https://www.youtube.com/watch?v={entry.get('id')}"
            try:
                info = ydl.extract_info(link, download=False, process=False)
            except Exception as e:
                # メンバー限定動画などは取得できずに例外になる
                logger.info(f"動画情報を取得できないためスキップしました: {link} - {e}")
                continue

            timestamp = info.get("timestamp")
            if timestamp and timestamp < cutoff:
                # 一覧は新しい順なので、これ以降はすべて対象外
                break
            if not timestamp:
                logger.info(f"公開日時が不明なためスキップしました: {link}")
                continue
            if info.get("availability") in ("subscriber_only", "premium_only", "needs_auth"):
                logger.info(f"メンバー限定などの動画のためスキップしました: {link}")
                continue
            if info.get("live_status") in ("is_live", "is_upcoming"):
                logger.info(f"配信中・公開前の動画のためスキップしました: {link}")
                continue

            video_info_list.append({
                "title": info.get("title") or entry.get("title"),
                "link": link,
                "uploaded_date": datetime.fromtimestamp(timestamp).isoformat(),
            })

    logger.info(f"{channel_name}: 新着動画 {len(video_info_list)} 件")
    return video_info_list, channel_name


def fetch_video_title(video_url):
    title = None
    logger.info(f"Fetching video title for: {video_url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(video_url)
        page.wait_for_load_state("networkidle")
        title = page.query_selector("#title").text_content().strip()

        browser.close()

        logger.info(f"Video title: {title}")

        return title



if __name__ == "__main__":
    title = fetch_video_title("https://www.youtube.com/watch?v=RI4nZL1M4mI")
    print("Title:", title)
