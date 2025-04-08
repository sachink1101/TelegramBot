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
    "@tradelikeberlinalpha",  # Replace with your actual channels
    "@tradin_capital"
]

# Coinbase API endpoint
COINBASE_API_URL = "https://api.coinbase.com/v2/prices/BTC-USD/historic"

# Setup Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

# Requests session with retry logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Fetch Coinbase price data (approximated as OHLC from spot data)
def get_coinbase_data(limit=30):
    params = {"period": "hour"}
    try:
        response = session.get(COINBASE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()["data"]["prices"]
        formatted_data = [
            {"open": d["price"], "high": d["price"], "low": d["price"], "close": d["price"]}
            for d in data[:limit]
        ]
        return formatted_data[::-1]
    except Exception as e:
        raise Exception(f"Coinbase fetch failed: {str(e)}")

# Calculate 30-period moving average and current price
def calculate_ma_and_price(data):
    closes = [float(candle["close"]) for candle in data]
    ma_30 = sum(closes) / len(closes)
    current_price = float(data[-1]["close"])
    return ma_30, current_price

# Check if current price is within threshold of the MA
def is_touching(price, ma, threshold=10.0):
    return abs(price - ma) <= threshold

# Send signal to Telegram channels
async def send_telegram_signal(price, ma, source):
    message = f"🚨 Signal: BTC/USD price ({price:.2f}) touched 30 MA ({ma:.2f}) on {source} (15-min)"
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {message}")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

# Send error message to Telegram (with cooldown)
async def send_telegram_error(message, last_error_time, error_cooldown=14400):
    current_time = time.time()
    if current_time - last_error_time >= error_cooldown:
        for chat_id in CHAT_IDS:
            try:
                await bot.send_message(chat_id=chat_id, text=message)
                print(f"✅ Sent error to {chat_id}: {message}")
            except Exception as telegram_error:
                print(f"❌ Telegram error for {chat_id}: {str(telegram_error)}")
        return current_time
    return last_error_time

# Main async loop
async def main():
    print("📡 TradeLikeBerlin Alpha Bot started with Coinbase...")
    last_alert_time = 0
    last_error_time = 0
    alert_cooldown = 900      # 15 minutes
    error_cooldown = 14400    # 4 hours

    while True:
        try:
            data = get_coinbase_data()
            ma_30, current_price = calculate_ma_and_price(data)
            source = "Coinbase"

            current_time = time.time()
            if is_touching(current_price, ma_30) and (current_time - last_alert_time) >= alert_cooldown:
                print(f"Touch detected: Price {current_price:.2f}, 30 MA {ma_30:.2f} [Source: {source}]")
                await send_telegram_signal(current_price, ma_30, source)
                last_alert_time = current_time

            await asyncio.sleep(15)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            last_error_time = await send_telegram_error(error_msg, last_error_time, error_cooldown)
            print(error_msg)
            await asyncio.sleep(60)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
