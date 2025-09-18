# Flask: Python の軽量Webフレームワーク
from flask import Flask, request, abort
# LINE公式のBot SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
# 環境変数を扱うライブラリ
import os
from dotenv import load_dotenv
# 日付処理
from datetime import datetime, date

# .env ファイルを読み込み（APIキーなどを環境変数にする）
load_dotenv()

# 環境変数から LINE チャネルのアクセストークンとシークレットを取得
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# LINE Bot SDK にキーを渡して初期化
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)  # LINEからのイベントを処理するオブジェクト

# Flaskアプリを作成
app = Flask(__name__)

# 禁酒開始日を保存するテキストファイル名（グローバル変数のように使う）
FILENAME = "start_date.txt"

def save_start_date(d: date):
    """開始日をファイルに保存"""
    # "YYYY-MM-DD" 形式でファイルに書き込む
    with open(FILENAME, "w", encoding="utf-8") as f:
        f.write(d.strftime("%Y-%m-%d"))

def load_start_date() -> date | None:
    """保存された開始日を読み込む"""
    # ファイルが存在すれば読み込み
    if os.path.exists(FILENAME):
        with open(FILENAME, "r", encoding="utf-8") as f:
            try:
                # 読み込んだ文字列を日付型に変換
                return datetime.strptime(f.read().strip(), "%Y-%m-%d").date()
            except ValueError:
                # 形式が壊れていたら None を返す
                return None
    # ファイルがなければ None
    return None


# ユーザーからのメッセージを処理する部分
@handler.add(MessageEvent, message=TextMessage)  # type: ignore
def on_message(event: MessageEvent):
    # ユーザーが送ってきたメッセージのテキストを取得
    text = event.message.text.strip()

    # 「禁酒開始 YYYYMMDD」という形式で入力されたかを確認
    # 仕様：
    # 1. 入力形式は「禁酒開始 YYYYMMDD」
    # 2. スペース必須（例: 禁酒開始 20250901）
    # 3. 日付は8桁の数字（YYYYMMDD）、ハイフンなし
    if text.startswith("禁酒開始"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 8:
            try:
                # 日付文字列を date 型に変換
                start_date = datetime.strptime(parts[1], "%Y%m%d").date()
                # ファイルに保存
                save_start_date(start_date)
                reply = f"開始日 {start_date.strftime('%Y-%m-%d')} を保存しました。"
            except ValueError:
                reply = "日付の形式が正しくありません。例: 禁酒開始 20250901"
        else:
            reply = "例: 禁酒開始 20250901"
        # ユーザーに返信
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # それ以外のメッセージが来たとき → 禁酒日数を返す
    start_date = load_start_date()
    if start_date:
        today = date.today()
        # 今日の日付との差を計算、初日を1日目とする
        days = (today - start_date).days + 1
        reply = f"今日は禁酒{days}日目です！（開始日: {start_date.strftime('%Y-%m-%d')}）"
    else:
        reply = "開始日が設定されていません。「禁酒開始 YYYYMMDD」で登録してください。"

    # 結果をLINEに返信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


# LINEのWebhookエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    # LINEサーバーから送られてきた署名を取得
    signature = request.headers["X-Line-Signature"]

    # リクエストボディをテキストで取得
    body = request.get_data(as_text=True)

    try:
        # LINE SDK にリクエストを渡して処理
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名が違う場合は不正アクセスとみなす
        abort(400)

    return "OK"


# ローカルで動かす場合のエントリーポイント
if __name__ == "__main__":
    # RenderではPORTが自動設定されるので、環境変数から取得
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
