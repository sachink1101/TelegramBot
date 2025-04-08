import requests
import time
from telegram import Bot
import asyncio
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Telegram Bot Token and Channel Chat IDs
TELEGRAM_TOKEN = "7855031635:AAG7CBHRCrwjGwuut47Y6fDLooHNjlX-980"  # @tradeberlinbot
CHAT_IDS = [
    "@tradelikeberlinalpha",  # REPLACE with actual Chat ID for @tradelikeberlinalpha
    "@tradin_capital"   # REPLACE with actual Chat ID for @tradin_capital
]

# API Endpoint (Coinbase only)
COINBASE_API_URL = "https://api.coinbase.com/v2/prices/BTC-USD/historic"

# Initialize Telegram Bot
bot = Bot(TELEGRAM_TOKEN)

# Setup requests session with retries
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Function to fetch Coinbase OHLC data
def get_coinbase_data(step=900, limit=30):
    params = {"period": "hour"}  # Coinbase uses hourly data; we'll approximate 15-min intervals
    try:
        response = session.get(COINBASE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()["data"]["prices"]
        # Approximate OHLC from spot prices, take last 30 entries
        formatted_data = [{"open": d["price"], "high": d["price"], "low": d["price"], "close": d["price"]} for d in data[:limit]]
        return formatted_data[::-1]  # Reverse to chronological order
    except Exception as e:
        raise Exception(f"Coinbase fetch failed: {str(e)}")

# Function to calculate 30 MA and current price
def calculate_ma_and_price(data):
    closes = [float(candle["close"]) for candle in data]
    ma_30 = sum(closes) / len(closes)
    current_price = float(data[-1]["close"])
    return ma_30, current_price

# Function to check if price touches MA
def is_touching(price, ma, threshold=10.0):  # 10 USD threshold for testing
    return abs(price - ma) <= threshold

# Async function to send Telegram signal to multiple channels
async def send_telegram_signal(price, ma, source):
    message = f"🚨 Signal: BTC/USD price ({price:.2f}) touched 30 MA ({ma:.2f}) on {source} (15-min)"
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {message}")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

# Async function to send Telegram error (with cooldown)
async def send_telegram_error(message, last_error_time, error_cooldown=14400):  # 4-hour cooldown
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

# Main loop
async def main():
    print("📡 TradeLikeBerlin Alpha Bot started with Coinbase...")
    last_alert_time = 0
    last_error_time = 0
    alert_cooldown = 900  # 15 minutes for signals
    error_cooldown = 14400  # 4 hours for errors

    while True:
        try:
            # Fetch data from Coinbase
            data = get_coinbase_data(step=900, limit=30)
            source = "Coinbase"

            # Calculate MA and price
            ma_30, current_price = calculate_ma_and_price(data)

            # Check for touch and send signal
            current_time = time.time()
            if is_touching(current_price, ma_30) and (current_time - last_alert_time) >= alert_cooldown:
                print(f"Touch detected: Price {current_price:.2f}, 30 MA {ma_30:.2f} [Source: {source}]")
                await send_telegram_signal(current_price, ma_30, source)
                last_alert_time = current_time

            # Wait before next check
            time.sleep(15)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            last_error_time = await send_telegram_error(error_msg, last_error_time, error_cooldown)
            print(error_msg)
            time.sleep(60)  # Wait longer on error

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())