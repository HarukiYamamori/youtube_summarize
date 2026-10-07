import os
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from logging import getLogger, basicConfig, INFO
import json

from audio_downloader import download_audio
from config import DEFAULT_MODEL

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 環境変数から取得
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.error("エラー: GOOGLE_API_KEY環境変数が設定されていません")
    raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")
client = genai.Client(api_key=GOOGLE_API_KEY)


class Result(BaseModel):
    title: str = Field(description="動画タイトル")
    summary: str = Field(description="HTML形式の要約本文")
    genre: str = Field(description="ジャンル")


def summarize_audio(audio_path, title, link, model=DEFAULT_MODEL):
    """音声ファイルをGeminiにアップロードし、1回の呼び出しで要約とジャンル判定を行う"""
    logger.info(f"Summarize file:{audio_path}")
    audio_file = client.files.upload(file=audio_path)
    try:
        return _summarize(audio_file, title, link, model)
    finally:
        # アップロードした音声ファイルをGeminiから削除
        try:
            client.files.delete(name=audio_file.name)
            logger.info(f"Deleted uploaded file: {audio_file.name}")
        except Exception as e:
            logger.warning(f"アップロードしたファイルの削除に失敗しました: {audio_file.name} - {e}")


def _summarize(audio_file, title, link, model):
    prompt = f"""
        添付の音声ファイルの内容を要約し、構造化されたHTML形式で出力してください。

        【出力形式の要件】
        1. HTMLの構造は以下の通りにしてください：
        - <h1>タグ: 動画タイトルをリンクとして表示（リンク先: {link}）
        - なお、タイトルがない場合は、音声の内容から動画タイトルを自由に生成してください。
        - <div class="summary">タグ: 要約内容を表示

        2. 要約内容の構造：
        - 重要なポイントを箇条書き（<ul><li>）または段落（<p>）で整理
        - 見出しが必要な場合は<h2>または<h3>を使用
        - 読みやすく、論理的な順序で構成

        3. HTMLの品質：
        - 適切なセマンティックHTMLタグを使用
        - マークダウン記法（など）は使用しない
        - 純粋なHTMLのみを出力

        【入力情報】
        動画タイトル: {title}
        本文: 添付の音声ファイル

        【ジャンル判定】
        音声の内容を分析し、以下のいずれかのジャンルを選択してください：
        - 政治経済
        - 社会
        - 文化
        - 体育
        - アート
        - 音楽
        - テクノロジー
        - 科学
        - 教育
        - エンタメ
        - グルメ
        - 旅行
        - ヘルスケア
        - ビジネス
        - ファッション
        - 生活情報
        - その他

        【出力HTML形式】
        <h1><a href="{link}">動画タイトル（タイトルは音声の内容を踏まえて自由に生成してください）</a></h1>
        <div class="genre">ジャンル: テクノロジー</div>
        <div class="summary">
        <h2>概要</h2>
        <p>要約の最初の段落...</p>
        <h3>主なポイント</h3>
        <ul>
            <li>ポイント1</li>
            <li>ポイント2</li>
        </ul>
        </div>

        上記の形式に従って、要約を生成してください。    
    """

    response = client.models.generate_content(
        model=model,
        contents=[prompt, audio_file],
        config={
            "response_mime_type": "application/json",
            "response_schema": Result,
        },
    )
    
    # レスポンスの検証
    if not response.candidates or not response.candidates[0].content.parts:
        finish_reason = response.candidates[0].finish_reason if response.candidates else "不明"
        logger.error(f"要約に失敗しました。finish_reason: {finish_reason}")
        # エラーの場合は、デフォルト値でResultオブジェクトを返す
        return Result(
            title=title or "タイトル不明",
            summary=f"<h1><a href=\"{link}\">{title}</a></h1><p>要約の生成に失敗しました。finish_reason: {finish_reason}</p>",
            genre="その他"
        )
    
    try:
        result_json = json.loads(response.text)
        result = Result(**result_json)
        
        logger.info(f"Title: {result.title}")
        logger.info(f"Summary result:\n{result.summary}")
        logger.info(f"Genre: {result.genre}")
        
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSONのパースに失敗しました: {e}")
        logger.error(f"Response text: {response.text}")
        return Result(
            title=title or "タイトル不明",
            summary=f"<h1><a href=\"{link}\">{title}</a></h1><p>要約の生成に失敗しました。JSONパースエラー</p>",
            genre="その他"
        )


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=5N7wwGoLrKs"
    title, audio_path = download_audio(url)
    summarize_audio(audio_path, title, url)

