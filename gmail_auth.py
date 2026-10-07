"""Gmail APIのOAuth認証を行い、token.pickleを作成・更新する

ブラウザが開ける環境で手動で実行する: python gmail_auth.py
"""
import pickle
from logging import getLogger, basicConfig, INFO

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from gmail_sender import CREDENTIALS_PATH, SCOPES, TOKEN_PATH

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


if __name__ == "__main__":
    # 既存のトークンは使わず、ブラウザで認証し直す（成功した場合だけ上書き保存）
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()

    with open(TOKEN_PATH, 'wb') as token:
        pickle.dump(creds, token)

    logger.info(f"認証が完了しました: {profile.get('emailAddress')}（{TOKEN_PATH}を保存しました）")
