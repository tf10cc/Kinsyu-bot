import os
from datetime import date, datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Flask アプリの玄関
app = Flask(__name__)

# LINE API 設定
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

# 開始日を保存するテキストファイル（グローバル変数代わり）
FILENAME = "start_date.txt"

# 開始日を保存
def save_start_date(d: date):
    with open(FILENAME, "w") as f:
        f.write(d.strftime("%Y%m%d"))

# 開始日を読み込み
def load_start_date() -> date:
    try:
        with open(FILENAME, "r") as f:
            return datetime.strptime(f.read().strip(), "%Y%m%d").date()
    except (FileNotFoundError, ValueError):
        return date.today()

# 日数を数える
def count_days() -> int:
    return (date.today() - load_start_date()).days + 1

@app.route("/")
def home():
    return "Kinsyu-bot is running!"

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

        if len(parts) == 2:
            try:
                d = datetime.strptime(parts[1], "%Y%m%d").date()
                save_start_date(d)  # ← ファイルに保存
                days = (date.today() - d).days + 1
                msg = f"開始日 {d:%Y-%m-%d} から {days}日目です。"
            except ValueError:
                msg = "日付は YYYYMMDD 形式で入力してください。例: 禁酒開始 20250916"
        else:
            msg = "例: 禁酒開始 20250916"
    else:
        days = count_days()
        sd = load_start_date()
        msg = f"今日は禁酒{days}日目です！（開始日: {sd:%Y-%m-%d}）"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))  # type: ignore

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
