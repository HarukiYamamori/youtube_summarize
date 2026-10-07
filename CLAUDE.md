# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

新着のYouTube動画を探し、Google Geminiで要約し、HTML形式の要約をGmail APIでメール送信するバッチスクリプト。GCP上で1日1回実行される。コードのコメント・ログメッセージ・LLMプロンプト・READMEは日本語で書かれているので、この慣例に従うこと。

## セットアップと実行

```bash
./make-venv.sh              # Python 3.12でvenv/を作成し、requirementsのインストールとffmpeg（macOS）のセットアップまで行う
source venv/bin/activate
python gmail_auth.py        # 初回・トークン切れ時のみ。ブラウザでGmailのOAuth認証を行い、token.pickleを保存
python main.py              # パイプライン全体を実行
```

外部依存として、PATH上の`ffmpeg`（yt-dlpのmp3変換に必要）が必要。

設定は2か所にある。
- **`config.toml`**（`config.example.toml`をコピーして作る。宛先アドレスが入るのでgitignore対象）：対象URL（`[[targets]]`）、まとめて送るURL群（`[[groups]]`：`name`・`urls`・任意の`recipients`と`focus`）、送信先（全体の`recipients`と、ターゲットごとの上書き）、Geminiのモデル名、新着とみなす時間、チャンネルごとの確認本数。パスは環境変数`CONFIG_PATH`で変えられる。`config.toml`が無い場合は、環境変数`CHANNEL_URLS`・`EMAIL_ADDRESSES`（カンマ区切り）から読み込む（`config.load_config`）。
- **`.env`**（python-dotenv）：秘密情報。`GOOGLE_API_KEY`は必須で、`GMAIL_ADDRESS`は送信元アドレス。`GMAIL_PASSWORD`と`MAIL_TITLE`はREADMEに記載があるが、どこからも使われていない。メールはSMTPではなく、OAuth認証のGmail API経由で送るため。

Gmail OAuthでは`credentials.json`（クライアントシークレット）を使い、トークンを`token.pickle`にキャッシュする。`get_gmail_service()`はブラウザを開かない。トークンが無い・更新できない場合は`GmailAuthError`を投げ、`main.py`は動画を処理する前に終了する。再認証は`python gmail_auth.py`で行う。詳細は`GMAIL_API_SETUP.md`を参照。`credentials.json`、`token.pickle`、`.env`、`config.toml`、`data/`はすべてgitignore対象。

## テスト

テストスイート・リンター・フォーマッターは無い。`test.py`は古いpytubefixの試作スクリプトで、importした時点で動画をダウンロードしてしまう。各モジュールには手動確認用の`if __name__ == "__main__":`ブロックがある（`python crawl_videos.py`、`python audio_downloader.py`、`python audio_transcript.py`）。これらは実サービスを呼び出す。

## アーキテクチャ

`main.py`は`main()`関数を持たないトップレベルのスクリプト。`load_config()`で設定を読み、Gmailの認証を確認してから、`config.targets`を順に処理する。各ターゲットは次の2通りのどちらかで処理され、メールはそのターゲットの`recipients`に送る。

- **単一動画のURL**（`/watch?`を含む）：ダウンロード → 要約。**動画1本につきメール1通**を送る。件名はYouTubeの動画タイトル（取れなければGeminiが生成したタイトル）で、判定された`genre`をGmailラベルとして付ける。
- **チャンネルのURL**：`crawl_videos.fetch_channel_data(f"{url}/videos", new_video_hours, max_check_videos)`が、yt-dlpで動画一覧（新しい順に最大`max_check_videos`本）を取得し、1本ずつ詳細を取って公開日時（`timestamp`）が直近`new_video_hours`時間以内のものを残す。期間外の動画が出た時点で打ち切る。メンバー限定（`availability`）、配信中・公開前（`live_status`）、情報を取得できない動画はスキップする。そのチャンネルの要約をすべて`<hr>`でつなぎ、**チャンネルごとにメール1通**として送る。件名はチャンネル名で、ラベルは付かない。送る要約が1件も無ければ送信しない。

`config.targets`の後に`config.groups`を処理する。グループ内の各URLを上と同じ`summarize_target`で要約し（URL単位の例外はログに出してスキップ）、要約が2件以上なら`audio_transcript.synthesize_summaries(summaries, focus, model)`で各要約のHTMLテキストだけからトピック別ダイジェストを作る（音声は再アップロードしない）。メールは**グループごとに1通**で、件名はグループの`name`、本文は「ダイジェスト → 個別の要約」の順。ダイジェスト生成に失敗した場合は個別の要約だけを送る。

ダウンロードや要約に失敗した動画は、ログに出してスキップする（`main.summarize_video`がNoneを返す）。各ターゲットの処理が終わるたびに、`file_handler.delete_all_files()`で`data/`を空にする。

各モジュールの役割:
- `audio_downloader.download_audio(url)`は`data/<video_id>.mp3`に保存し、`(title, path)`を返す。まずyt-dlpで試し、失敗したらpytubefixにフォールバックする。例外が出なくても出力ファイルが無ければ失敗として扱う。タイトルはダウンロードしたライブラリが返した情報から取る。
- `audio_transcript.summarize_audio(path, title, link, model)`は`google-genai` SDKを使い、音声ファイルをアップロードして、**1回の呼び出しで**Pydanticの`Result(title, summary, genre)`に沿った構造化JSONを要求する（文字起こしは別に行わない）。`summary`はHTMLで、`genre`はプロンプト内に固定で並べた日本語ジャンルのいずれか。アップロードしたファイルは`finally`で削除する。応答が空・JSONでない場合は、失敗した旨のHTMLを入れた`Result`を返す（メールにはその内容が載る）。
- `gmail_sender.send_email(to, name, body, label_name=None)`は件名を`【YouTube Summary】{name}`にする。メールを送信したあと`messages.modify`でラベルを付ける（ラベルが存在しなければ先に作成する）。エラーはログに出すだけで、例外として投げない。
- Geminiの呼び出しはすべて`audio_transcript._generate_content`を通る。5xx・429・タイムアウトで失敗した場合は、`fallback_model`で1回だけやり直す（`fallback_model`が空、または`model`と同じ場合はやり直さない）。混雑時にリクエストが止まったままにならないよう、クライアントには1リクエスト10分のタイムアウトを設定している。
- 設定の既定値（モデル名`gemini-3-flash-preview`、フォールバック`gemini-flash-latest`、24時間、15本）は`config.py`の`DEFAULT_*`にある。

## 注意点

- `audio_transcript.py`は、`GOOGLE_API_KEY`が未設定だと**import時に**`ValueError`を投げる。そのため`main`や`audio_transcript`をimportするには環境変数の設定が必要。
- YouTubeのRSS（`feeds/videos.xml`）は2026-10時点で全チャンネル404を返していたため、新着取得はyt-dlpで行っている。
- 1日に`max_check_videos`本より多く投稿するチャンネルでは、それを超えた分は取りこぼす。
- OAuth同意画面が「テスト」状態の外部アプリだと、リフレッシュトークンは7日で失効する。その場合は毎週`gmail_auth.py`での再認証が必要になる。
- 各モジュールがimport時に`basicConfig`を呼んでいるため、最初にimportされたモジュールの設定が有効になる。
