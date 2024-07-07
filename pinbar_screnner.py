import yfinance as yf
import matplotlib.pyplot as plt
from io import BytesIO
import plotly.graph_objects as go
import requests
from dotenv import dotenv_values

# Yahoo Finance Configuration
symbols = [
    # 'EURUSD=X',
    # 'JPY=X',
    'GBPUSD=X'
]

config = dotenv_values(".env")
# Telegram Bot Configuration
interval = config.get('INTERVAL')
bot_token = config.get('TELEGRAM_BOT_TOKEN')
channel_id = config.get('TELEGRAM_CHANNEL_ID')


# Function to fetch EUR/USD candlestick data
def fetch_candlestick_data(symbol, interval):
    df = yf.download(tickers=symbol, interval=interval, period='1d')
    return df


def show_candle_stick_chart(dataframe):
    candlestick = go.Candlestick(
        x=dataframe.index,
        open=dataframe['Open'],
        high=dataframe['High'],
        low=dataframe['Low'],
        close=dataframe['Close']
    )

    fig = go.Figure(data=[candlestick])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")

    fig.show()


def save_candle_stick_chart(dataframe, path):
    candlestick = go.Candlestick(
        x=dataframe.index,
        open=dataframe['Open'],
        high=dataframe['High'],
        low=dataframe['Low'],
        close=dataframe['Close']
    )

    fig = go.Figure(data=[candlestick])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")

    # fig.write_image(f"charts/{name}.png")
    fig.write_image(path, width=1920, height=1080)


# Function to create a candlestick chart using Plotly
def create_candlestick_chart(df):
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )
    fig = go.Figure(data=[candlestick])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")
    return fig


# Function to detect pinbar candles
def is_pinbar(candle):
    open_price, high, low, close = candle
    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low
    return body <= 0.3 * (high - low) and (upper_wick >= 2 * body or lower_wick >= 2 * body)


def send_telegram_message(bot_token, channel_id, message, fig):
    # requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={channel_id}&text={message}")
    # Save the figure as an image
    buf = BytesIO()
    fig.write_image(buf, format='png', width=1920, height=1080)
    buf.seek(0)
    files = {'photo': buf}
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto?chat_id={channel_id}",
                  files=files)


# Main function
def main():
    for symbol in symbols:
        # Fetch candlestick data
        df = fetch_candlestick_data(symbol, interval)

        # Check for pinbar in the latest candle
        latest_candle = df.iloc[-1]
        # if is_pinbar(latest_candle):
        if True:
            # Create the candlestick chart
            fig = create_candlestick_chart(df)

            # Send message to Telegram
            message = f'Pinbar detected on {symbol} 5min timeframe at {df.index[-1]}'
            send_telegram_message(bot_token, channel_id, message, fig)


# Run the main function
if __name__ == '__main__':
    main()
