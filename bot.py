import asyncio
import time
import requests
import pandas as pd
from telegram import Bot

# --- CONFIG ---
BOT_TOKEN = "7855031635:AAG7CBHRCrwjGwuut47Y6fDLooHNjlX-980"
CHANNEL_ID = "@TradeLikeBerlinAlpha"
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
MA_PERIOD = 30
CHECK_INTERVAL = 900  # 15 minutes

bot = Bot(token=BOT_TOKEN)

def fetch_price_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={MA_PERIOD+1}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

async def check_signal():
    df = fetch_price_data()
    ma30 = df['close'].rolling(window=MA_PERIOD).mean().iloc[-1]
    current_price = df['close'].iloc[-1]

    if round(current_price, 2) == round(ma30, 2):
        message = (
            f"📈 BTC/USDT Signal: Price touched MA({MA_PERIOD})\n"
            f"Price: {current_price:.2f}\nMA{MA_PERIOD}: {ma30:.2f}"
        )
        await bot.send_message(chat_id=CHANNEL_ID, text=message)
        print("✅ Signal sent!")
    else:
        print(f"No signal | Price: {current_price:.2f} | MA: {ma30:.2f}")

async def main_loop():
    print("📡 TradeLikeBerlin Alpha Bot started...")
    while True:
        try:
            await check_signal()
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main_loop())
