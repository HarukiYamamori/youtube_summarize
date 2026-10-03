# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

新着のYouTube動画を探し、Google Geminiで文字起こしと要約を行い、HTML形式の要約をGmail APIでメール送信するバッチスクリプト。GCP上で1日1回実行される。コードのコメント・ログメッセージ・LLMプロンプト・READMEは日本語で書かれているので、この慣例に従うこと。

## セットアップと実行

```bash
./make-venv.sh              # Python 3.12でvenv/を作成し、requirementsのインストール、ffmpeg（macOS）とPlaywright Chromiumのセットアップまで行う
source venv/bin/activate
python main.py              # パイプライン全体を実行
```

外部依存として、PATH上の`ffmpeg`（yt-dlpのmp3変換に必要）とPlaywrightのChromiumブラウザ（`playwright install chromium`）が必要。

設定はpython-dotenvで`.env`から読み込む。`CHANNEL_URLS`・`EMAIL_ADDRESSES`・`GOOGLE_API_KEY`は必須で、`GMAIL_ADDRESS`は送信元アドレス。`GMAIL_PASSWORD`と`MAIL_TITLE`はREADMEに記載があるが、どこからも使われていない。メールはSMTPではなく、OAuth認証のGmail API経由で送るため。

Gmail OAuthでは`credentials.json`（クライアントシークレット）を使い、トークンを`token.pickle`にキャッシュする。トークンが無いか更新できない場合、`get_gmail_service()`がローカルのブラウザで認証フローを開く。詳細は`GMAIL_API_SETUP.md`を参照。これらのファイル、`.env`、`data/`はすべてgitignore対象。

## テスト

テストスイート・リンター・フォーマッターは無い。`test.py`は古いpytubefixの試作スクリプトで、importした時点で動画をダウンロードしてしまう。各モジュールには手動確認用の`if __name__ == "__main__":`ブロックがある（`python crawl_videos.py`、`python audio_downloader.py`など）。これらは実サービスを呼び出す。`audio_transcript.py`のブロックは古いまま動かない（`download_audio`が現在は`(title, path)`のタプルを返すため）。

## アーキテクチャ

`main.py`は`main()`関数を持たないトップレベルのスクリプト。カンマ区切りの`CHANNEL_URLS`を順に処理し、各URLは次の2通りのどちらかで処理される。

- **単一動画のURL**（`/watch?`を含む）：ダウンロード → 文字起こし → 要約。**動画1本につきメール1通**を送る。件名はGeminiが生成したタイトルで、判定された`genre`をGmailラベルとして付ける。
- **チャンネルのURL**：`crawl_videos.fetch_channel_data(f"{url}/videos")`が、ヘッドレスのPlaywrightでチャンネルの動画一覧ページをスクレイピングする。投稿日表示が時間・分・秒単位のもの（`時間前`・`hours ago`など、日本語と英語の両方の文字列）だけを残すので、おおむね直近24時間の動画が対象になる。メンバー限定動画（`aria-label='メンバー限定'`）はスキップする。そのチャンネルの要約をすべて`<hr>`でつなぎ、**チャンネルごとにメール1通**として送る。件名はチャンネル名で、ラベルは付かない。

各URLの処理が終わるたびに、`file_handler.delete_all_files()`で`data/`を空にする。

各モジュールの役割:
- `audio_downloader.download_audio(url)`は`data/<video_id>.mp3`に保存し、`(title, path)`を返す。まずyt-dlpで試し、失敗したらpytubefixにフォールバックする。例外が出なくても出力ファイルが無ければ失敗として扱う。タイトルは別途Playwrightでページを読み込んで取得する（`crawl_videos.fetch_video_title`）。取得に失敗した場合、タイトルは`""`になる。
- `audio_transcript`は`google-genai` SDKを使う。モデル名は`model`にハードコードされている（現在は`gemini-3-flash-preview`。READMEには2.0 Flashと書かれている）。`transcript()`は音声ファイルをアップロードして文字起こしを依頼する。`summary_response()`はPydanticの`Result(title, summary, genre)`に沿った構造化JSONを要求する。`summary`はHTMLで、`genre`はプロンプト内に固定で並べた日本語ジャンルのいずれか。
- `gmail_sender.send_email(to, name, body, label_name=None)`は件名を`【YouTube Summary】{name}`にする。メールを送信したあと`messages.modify`でラベルを付ける（ラベルが存在しなければ先に作成する）。エラーはログに出すだけで、例外として投げない。

## 注意点

- `audio_transcript.py`は、`GOOGLE_API_KEY`が未設定だと**import時に**`ValueError`を投げる。そのため`main`や`audio_transcript`をimportするには環境変数の設定が必要。
- `summary_response`がエラー時に作るフォールバックの`Result(...)`は、必須フィールドの`title`が抜けている。そのためフォールバックを返す代わりにPydanticの`ValidationError`が発生する。
- チャンネルのスクレイパーは、YouTubeのDOMセレクタ（`.ytd-rich-grid-media`、`a#thumbnail`、`#metadata-line`、`h1[aria-label]`）と、相対日付表示の言語に依存している。YouTubeのUIが変わると、分かりやすいエラーを出さずに壊れることが多い。
- 各モジュールがimport時に`basicConfig`を呼んでいるため、最初にimportされたモジュールの設定が有効になる。
