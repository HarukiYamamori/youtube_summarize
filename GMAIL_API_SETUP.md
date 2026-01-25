# Gmail API設定ガイド

本システムはGmail APIを使用してメールを送信し、ジャンルに応じたラベルを自動付与します。以下の手順で設定してください。

## 前提条件

- Googleアカウントを持っていること
- Google Cloud Platform（GCP）のアカウントを持っていること（無料枠で利用可能）

## セットアップ手順

### 1. Google Cloud Consoleにアクセス

1. https://console.cloud.google.com/ にアクセス
2. Googleアカウントでログイン

### 2. プロジェクトの作成（未作成の場合）

1. 画面上部のプロジェクト選択ドロップダウンをクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を入力（例: `youtube-summarize`）
4. 「作成」をクリック
5. 作成したプロジェクトを選択

### 3. Gmail APIを有効化

1. 左メニューから「APIとサービス」→「ライブラリ」を選択
2. 検索ボックスに「Gmail API」と入力
3. 「Gmail API」を選択
4. 「有効にする」をクリック

### 4. OAuth同意画面の設定

1. 左メニューから「APIとサービス」→「OAuth同意画面」を選択
2. ユーザータイプを選択：
   - **個人利用のみ**: 「外部」を選択
   - **組織内のみ**: 「内部」を選択（Google Workspaceアカウントが必要）
3. 「作成」をクリック
4. **アプリ情報**を入力：
   - アプリ名: `YouTube Summary`（任意）
   - ユーザーサポートメール: 自分のメールアドレス
   - デベロッパーの連絡先情報: 自分のメールアドレス
5. 「保存して次へ」をクリック
6. **スコープ設定**：
   - 「スコープを追加または削除」をクリック
   - 以下のスコープを追加：
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.modify`
   - 「更新」をクリック
   - 「保存して次へ」をクリック
7. **テストユーザー**（外部アプリの場合）：
   - 「+ ADD USERS」をクリック
   - 自分のGmailアドレスを追加
   - 「保存して次へ」をクリック
8. 概要を確認して「ダッシュボードに戻る」をクリック

### 5. OAuth 2.0認証情報の作成

1. 左メニューから「APIとサービス」→「認証情報」を選択
2. 上部の「+ 認証情報を作成」→「OAuth クライアント ID」を選択
3. **アプリケーションの種類**: 「デスクトップアプリ」を選択
4. **名前**: `YouTube Summary Client`（任意）
5. 「作成」をクリック
6. 認証情報が表示されたら、「JSONをダウンロード」をクリック
7. ダウンロードしたファイルを`credentials.json`にリネーム
8. プロジェクトのルートディレクトリ（`main.py`と同じ場所）に配置

```
youtube_summarize/
├── credentials.json  ← ここに配置
├── main.py
├── gmail_sender.py
└── ...
```

### 6. ファイルの保護

`credentials.json`と`token.pickle`（後で自動生成されます）をGitにコミットしないよう、`.gitignore`に追加してください：

```gitignore
credentials.json
token.pickle
```

## 初回認証

1. システムを初回実行すると、ブラウザが自動的に開きます
2. Googleアカウントでログイン（テストユーザーとして追加したGmailアドレスでログインしてください）
3. 権限を確認して「許可」をクリック
4. 認証が完了すると、`token.pickle`が自動生成されます
5. 次回以降は自動で認証されます（トークンの有効期限内）

## 注意事項

- **`GMAIL_PASSWORD`環境変数は不要**: Gmail APIを使用する場合は、OAuth 2.0認証を使用するため、アプリケーションパスワードは不要です
- **テストユーザーの制限**: 外部アプリの場合、テストユーザーとして追加したアカウントのみが使用できます。本番環境で使用する場合は、OAuth同意画面を公開する必要があります
- **トークンの有効期限**: `token.pickle`のトークンが期限切れになった場合は、再度認証が必要になります
- **セキュリティ**: `credentials.json`と`token.pickle`は機密情報です。絶対にGitにコミットしないでください

## トラブルシューティング

### 認証エラーが発生する場合

- テストユーザーとして自分のGmailアドレスが追加されているか確認
- OAuth同意画面の設定が完了しているか確認
- `credentials.json`が正しい場所に配置されているか確認

### ラベルが付与されない場合

- Gmail APIが有効化されているか確認
- `gmail.modify`スコープが追加されているか確認
- ログを確認してエラーメッセージを確認

## 参考リンク

- [Gmail API ドキュメント](https://developers.google.com/gmail/api)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)

