import os
from dotenv import load_dotenv
load_dotenv()

from datetime import date, datetime
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# LINE Developers の環境変数から読み込み
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# トークンが設定されていなければ None
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

# .env または Render 環境変数から禁酒開始日を取得
START_DATE_STR = os.environ.get("START_DATE", "")

def get_start_date() -> date:
    """環境変数から開始日を取得。なければ今日を返す。"""
    if START_DATE_STR:
        try:
            return datetime.strptime(START_DATE_STR, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()

def count_days() -> int:
    """禁酒開始日からの日数をカウント"""
    return (date.today() - get_start_date()).days + 1

@app.route("/")
def home():
    """Render のルート確認用"""
    return "Kinsyu-bot is running!"

@app.get("/health")
def health():
    """Render のヘルスチェック用エンドポイント"""
    return "ok", 200

@app.post("/callback")
def callback():
    """LINE Messaging API からのWebhookを処理"""
    if handler is None:
        abort(500, "LINE credentials not set")
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ユーザーからのメッセージ受信イベント
@handler.add(MessageEvent, message=TextMessage)  # type: ignore
def on_message(event: MessageEvent):
    text = event.message.text.strip()

    if text.startswith("禁酒開始"):
        # 仕様：
        # 1. 入力形式は「禁酒開始 YYYYMMDD」
        # 2. スペース必須（例: 禁酒開始 20250901）
        # 3. 日付は8桁の数字（YYYYMMDD）、ハイフンなし
        parts = text.split()
        if len(parts) == 2 and len(parts[1]) == 8 and parts[1].isdigit():
            try:
                # parts[1] を日付に変換
                d = datetime.strptime(parts[1], "%Y%m%d").date()
                days = (date.today() - d).days + 1
                msg = f"開始日 {d:%Y-%m-%d} から {days}日目です。"
            except ValueError:
                # 不正な日付（例: 20251301）を弾く
                msg = "日付が正しくありません。例: 禁酒開始 20250901"
        else:
            # 入力形式が間違っている場合
            msg = "例: 禁酒開始 20250901"
    else:
        # 通常のメッセージ時は、環境変数からの日数を返す
        days = count_days()
        sd = get_start_date()
        msg = f"今日は禁酒{days}日目です！（開始日: {sd:%Y-%m-%d}）"

    # LINE に返信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))  # type: ignore

if __name__ == "__main__":
    # Render 環境では PORT 環境変数が自動で設定される
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
