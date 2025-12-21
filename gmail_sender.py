import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging import getLogger, basicConfig, INFO
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


def send_email(receiver_address, channel_name, body, is_html=True):
    # 環境変数から取得、なければデフォルト値を使用
    sender_email = os.getenv('GMAIL_ADDRESS', "")
    password = os.getenv('GMAIL_PASSWORD', "")  # 環境変数から取得

    subject = f"【YouTube Summary】{channel_name}"

    # メールのヘッダー部分を作成
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_address
    message["Subject"] = subject

    # HTMLとプレーンテキストの両方をメールに追加
    if is_html:
        # HTML形式のメール
        message.attach(MIMEText(body, "html"))
    else:
        # プレーンテキスト形式のメール
        message.attach(MIMEText(body, "plain"))

    try:
        # GmailのSMTPサーバーに接続
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # TLS接続を開始
        server.login(sender_email, password)  # ログイン
        text = message.as_string()  # メールを文字列に変換
        server.sendmail(sender_email, receiver_address, text)  # メールを送信
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        server.quit()  # サーバーから切断


if __name__ == "__main__":
    html_content = """<html><body><h1>Hello!</h1><p>This is an <b>HTML</b> email.</p></body></html>"""
    plain_text_content = "Hello!\nThis is a plain text email."

    # HTMLメールとして送信
    send_email(html_content, is_html=True)

    # プレーンテキストメールとして送信
    send_email(plain_text_content, is_html=False)
