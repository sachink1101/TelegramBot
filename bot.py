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

# API Endpoint (Binance)
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Initialize Telegram Bot
bot = Bot(TELEGRAM_TOKEN)

# Setup requests session with retries
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[502, 503, 504, 429])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Function to fetch Binance OHLC data
def get_binance_data(step=900, limit=30):
    params = {"symbol": "BTCUSDT", "interval": "15m", "limit": limit}
    try:
        response = session.get(BINANCE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        formatted_data = [{"open": d[1], "high": d[2], "low": d[3], "close": d[4]} for d in data]
        return formatted_data
    except Exception as e:
        raise Exception(f"Binance fetch failed: {str(e)}")

# Function to calculate 30 MA and current price
def calculate_ma_and_price(data):
    closes = [float(candle["close"]) for candle in data]
    ma_30 = sum(closes) / len(closes)
    current_price = float(data[-1]["close"])
    return ma_30, current_price

# Function to check if price touches MA
def is_touching(price, ma, threshold=10.0):  # Increased to 10 USD for testing
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

# Main loop
async def main():
    print("📡 TradeLikeBerlin Alpha Bot started with Binance...")
    last_alert_time = 0
    alert_cooldown = 900  # 15 minutes in seconds

    while True:
        try:
            # Fetch data from Binance
            data = get_binance_data(step=900, limit=30)
            source = "Binance"

            # Calculate MA and price
            ma_30, current_price = calculate_ma_and_price(data)

            # Check for touch and send signal
            current_time = time.time()
            if is_touching(current_price, ma_30) and (current_time - last_alert_time) >= alert_cooldown:
                print(f"Touch detected: Price {current_price:.2f}, 30 MA {ma_30:.2f}")
                await send_telegram_signal(current_price, ma_30, source)
                last_alert_time = current_time

            # Wait before next check
            time.sleep(15)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            for chat_id in CHAT_IDS:
                try:
                    await bot.send_message(chat_id=chat_id, text=error_msg)
                    print(f"✅ Sent error to {chat_id}: {error_msg}")
                except Exception as telegram_error:
                    print(f"❌ Telegram error for {chat_id}: {str(telegram_error)}")
            print(error_msg)
            time.sleep(60)  # Wait longer on error

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())