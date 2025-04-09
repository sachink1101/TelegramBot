import time
import requests
import asyncio
from telegram import Bot
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 🔐 Hardcoded credentials (replace if needed)
API_KEY = "v0MrX39nDUV0rqs5UJXsTf7cAHzaJ1"
API_SECRET = "SVgMt4S8f3XItZImxypCCXwOxAT577gVhnjGiEyRNNN4jNKbEkhianCQfrCy"
TELEGRAM_TOKEN = "7855031635:AAG7CBHRCrwjGwuut47Y6fDLooHNjlX-980"

# Telegram channel IDs
CHAT_IDS = [
    "@tradelikeberlinalpha",
    "@tradin_capital"
]

# Binance API endpoint for 15m candles
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Setup Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

# Requests session with retry logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Fetch Binance 15m candle data
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
        raise Exception(f"Binance fetch failed: {str(e)}")

# Calculate 30-period moving average and current price
def calculate_ma_and_price(data):
    closes = [candle["close"] for candle in data[-30:]]
    ma_30 = sum(closes) / len(closes)
    current_price = closes[-1]
    return ma_30, current_price

# Check if current price is within threshold of the MA
def is_touching(price, ma, threshold=10.0):
    return abs(price - ma) <= threshold

# Send signal to Telegram channels
async def send_telegram_signal(price, ma):
    message = f"🚨 Signal: BTC/USD price ({price:.2f}) touched 30 MA ({ma:.2f}) in (15-min TF)\n\nHave a look and plan an execution"
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {message}")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

# Send error message to Telegram (only once per cooldown)
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

# Main async loop
async def main():
    print("📱 TradeLikeBerlin Alpha Bot started with Binance 15m data...")
    last_error_time = 0
    error_cooldown = 14400  # 4 hours
    last_signal_time = 0
    signal_cooldown = 900  # 15 minutes
    last_alerted_candle = None

    while True:
        try:
            data = get_binance_data()
            ma_30, current_price = calculate_ma_and_price(data)
            current_time = time.time()
            latest_candle_timestamp = data[-1]["timestamp"]

            if is_touching(current_price, ma_30):
                # Only send if this candle wasn't alerted before AND cooldown passed
                if (latest_candle_timestamp != last_alerted_candle and
                        current_time - last_signal_time >= signal_cooldown):
                    print(f"Touch detected: Price {current_price:.2f}, 30 MA {ma_30:.2f}")
                    await send_telegram_signal(current_price, ma_30)
                    last_signal_time = current_time
                    last_alerted_candle = latest_candle_timestamp
                else:
                    print("⏳ Touch condition met but already alerted for this candle or still cooling down.")

            await asyncio.sleep(15)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            last_error_time = await send_telegram_error(error_msg, last_error_time, error_cooldown)
            print(error_msg)
            await asyncio.sleep(60)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
