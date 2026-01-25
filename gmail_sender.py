import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import base64
from logging import getLogger, basicConfig, INFO
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']


def get_gmail_service():
    """Gmail APIを使用してGmailサービスを取得"""
    creds = None
    token_path = "token.pickle"

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def get_or_create_label(service, label_name):
    """ラベルを取得、なければ作成"""
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        label_obj = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created_label = service.users().labels().create(userId='me', body=label_obj).execute()
        return created_label['id']
    except Exception as e:
        logger.error(f"ラベルの取得/作成エラー: {e}")
        return None

def send_email(receiver_address, channel_name, body, is_html=True, label_name=None):
    """Gmail APIを使用してメールを送信し、ラベルを付与"""
    sender_email = os.getenv('GMAIL_ADDRESS', "")
    
    subject = f"【YouTube Summary】{channel_name}"
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_address
    message["Subject"] = subject
    
    if is_html:
        message.attach(MIMEText(body, "html"))
    else:
        message.attach(MIMEText(body, "plain"))
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        service = get_gmail_service()
        
        # まずメールを送信
        send_message = {'raw': raw_message}
        sent_message = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        message_id = sent_message['id']
        logger.info(f"Email sent successfully with message ID: {message_id}")

        logger.info(f"Label name: {label_name}")
        
        # ラベルを付与（送信後にmessages.modifyを使用）
        if label_name:
            label_id = get_or_create_label(service, label_name)
            if label_id:
                try:
                    service.users().messages().modify(
                        userId='me',
                        id=message_id,
                        body={'addLabelIds': [label_id]}
                    ).execute()
                    logger.info(f"Label '{label_name}' applied to the email")
                except Exception as e:
                    logger.error(f"ラベルの付与に失敗しました: {e}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
