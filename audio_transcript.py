import os
import time
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


# 混雑はしばらく待つと解消することが多いので、「model → fallback_model」の一巡を、待ち時間を空けて最大この回数まで繰り返す
GENERATE_ROUNDS = 3
# 一巡がすべて失敗したときの待ち時間（秒）。n巡目の後は ROUND_WAIT_SECONDS * n 秒待つ
ROUND_WAIT_SECONDS = 60


def _generate_content(contents, config, model, fallback_model):
    """generate_contentを呼ぶ。混雑などで失敗した場合は、fallback_modelでやり直す

    model・fallback_modelの両方が失敗した場合は、待ち時間を空けて最大GENERATE_ROUNDS巡まで繰り返す。
    混雑以外のエラー（400など）は、やり直さずにそのまま送出する。
    """
    models = [model] if not fallback_model or fallback_model == model else [model, fallback_model]
    for round_no in range(1, GENERATE_ROUNDS + 1):
        for i, m in enumerate(models):
            try:
                return client.models.generate_content(model=m, contents=contents, config=config)
            except Exception as e:
                if not _is_retryable(e):
                    raise
                last_error = e
                if i + 1 < len(models):
                    logger.warning(f"{m}で失敗したため、{models[i + 1]}でやり直します: {e}")
                else:
                    logger.warning(f"{m}で失敗しました（{round_no}/{GENERATE_ROUNDS}巡目）: {e}")
        if round_no < GENERATE_ROUNDS:
            wait = ROUND_WAIT_SECONDS * round_no
            logger.info(f"{wait}秒待ってからやり直します")
            time.sleep(wait)
    raise last_error


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
    title: str = Field(description="全体の内容を表すタイトル")
    digest: str = Field(description="HTML形式のダイジェスト本文")


def synthesize_summaries(summaries, focus="", model=DEFAULT_MODEL, fallback_model=DEFAULT_FALLBACK_MODEL):
    """複数の動画の要約（HTML）を、トピック別の1つのダイジェスト（HTML）とタイトルにまとめる。失敗した場合はNoneを返す"""
    joined = "\n\n".join(f"<!-- 要約{i} -->\n{summary}" for i, summary in enumerate(summaries, 1))
    focus_text = f"\n        【まとめ方の指示】\n        {focus}\n" if focus else ""

    prompt = f"""
        以下は複数のYouTube動画の要約（HTML）です。これらを横断して、1つのダイジェストにまとめ、HTML形式で出力してください。
        あわせて、ダイジェスト全体の内容を表すタイトル（メールの件名になる。30文字程度）を付けてください。

        【まとめ方】
        - 動画単位ではなく、トピック単位で整理してください。
        - 複数の動画で同じ話題を扱っている場合は、1つのトピックに統合してください。
        - 重要度の高いトピックから順に並べてください。
        - 動画によって見解や伝え方が異なる点があれば、その違いも記載してください。
        - 要約に書かれていない情報を補ったり、推測したりしないでください。
{focus_text}
        【HTMLの要件】
        - トピックの見出しは<h2>、内容は<ul><li>または<p>を使用
        - 動画へのリンクや出典は付けない（動画の一覧は別に付ける）
        - マークダウン記法は使用しない
        - 純粋なHTMLのみを出力

        【出力HTML形式】
        <h2>トピック1の見出し</h2>
        <ul>
            <li>ポイント1</li>
            <li>ポイント2</li>
        </ul>

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
        digest = Digest(**json.loads(response.text))
    except Exception as e:
        logger.error(f"ダイジェストの生成に失敗しました: {e}")
        return None

    logger.info(f"Digest title: {digest.title}")
    logger.info(f"Digest result:\n{digest.digest}")
    return digest


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=5N7wwGoLrKs"
    title, audio_path = download_audio(url)
    summarize_audio(audio_path, title, url)

