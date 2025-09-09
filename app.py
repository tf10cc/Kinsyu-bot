import os
from datetime import date, datetime
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

START_DATE_STR = os.environ.get("START_DATE", "")

def get_start_date() -> date:
    if START_DATE_STR:
        try:
            return datetime.strptime(START_DATE_STR, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()

def count_days() -> int:
    return (date.today() - get_start_date()).days + 1

@app.get("/health")
def health():
    return "ok", 200

@app.post("/callback")
def callback():
    if handler is None:
        abort(500, "LINE credentials not set")
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)  # type: ignore
def on_message(event: MessageEvent):
    text = event.message.text.strip()

    if text.startswith("禁酒開始"):
        parts = text.split()
        if len(parts) == 2:
            try:
                d = datetime.strptime(parts[1], "%Y-%m-%d").date()
                days = (date.today() - d).days + 1
                msg = f"開始日 {d:%Y-%m-%d} から {days}日目です。"
            except ValueError:
                msg = "日付は YYYY-MM-DD で入力してください。例: 禁酒開始 2025-09-01"
        else:
            msg = "例: 禁酒開始 2025-09-01"
    else:
        days = count_days()
        sd = get_start_date()
        msg = f"今日は禁酒{days}日目です！（開始日: {sd:%Y-%m-%d}）"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))  # type: ignore

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))