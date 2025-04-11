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
        response = session.get(BINANCE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise ValueError("Empty data received from Binance")
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
    if len(closes) < 30:
        raise ValueError("Insufficient data for MA calculation")
    ma_30 = sum(closes) / len(closes)
    current_price = closes[-1]
    return ma_30, current_price

# Check if price is touching MA
def is_touching(price, ma, percent_threshold=0.15):
    threshold = ma * (percent_threshold / 100)
    return abs(price - ma) <= threshold

# Format timestamp for readable message
def format_timestamp(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp / 1000))

# Send Telegram Signal
async def send_telegram_signal(symbol, price, ma, timestamp):
    symbol_label = "BTC/USDT" if symbol == "BTCUSDT" else "ETH/USDT"
    formatted_time = format_timestamp(timestamp)
    message = (
        f"🚨 {symbol_label} Signal\n"
        f"Price: {price:.2f} touched 30 MA: {ma:.2f}\n"
        f"Time: {formatted_time} (15m TF)\n"
        f"⚠️ Confirm on chart before trading!"
    )
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent to {chat_id}: {symbol_label} signal")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {str(e)}")

# Send Telegram Error (with cooldown)
async def send_telegram_error(message, last_error_time, error_cooldown=14400):
    current_time = time.time()
    if current_time - last_error_time >= error_cooldown:
        try:
            await bot.send_message(chat_id=CHAT_IDS[0], text=f"⚠️ Bot Error: {message}")
            print(f"✅ Sent error to {CHAT_IDS[0]}")
            return current_time
        except Exception as e:
            print(f"❌ Telegram error for {CHAT_IDS[0]}: {str(e)}")
    return last_error_time

# Align checks with candle close
def is_new_candle(timestamp, interval_seconds=900):
    current_time = int(time.time() * 1000)
    candle_start = (current_time // (interval_seconds * 1000)) * (interval_seconds * 1000)
    return timestamp >= candle_start

# Main Async Loop
async def main():
    print("📈 TradeLikeBerlin Alpha Bot v2.0 Started (15m TF)...")
    last_error_time = 0
    symbols = ["BTCUSDT", "ETHUSDT"]
    last_alerted_candle = {symbol: None for symbol in symbols}  # Track last alerted candle
    candle_interval = 900  # 15 minutes in seconds

    while True:
        try:
            for symbol in symbols:
                # Fetch data
                data = get_binance_data(symbol=symbol, interval="15m", limit=30)
                latest_candle = data[-1]
                latest_timestamp = latest_candle["timestamp"]

                # Only process if it's a new candle
                if last_alerted_candle[symbol] == latest_timestamp:
                    continue  # Skip if this candle was already alerted

                # Calculate MA and price
                ma_30, current_price = calculate_ma_and_price(data)

                # Check if price touches MA
                if is_touching(current_price, ma_30):
                    print(f"📊 {symbol} Touch Detected | Price: {current_price:.2f} | MA: {ma_30:.2f} | Time: {format_timestamp(latest_timestamp)}")
                    await send_telegram_signal(symbol, current_price, ma_30, latest_timestamp)
                    last_alerted_candle[symbol] = latest_timestamp
                else:
                    print(f"🔍 {symbol} No Touch | Price: {current_price:.2f} | MA: {ma_30:.2f}")

            # Sleep until next candle (~15m)
            await asyncio.sleep(candle_interval - (time.time() % candle_interval) + 5)

        except Exception as e:
            error_msg = f"Error in main loop: {str(e)}"
            print(f"❌ {error_msg}")
            last_error_time = await send_telegram_error(error_msg, last_error_time)
            await asyncio.sleep(60)  # Wait before retrying after error

# Run the Bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")