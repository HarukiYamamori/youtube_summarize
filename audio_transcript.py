import os
import httpx
from google import genai
from google.genai import errors
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from logging import getLogger, basicConfig, INFO
import json

from audio_downloader import download_audio
from config import DEFAULT_MODEL, DEFAULT_FALLBACK_MODEL

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# 環境変数から取得
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.error("エラー: GOOGLE_API_KEY環境変数が設定されていません")
    raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")
# 混雑時にリクエストが応答しないまま止まらないよう、1リクエストあたりのタイムアウト（ミリ秒）を設定する
REQUEST_TIMEOUT_MS = 10 * 60 * 1000
client = genai.Client(api_key=GOOGLE_API_KEY, http_options={"timeout": REQUEST_TIMEOUT_MS})


def _is_retryable(e):
    """モデルの混雑・一時的な障害（5xx、429、タイムアウト）ならTrue"""
    if isinstance(e, errors.ServerError) or isinstance(e, httpx.TimeoutException):
        return True
    return isinstance(e, errors.ClientError) and e.code == 429


def _generate_content(contents, config, model, fallback_model):
    """generate_contentを呼ぶ。混雑などで失敗した場合は、fallback_modelで1回だけやり直す"""
    try:
        return client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as e:
        if not fallback_model or fallback_model == model or not _is_retryable(e):
            raise
        logger.warning(f"{model}で失敗したため、{fallback_model}でやり直します: {e}")
        return client.models.generate_content(model=fallback_model, contents=contents, config=config)


class Result(BaseModel):
    title: str = Field(description="動画タイトル")
    summary: str = Field(description="HTML形式の要約本文")
    genre: str = Field(description="ジャンル")


def summarize_audio(audio_path, title, link, model=DEFAULT_MODEL, fallback_model=DEFAULT_FALLBACK_MODEL):
    """音声ファイルをGeminiにアップロードし、1回の呼び出しで要約とジャンル判定を行う"""
    logger.info(f"Summarize file:{audio_path}")
    audio_file = client.files.upload(file=audio_path)
    try:
        return _summarize(audio_file, title, link, model, fallback_model)
    finally:
        # アップロードした音声ファイルをGeminiから削除
        try:
            client.files.delete(name=audio_file.name)
            logger.info(f"Deleted uploaded file: {audio_file.name}")
        except Exception as e:
            logger.warning(f"アップロードしたファイルの削除に失敗しました: {audio_file.name} - {e}")


def _summarize(audio_file, title, link, model, fallback_model):
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

    response = _generate_content(
        [prompt, audio_file],
        {
            "response_mime_type": "application/json",
            "response_schema": Result,
        },
        model,
        fallback_model,
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


class Digest(BaseModel):
    digest: str = Field(description="HTML形式のダイジェスト本文")


def synthesize_summaries(summaries, focus="", model=DEFAULT_MODEL, fallback_model=DEFAULT_FALLBACK_MODEL):
    """複数の動画の要約（HTML）を、トピック別の1つのダイジェスト（HTML）にまとめる。失敗した場合はNoneを返す"""
    joined = "\n\n".join(f"<!-- 要約{i} -->\n{summary}" for i, summary in enumerate(summaries, 1))
    focus_text = f"\n        【まとめ方の指示】\n        {focus}\n" if focus else ""

    prompt = f"""
        以下は複数のYouTube動画の要約（HTML）です。これらを横断して、1つのダイジェストにまとめ、HTML形式で出力してください。

        【まとめ方】
        - 動画単位ではなく、トピック単位で整理してください。
        - 複数の動画で同じ話題を扱っている場合は、1つのトピックに統合してください。
        - 重要度の高いトピックから順に並べてください。
        - 動画によって見解や伝え方が異なる点があれば、その違いも記載してください。
        - 各トピックの末尾に、出典となった動画のリンクを付けてください（各要約の<h1>内のリンクとタイトルを使う）。
        - 要約に書かれていない情報を補ったり、推測したりしないでください。
{focus_text}
        【HTMLの要件】
        - トピックの見出しは<h2>、内容は<ul><li>または<p>を使用
        - マークダウン記法は使用しない
        - 純粋なHTMLのみを出力

        【出力HTML形式】
        <h2>トピック1の見出し</h2>
        <ul>
            <li>ポイント1</li>
            <li>ポイント2</li>
        </ul>
        <p class="source">出典: <a href="動画のリンク">動画タイトル</a></p>

        【要約一覧】
        {joined}
    """

    try:
        response = _generate_content(
            [prompt],
            {
                "response_mime_type": "application/json",
                "response_schema": Digest,
            },
            model,
            fallback_model,
        )
        digest = Digest(**json.loads(response.text)).digest
    except Exception as e:
        logger.error(f"ダイジェストの生成に失敗しました: {e}")
        return None

    logger.info(f"Digest result:\n{digest}")
    return digest


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=5N7wwGoLrKs"
    title, audio_path = download_audio(url)
    summarize_audio(audio_path, title, url)

