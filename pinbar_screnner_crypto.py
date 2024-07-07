import requests
from dotenv import dotenv_values
import time
import pandas as pd
import json
from datetime import datetime, timedelta
from tqdm.asyncio import tqdm
import aiohttp
import asyncio
from aiolimiter import AsyncLimiter
import hmac
from hashlib import sha256
import plotly.graph_objects as go
from io import BytesIO


count_of_strong_close_bars = 4

now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

config = dotenv_values(".env")
api_key = config.get('BINGX_API_KEY')
secret_key = config.get('BINGX_SECRET_KEY')
APIURL = "https://open-api.bingx.com"
timeStampFormat = '%Y-%m-%d %H:%M:%S'
MAX_CONCURRENT = 16
RATE_LIMIT_IN_SECOND = 16
limiter = AsyncLimiter(RATE_LIMIT_IN_SECOND, 1.0)
weekly_time_frame = "1w"
h4_time_frame = "4h"
h1_time_frame = "1h"
d1_time_frame = "1d"
m_15_time_frame = '15m'
time_frame = m_15_time_frame
interval = config.get('INTERVAL')
bot_token = config.get('TELEGRAM_BOT_TOKEN')
channel_id = config.get('TELEGRAM_CHANNEL_ID')

defaultCurrenCyParamsMap = {
    "symbol": "BTC-USDT",
    "interval": f"{time_frame}",
}

default_columns = [
    "candlestick_chart_open_time",
    "Open",
    "High",
    "Low",
    "Close",
    "adj_close",
    "candlestick_chart_close_time",
    "volume"
]

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
def send_request(method, path, urlpa, payload):
    url = "%s%s?%s&signature=%s" % (APIURL, path, urlpa, get_sign(secret_key, urlpa))
    # print(url)
    headers = {
        'X-BX-APIKEY': api_key,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.text


def get_all_currencies():
    payload = {}
    path = '/openApi/spot/v1/common/symbols'
    method = "GET"
    paramsMap = {
        "symbol": ""
    }
    paramsStr = prase_param(paramsMap)
    return send_request(method, path, paramsStr, payload)


def get_sign(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()
    # print("sign=" + signature)
    return signature


def convert_to_time_stamp(x):
    timeoftest = datetime.utcfromtimestamp(float(x / 1000))
    timeoftest = timeoftest + timedelta(minutes=(3 * 60) + 30)
    timeoftest = timeoftest.strftime(timeStampFormat)
    return timeoftest


def prase_param(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    return paramsStr + "&timestamp=" + str(int(time.time() * 1000))


async def main(df_all_currencies):
    payload = {}
    path = '/openApi/spot/v1/market/kline'
    method = "GET"
    headers = {
        'X-BX-APIKEY': api_key,
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for i in (df_all_currencies['symbol']):
            currency_params = {
                "symbol": f"{i}",
                "interval": f"{time_frame}",
                "startTime": start_time,
            }
            params_str = prase_param(currency_params)
            tasks.append(
                asyncio.ensure_future(send_async_request(session, path, params_str, currencyParams=currency_params)))

        results = []
        # results = await asyncio.gather(*tasks)
        for f in tqdm.as_completed(tasks, total=len(tasks)):
            results.append(await f)

        return results


async def send_async_request(session, path, urlpa, currencyParams):
    url = "%s%s?%s&signature=%s" % (APIURL, path, urlpa, get_sign(secret_key, urlpa))
    async with limiter:
        try:
            async with session.get(url) as response:
                text = await response.text()
                return get_currency_data_frame(text, currencyParams)
        except Exception as e:
            print(e)


def get_currency_data_frame(data, currencyParams):
    df = pd.DataFrame(json.loads(data)['data'])
    ##########################################normalizing data###########################################################
    df.columns = default_columns
    df['symbol'] = currencyParams['symbol']
    df['candlestick_chart_close_time'] = df['candlestick_chart_close_time'].apply(convert_to_time_stamp)
    df['candlestick_chart_open_time'] = df['candlestick_chart_open_time'].apply(convert_to_time_stamp)
    df['volume'] = df['volume'].apply(lambda x: x / 1000000)
    df = df.set_index('candlestick_chart_close_time').sort_index(ascending=True)
    df_final = df.iloc[1:4 ** 4 * 18]

    latest_candle = df_final.iloc[-1]

    # if is_pinbar(latest_candle):
    if True:
        # Create the candlestick chart
        fig = create_candlestick_chart(df_final)
        symbol = df_final["symbol"][0]
        # Send message to Telegram
        message = f'Pinbar detected on {symbol} 5min timeframe at {df.index[-1]}'
        send_telegram_message(bot_token, channel_id, message, fig)

    return df_final


###################################################################################################################

if __name__ == '__main__':
    dfAllCurrencies = pd.json_normalize(json.loads(get_all_currencies())['data']['symbols']).iloc[0:1]
    ScreenerDf = pd.DataFrame([], columns=default_columns, index=['candlestick_chart_close_time'])

    start_time = ""
    if time_frame == d1_time_frame:
        start_time = datetime.now() - timedelta(days=30)
    elif time_frame == h4_time_frame:
        start_time = datetime.now() - timedelta(days=14)
    elif time_frame == h1_time_frame:
        start_time = datetime.now() - timedelta(days=7)
    elif time_frame == m_15_time_frame:
        start_time = datetime.now() - timedelta(days=1)
    start_time = int(start_time.timestamp() * 1000)

    results = asyncio.run(main(dfAllCurrencies))
    # finalDf = pd.concat(results)


