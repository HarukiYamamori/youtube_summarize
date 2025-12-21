# YouTube動画サマリーシステム

## 概要
本システムは、指定したYouTube動画を自動でダウンロードし、文字起こし・翻訳・要約を行い、その結果をGmailで送信する自動化システムです。
GCP環境にて日次で定期実行され、日々の情報収集や動画要約に役立ちます。

## 使用技術
### 言語・ライブラリ
- Python 3.11
- yt-dlp（YouTube動画のダウンロード）
- Google Gemini 2.0 Flash（文字起こし・翻訳・要約）
- Gmail API（メール送信）
- python-dotenv（環境変数管理）

### 実行環境
Google Cloud Platform（GCP）上のインスタンスで日次スケジューリング実行

## 環境変数の設定

### 方法1: .envファイルを使用（推奨）

プロジェクトルートに`.env`ファイルを作成し、以下のように設定してください：

```env
GOOGLE_API_KEY=your-google-api-key-here
CHANNEL_URLS=https://www.youtube.com/@CNN, https://www.youtube.com/@BBC
EMAIL_ADDRESSES=sample1@gmail.com, sample2@gmail.com
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_PASSWORD=your-app-password-here
MAIL_TITLE=mail-title
```

**注意**: `.env`ファイルは`.gitignore`に追加して、Gitにコミットしないようにしてください。

### 方法2: システム環境変数として設定

ターミナルで以下のコマンドを実行：

```bash
export GOOGLE_API_KEY="your-google-api-key-here"
export CHANNEL_URLS="https://www.youtube.com/@CNN, https://www.youtube.com/@BBC"
export EMAIL_ADDRESSES="sample1@gmail.com, sample2@gmail.com"
export GMAIL_ADDRESS="your-email@gmail.com"
export GMAIL_PASSWORD="your-app-password-here"
export MAIL_TITLE="mail-title"
```

### 環境変数の説明

- `GOOGLE_API_KEY`: Google Gemini APIのキー（必須）
- `CHANNEL_URLS`: YouTubeチャンネルURL（カンマ区切り、必須）
- `EMAIL_ADDRESSES`: 送信先メールアドレス（カンマ区切り、必須）
- `GMAIL_ADDRESS`: 送信元Gmailアドレス（必須）
- `GMAIL_PASSWORD`: Gmailアプリケーションパスワード（必須）
- `MAIL_TITLE`: メールのタイトルに使用する文字列（オプション）

## セットアップ

### 1. 仮想環境の作成

シェルスクリプトを使用してPython 3.12の仮想環境を作成します：

```bash
./make-venv.sh
```

スクリプト実行後、表示されたコマンドで仮想環境を有効化してください：

```bash
source venv/bin/activate
```

仮想環境が有効化されると、プロンプトに `(venv)` が表示されます。

**手動で作成する場合：**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. ffmpegのインストール

本システムは音声ファイルをMP3形式に変換するためにffmpegを使用します。以下のコマンドでインストールしてください：

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Linux (apt):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Linux (yum):**
```bash
sudo yum install ffmpeg
```

**Windows:**
[ffmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロードしてインストールするか、[chocolatey](https://chocolatey.org/)を使用：
```bash
choco install ffmpeg
```

### 4. Playwrightブラウザのインストール

本システムはPlaywrightを使用してYouTubeチャンネル情報を取得します。初回実行前に、以下のコマンドでPlaywrightのブラウザをインストールしてください：

```bash
playwright install
```

または、Chromiumのみをインストールする場合：

```bash
playwright install chromium
```

**注意**: 初回インストール時やPlaywrightを更新した後は、必ずこのコマンドを実行してください。ブラウザがインストールされていないと、実行時にエラーが発生します。

## 処理の流れ
1. **YouTube動画の取得**<br>`yt_dlp`を使用して、指定URLの動画をMP3形式でダウンロード
2. **音声文字起こし・翻訳・要約**<br>`Google Gemini 2.0 Flash`により、音声を文字起こしし、日本語または英語に翻訳、さらに要約文を生成
3. **Gmailで要約を送信**<br>生成した要約を、`Gmail API`を通じて指定アドレス宛に自動送信

## Gmailアプリケーションパスワードの取得方法（OAuth未使用の場合）
※この方法は、2段階認証が有効なGoogleアカウントでのみ使用できます。

Gmail経由でメール送信を行うためには、「アプリパスワード」が必要です。以下の手順で取得してください。

### 1. Googleアカウントにログイン
- https://myaccount.google.com にアクセスし、Gmailを使用しているGoogleアカウントにログインします。

### 2. 2段階認証を有効化（未設定の場合）
- 左のメニューから「セキュリティ」を選択
- 「2段階認証プロセス」に進み、手順に従って設定

### 3. アプリパスワードの発行
- 再び「セキュリティ」ページに戻り、「アプリパスワード」をクリック
※このリンクは以下でもアクセス可能です：https://myaccount.google.com/apppasswords
- ログインを求められた場合は再度ログイン
- 「アプリを選択」 → メール を選択
- 「デバイスを選択」 → その他（名前を入力） を選び、例: YouTubeSummaryApp と入力
- 「生成」をクリックすると、16桁のアプリパスワードが表示されます

### アプリパスワードの利用
取得したパスワードは、`.env`ファイルに`GMAIL_PASSWORD`として設定してください：

```env
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_PASSWORD=16-digit application password
```

または、環境変数として設定：
```bash
export GMAIL_ADDRESS="your_email@gmail.com"
export GMAIL_PASSWORD="16-digit application password"
```

## 実行タイミング
GCPインスタンス上で 日次定期実行（Cloud Scheduler + Cloud Functions）

## 利用ケース
- 長時間の動画を手早く把握したいビジネスユーザー
- 語学学習目的での字幕・翻訳支援
- ニュース・教育系動画の要点収集