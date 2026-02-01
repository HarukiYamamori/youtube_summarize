import os
import yt_dlp
from urllib.parse import urlparse, parse_qs
from logging import getLogger, basicConfig, INFO
from pytubefix import YouTube
import traceback
from crawl_videos import fetch_video_title

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

def get_video_id(url):
    """YouTubeのURLから動画IDを取得"""
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query).get("v", [""])[0]

def download_audio(url):
    logger.info("Start download of audio")
    video_id = get_video_id(url)
    audio_path = f"data/{video_id}"
    result_path = f"{audio_path}.mp3"

    # data フォルダを作成（存在しない場合）
    os.makedirs("data", exist_ok=True)

    last_error = None
    try:
        download_with_youtube_dl(url, audio_path)
        if os.path.exists(result_path):
            logger.info(f"Saved at: {result_path}")
            return _get_title_and_return(result_path)
        # 例外なしで返ったがファイルが無い = ダウンロード失敗（yt-dlpが例外を投げない場合）
        logger.warning("yt-dlp returned but output file was not created")
        last_error = RuntimeError(f"yt-dlp did not create file: {result_path}")
    except Exception as e:
        last_error = e
        logger.error(f"Error downloading with youtube_dl: {e}")

    logger.info("Trying pytube as fallback...")
    try:
        download_with_pytube(url, audio_path)
        if os.path.exists(result_path):
            logger.info(f"Saved at: {result_path}")
            return _get_title_and_return(result_path)
        last_error = last_error or RuntimeError(f"pytube did not create file: {result_path}")
    except Exception as e:
        last_error = e
        logger.error(f"Error downloading with pytube: {e}")
        logger.error(traceback.format_exc())

    # 両方失敗した場合は例外を再送出
    if last_error:
        raise last_error
    raise FileNotFoundError(f"Download failed: {result_path} was not created")


def download_with_youtube_dl(url, audio_path):
    # yt-dlp 設定
    # ffmpegのパスを環境変数から取得、なければ自動検出
    import shutil
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        # 一般的なパスを試す
        for path in ['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg']:
            if os.path.exists(path):
                ffmpeg_path = path
                break
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': audio_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,  # プレイリストのダウンロードを防ぐ
    }
    
    # ffmpegが見つかった場合のみ設定
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path
    else:
        logger.warning("ffmpegが見つかりません。音声変換が失敗する可能性があります。")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_with_pytube(url, audio_path):
    yt = YouTube(url)
    output_path = os.path.dirname(audio_path)
    filename = f"{os.path.basename(audio_path)}.mp3"
    result_path = f"{output_path}/{filename}"
    logger.info(f"Downloading audio with pytube to: {result_path}")

    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream is None:
        raise RuntimeError("pytube: No audio stream found for this video")
    audio_stream.download(output_path=output_path, filename=filename)
    if not os.path.exists(result_path):
        raise RuntimeError(f"pytube: File was not created: {result_path}")
    return result_path


def _get_title_and_return(path):
    try:
        title = fetch_video_title(url)
    except Exception as e:
        logger.warning("Failed to fetch video title: %s", e)
        title = ""
    return (title, path)


if __name__ == "__main__":
    download_audio("https://www.youtube.com/watch?v=5N7wwGoLrKs")
