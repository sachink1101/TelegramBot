import time
import requests
import asyncio
from telegram import Bot
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 🔐 Credentials
API_KEY = "v0MrX39nDUV0rqs5UJXsTf7cAHzaJ1"
API_SECRET = "SVgMt4S8f3XItZImxypCCXwOxAT577gVhnjGiEyRNNN4jNKbEkhianCQfrCy"
TELEGRAM_TOKEN = "7855031635:AAG7CBHRCrwjGwuut47Y6fDLooHNjlX-980"

# Telegram channel IDs
CHAT_IDS = [
    "@tradelikeberlinalpha",
    "@tradin_capital"
]

# Binance API URL
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Setup Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

# Requests session with retry logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Supported symbols
SYMBOLS = ["BTCUSDT", "ETHUSDT", "XAUUSD"]

# Get Binance data
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

def calculate_ma_and_price(data):
    closes = [candle["close"] for candle in data[-30:]]
    ma_30 = sum(closes) / len(closes)
    current_price = closes[-1]
    return ma_30, current_price

def is_touching(price, ma, threshold=10.0):
    return abs(price - ma) <= threshold

async def send_telegram_signal(symbol, price, ma):
    message = f"🚨 Signal: {symbol} price ({price:.2f}) touched 30 MA ({ma:.2f}) on 15m TF.\n\nHave a look and plan an execution."
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {message}")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

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

# Main loop
async def main():
    print("📈 TradeLikeBerlin Multi-Symbol Bot started with 15m data...")
    last_error_time = 0
    signal_cooldown = 900  # 15 minutes
    last_signal_times = {symbol: 0 for symbol in SYMBOLS}
    last_alerted_candle = {symbol: None for symbol in SYMBOLS}

    while True:
        for symbol in SYMBOLS:
            try:
                data = get_binance_data(symbol)
                ma_30, current_price = calculate_ma_and_price(data)
                current_time = time.time()
                latest_candle_timestamp = data[-1]["timestamp"]

                if is_touching(current_price, ma_30):
                    if (latest_candle_timestamp != last_alerted_candle[symbol] and
                            current_time - last_signal_times[symbol] >= signal_cooldown):
                        print(f"📍 {symbol} Touch: Price {current_price:.2f}, MA {ma_30:.2f}")
                        await send_telegram_signal(symbol, current_price, ma_30)
                        last_signal_times[symbol] = current_time
                        last_alerted_candle[symbol] = latest_candle_timestamp
                    else:
                        print(f"⏳ {symbol} met condition but already alerted or cooling down.")
                else:
                    print(f"🚫 {symbol} did not touch MA. Price: {current_price:.2f}, MA: {ma_30:.2f}")

            except Exception as e:
                error_msg = f"⚠️ Error for {symbol}: {str(e)}"
                last_error_time = await send_telegram_error(error_msg, last_error_time)
                print(error_msg)

        await asyncio.sleep(15)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
