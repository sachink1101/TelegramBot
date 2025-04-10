import time
import requests
import asyncio
from telegram import Bot
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 🔐 API & Telegram Credentials
TELEGRAM_TOKEN = "7855031635:AAG7CBHRCrwjGwuut47Y6fDLooHNjlX-980"

# Telegram Channels
CHAT_IDS = [
    "@tradelikeberlinalpha",
    "@tradin_capital"
]

# Binance API Endpoint
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Telegram Bot Setup
bot = Bot(token=TELEGRAM_TOKEN)

# Session with Retry Logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Fetch Binance Data
def get_binance_data(symbol="BTCUSDT", interval="15m", limit=30):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = session.get(BINANCE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        formatted_data = [
            {
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4])
            } for candle in data
        ]
        return formatted_data
    except Exception as e:
        raise Exception(f"{symbol} fetch failed: {str(e)}")

# Calculate MA and Price
def calculate_ma_and_price(data):
    closes = [candle["close"] for candle in data[-30:]]
    ma_30 = sum(closes) / len(closes)
    current_price = closes[-1]
    return ma_30, current_price

# Check if price is touching MA (with tighter precision)
def is_touching(price, ma, percent_threshold=0.2):
    threshold = ma * (percent_threshold / 100)
    return abs(price - ma) <= threshold

# Send Telegram Signal
async def send_telegram_signal(symbol, price, ma):
    symbol_label = "BTC/USDT" if symbol == "BTCUSDT" else "ETH/USDT"
    message = f"🚨 Signal: {symbol_label} price ({price:.2f}) touched 30 MA ({ma:.2f}) on 15-min TF.\n\nCheck chart for confirmation and execution plan."
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {message}")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

# Send Telegram Error (with cooldown)
async def send_telegram_error(message, last_error_time, error_cooldown=14400):
    current_time = time.time()
    if current_time - last_error_time >= error_cooldown:
        try:
            await bot.send_message(chat_id=CHAT_IDS[0], text=message)
            print(f"✅ Sent error to {CHAT_IDS[0]}: {message}")
        except Exception as telegram_error:
            print(f"❌ Telegram error for {CHAT_IDS[0]}: {str(telegram_error)}")
        return current_time
    return last_error_time

# Main Async Loop
async def main():
    print("📱 TradeLikeBerlin Alpha Bot started with Binance 15m data...")
    last_error_time = 0
    signal_cooldown = 900  # 15 minutes
    last_signal_time = {"BTCUSDT": 0, "ETHUSDT": 0}
    last_alerted_candle = {"BTCUSDT": None, "ETHUSDT": None}
    symbols = ["BTCUSDT", "ETHUSDT"]

    while True:
        try:
            current_time = time.time()
            signal_sent = False

            for symbol in symbols:
                if current_time - last_signal_time[symbol] < signal_cooldown:
                    continue  # Still in cooldown for this symbol

                data = get_binance_data(symbol=symbol)
                ma_30, current_price = calculate_ma_and_price(data)
                latest_candle_timestamp = data[-1]["timestamp"]

                if is_touching(current_price, ma_30, percent_threshold=0.2):
                    if latest_candle_timestamp != last_alerted_candle[symbol]:
                        print(f"📈 {symbol} touched: Price {current_price:.2f}, MA {ma_30:.2f}")
                        await send_telegram_signal(symbol, current_price, ma_30)
                        last_alerted_candle[symbol] = latest_candle_timestamp
                        last_signal_time[symbol] = current_time
                        signal_sent = True

            if not signal_sent:
                print("🔍 No signal this cycle. Sleeping 15s...")

            await asyncio.sleep(15)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            last_error_time = await send_telegram_error(error_msg, last_error_time)
            print(error_msg)
            await asyncio.sleep(60)

# Run the Bot
if __name__ == "__main__":
    asyncio.run(main())
