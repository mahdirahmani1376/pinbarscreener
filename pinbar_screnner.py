import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from telegram import Bot

# Alpha Vantage API Configuration
ALPHA_VANTAGE_API_KEY = 'SVYMAQZMSDLD794S'
SYMBOL = 'EUR/USD'
INTERVAL = '5min'

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = 'your_telegram_bot_token'
TELEGRAM_CHANNEL_ID = '@your_telegram_channel_id'


# Function to fetch EUR/USD candlestick data
def fetch_candlestick_data(symbol, interval, api_key):
    url = f'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol.split("/")[0]}&to_symbol={symbol.split("/")[1]}&interval={interval}&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data['Time Series FX (' + interval + ')']).T
    df.columns = ['open', 'high', 'low', 'close']
    df.index = pd.to_datetime(df.index)
    df = df.astype(float)
    return df


# Function to detect pinbar candles
def is_pinbar(candle):
    open_price, high, low, close = candle
    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low
    return body <= 0.3 * (high - low) and (upper_wick >= 2 * body or lower_wick >= 2 * body)


# Function to send message with candlestick chart to Telegram
def send_telegram_message(bot_token, channel_id, message, image):
    bot = Bot(token=bot_token)
    bot.send_message(chat_id=channel_id, text=message)
    bot.send_photo(chat_id=channel_id, photo=image)


# Main function
def main():
    # Fetch candlestick data
    df = fetch_candlestick_data(SYMBOL, INTERVAL, ALPHA_VANTAGE_API_KEY)

    # Check for pinbar in the latest candle
    latest_candle = df.iloc[-1]
    if is_pinbar(latest_candle):
        # Plot the candlestick chart
        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df['close'], label='Close Price')
        plt.fill_between(df.index, df['low'], df['high'], alpha=0.1)
        plt.title(f'{SYMBOL} 5min Candlestick Chart')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()

        # Save plot to image
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Send message to Telegram
        message = f'Pinbar detected on {SYMBOL} 5min timeframe at {df.index[-1]}'
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, message, buf)


# Run the main function
if __name__ == '__main__':
    main()
