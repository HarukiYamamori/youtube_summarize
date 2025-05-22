import os
from pytubefix import YouTube
from urllib.parse import urlparse, parse_qs


def get_video_id(url):
    parsed_url = urlparse(url)
    video_id = parse_qs(parsed_url.query).get("v", [""])[0]
    return video_id


def download_audio(video_url):
    yt = YouTube(video_url)
    video_id = get_video_id(video_url)

    # data フォルダを作成（存在しない場合）
    os.makedirs("data", exist_ok=True)

    # 音声ストリームをダウンロード
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_path = f"data/{video_id}.mp3"
    audio_stream.download(filename=audio_path)

    return audio_path


# 動画URL
video_url = "https://www.youtube.com/watch?v=O8ApXMKy0sY"

# 音声ダウンロード
downloaded_file = download_audio(video_url)

print("保存先:", downloaded_file)  # data/O8ApXMKy0sY.mp3
