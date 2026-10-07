import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import pickle
import base64
from logging import getLogger, basicConfig, INFO
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']
TOKEN_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'


class GmailAuthError(Exception):
    """Gmail APIの認証が必要（トークンが無い・更新できない）"""


def get_gmail_service():
    """Gmail APIを使用してGmailサービスを取得

    トークンが無い・更新できない場合は、ブラウザを開かずにGmailAuthErrorを送出する。
    （ヘッドレス環境で認証画面の待ち状態のまま止まらないようにするため。再認証は gmail_auth.py で行う）
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds:
        raise GmailAuthError(f"{TOKEN_PATH}がありません。`python gmail_auth.py`で認証してください")

    if not creds.valid:
        if not (creds.expired and creds.refresh_token):
            raise GmailAuthError(f"{TOKEN_PATH}が無効です。`python gmail_auth.py`で再認証してください")
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise GmailAuthError(f"トークンを更新できません。`python gmail_auth.py`で再認証してください: {e}") from e

        with open(TOKEN_PATH, 'wb') as token:
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


if __name__ == "__main__":
    send_email(
        "yamaharu0205@gmail.com", 
        "【2ch有益スレ】綺麗事は言わない！具体的なモテ方教える【ゆっくり解説】#2ch #面白いスレ #2ch有益スレ", '<h1><a href="https://www.youtube.com/watch?v=O0i_7_s0cnI&t=388s">【2ch有益スレ】綺麗事は言わない！具体的なモテ方教える【ゆっくり解説】#2ch #面白いスレ #2ch有益スレ</a></h1><div class="summary"><p>この動画では、ガチでモテたい人向けに、根本的な「女と話す意欲」の向上から、具体的な見た目の改善、コミュニケーション術、アプローチ方法まで、多岐にわたる恋愛戦略が解説されています。小手先のテクニックではなく、土台となる内面と外面の強化が重要であると強調されています。</p><h2>モテるための土台：女と話す意欲の向上</h2><p>モテない人の多くは、そもそも女性と話す根本的な意欲に欠けています。この意欲、すなわち「テストステロン」を高めることが最優先であると述べられています。</p><h3>テストステロンを高める方法</h3><ul><li><b>亜鉛とエビオス（適量）</b>：摂取することでテストステロンが向上し、女性と話す意欲が湧きやすくなります。亜鉛は特に優先すべきで、適度な摂取量の増加も効果的とされます。（過剰摂取は注意）</li><li><b>オナ禁</b>：一般的なオナ禁効果よりも「女性と関わる意欲」を高めるものとして捉え、推奨されています。長期すぎるオナ禁は逆効果となるため、2週間に1度程度が目安。エロ禁は高難易度だが、より効果的。</li><li><b>その他</b>：刃物いじり（アメリカの銃研究を引用）、ウェイトトレーニング、FPSやレースゲームなどもテストステロン向上に寄与しますが、効果は亜鉛やオナ禁に比べ限定的です。</li></ul><h2>見た目の改善</h2><h3>体型の改善</h3><ul><li><b>脂肪の排除</b>：特に顔の脂肪はモテに大きなマイナス。「凡人のデブ」は価値がないとまで断言されており、真っ先に痩せるべきです。</li><li><b>目指すは細マッチョ</b>：ただ痩せるだけでなく、引き締まった体を目指します。</li><li><b>具体的な運動</b>：食事量を減らしつつ、栄養バランスを保ち、運動を取り入れます。水泳が最適ですが、自転車や軽めのウェイトトレーニングも効果的。上半身のスクワットとも言える「懸垂」は、背筋を伸ばし逆三角形の体型を作るのに非常に有効です。</li></ul><h3>顔の改善</h3><ul><li><b>肌の清潔感</b>：ニキビのない綺麗な肌を目指すことが重要。</li><li><b>鼻筋の形成</b>：鼻筋がないとブサイクに見えがちですが、整形なしで「金槌で鼻筋を叩く」ことで、わずかながら鼻筋を作る効果があると提唱されています。100均の小さい金槌で、顔を斜め上にし、金槌の重さに任せて鼻先から上の硬い部分（鼻筋）を軽く叩きます。ただし、団子鼻の改善には不向きです。</li><li><b>目元のケア</b>：クマ対策として十分な睡眠を推奨。目の疲れがひどい場合は、濡らしたタオルを温めて目に当てるのが効果的。</li><li><b>眉毛・髪型</b>：個人差が大きいため、雑誌などで研究し、自分に似合うスタイルを見つけることが勧められています。</li></ul><h2>コミュニケーション術</h2><h3>心構え</h3><ul><li><b>積極性と押しの強さ</b>：受け身ではなく、自分から積極的にアプローチする姿勢が非常に重要。失敗しても人生が終わるわけではないという気概を持つこと。</li><li><b>モチベーション維持</b>：他の男に奪われる状況を想像することで、嫉妬心を糧に行動意欲を高めることができます。</li></ul><h3>会話のコツ</h3><ul><li><b>質問を投げかける</b>：相手のことを知ろうとする姿勢で、積極的に質問します。特に「食」に関する話題は男女共通で滑りにくいとされます。政治経済のような重い話題は避けるべきです。</li><li><b>自己開示と返報性</b>：質問だけでなく、適度に自分の話も挟むことで、相手からの質問を引き出し、会話を継続させます。</li><li><b>楽しい雑談を心がける</b>：高度なギャグセンスなどは不要で、楽しい雑談ができれば十分。</li></ul><h3>態度と表情</h3><ul><li><b>はっきりとした声と視線</b>：ボソボソと喋ったり、相手の顔を見ずに話したりするのはNG。口をしっかり開けて、ハッキリ聞き取れる声で話します。</li><li><b>適切な視線</b>：相手の顔を見つめすぎるのは避けつつ、目を見て話すことが基本。恥ずかしい場合は口や鼻を見ることから始めたり、相手の目の二重を探すように見る（筆者談）という方法も。</li><li><b>表情トレーニング</b>：目一杯の笑顔、目の見開き、舌を上下の歯茎と唇の間で左右に動かす（顎の引き締め）、変顔などを行い、表情筋を鍛えることが推奨されています。</li></ul><h2>アプローチとデート</h2><ul><li><b>焦らないアプローチ</b>：いきなりの告白は悪手。まずは軽い会話ができる仲から始め、徐々に距離を縮めます。</li><li><b>最初の誘い方</b>：「一緒に飯を食べに行こう」が適切。心理テクニックとして、最初に無理難題を突きつけて断らせてから本命の頼みを出すと、OKをもらいやすいとされます。</li><li><b>断られても諦めない</b>：一度や二度断られても諦めず、数回誘うことが大切。</li><li><b>会計は奢る</b>：最初の食事では、無理をしてでも奢るのが望ましい。相手が社会人なら「次は私が払います」と言わせることで、次回の口実が作れます。</li><li><b>相手の選別</b>：あまり乗り気でない相手には深追いせず、自分に興味のない人を切り捨てることも重要。愛想の良い子を選ぶと良いでしょう。</li><li><b>デートプラン</b>：駅で待ち合わせ、駅から少し離れた場所へ歩いて移動し食事、食後また駅まで歩いて解散、といったシンプルで無理のないプランが推奨されます。複数の店をリサーチしておくと、次回の誘いにも繋がります。</li><li><b>LINE/メール</b>：会話と同様、質問と適度な自己開示を意識。返信の催促や連投は厳禁。2～3日おきの頻度を目安に、相手の反応を見て調整します。絵文字を一つ入れることも勧められています。</li><li><b>告白のタイミング</b>：何度か食事やデートを重ねてから告白。振られてもすぐに諦めず、数回アタックすることも有効とされています。</li></ul></div>',
        label_name='生活情報'
    )