from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os
import pandas as pd
import ta

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

def get_stock_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=3mo"
    res = requests.get(url).json()
    try:
        result = res['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        df = pd.DataFrame({'close': closes})
        return df, result
    except Exception:
        return None, None

def analyze_stock(symbol):
    df, meta = get_stock_data(symbol)
    if df is None:
        return "ไม่สามารถดึงข้อมูลหุ้นได้ กรุณาตรวจสอบสัญลักษณ์อีกครั้ง"

    df.dropna(inplace=True)
    current_price = df['close'].iloc[-1]
    rsi = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator().iloc[-1]

    price_change_pct = ((current_price - ema200) / ema200) * 100
    emoji = "🟢" if price_change_pct > 0 else "🔴"
    advice = "buy" if rsi < 30 else "sell" if rsi > 70 else "wait"

    info = f"""
ชื่อหุ้น : {symbol.upper()}
ราคาปัจจุบัน : {current_price:.2f}
RSI : {rsi:.2f}
EMA200 : {ema200:.2f} ({price_change_pct:.2f}%) {emoji}
คำแนะนำ : {advice.upper()}
**ผู้ลงทุนควรศึกษาข้อมูลให้รอบด้านก่อนตัดสินใจ**
"""
    return info

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    if text.lower().startswith("info:"):
        symbol = text.split(":")[1].strip()
        reply = analyze_stock(symbol)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="พิมพ์: info:AAPL"))

if __name__ == "__main__":
    app.run()