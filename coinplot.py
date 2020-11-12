from bokeh.embed import components as plot_html
from bokeh.plotting import figure
from bokeh.models import WheelZoomTool
from bokeh.models.formatters import DatetimeTickFormatter
import bokeh.palettes
from flask import request
import functools
import pandas as pd
import requests
from time import time


candles = 150


def plot(currency='BTC_USDT', to_currency='USDT'):
    from_cur,in_cur = currency.split('_')
    symbol = currency.replace('_', '')
    interval = request.values.get('interval', '15m')
    log = request.values.get('log', 'false')
    log = log in ('true', '1', 'on', 'yes', 'y')
    line = request.values.get('line', 'false')
    line = line in ('true', '1', 'on', 'yes', 'y')
    ma = request.values.get('ma', 'false')
    ma = ma in ('true', '1', 'on', 'yes', 'y')
    dst_mins = int(request.values.get('dst', '0'))
    hour = time()//60//60
    url = 'https://www.binance.com/api/v1/klines?interval={interval}&symbol={symbol}&limit={limit}'.format(interval=interval, symbol=symbol, limit=candles)
    df = read_frame(url, time_zone_offset=dst_mins, cache_t=hour)
    if in_cur != to_currency and from_cur != to_currency:
        fwd = in_cur in ('USDT', 'BTC')
        symbol = (to_currency + in_cur) if fwd else (in_cur + to_currency)
        if symbol == 'USDTBTC':
            fwd = not fwd
            symbol = 'BTCUSDT'
        url = 'https://www.binance.com/api/v1/klines?interval={interval}&symbol={symbol}&limit={limit}'.format(interval=interval, symbol=symbol, limit=candles)
        to_df = read_frame(url, time_zone_offset=dst_mins, cache_t=hour)
        rows = min(len(df), len(to_df))
        if len(df) > rows:
            df = df.iloc[-rows:].reset_index(drop=True)
        if len(to_df) > rows:
            to_df = to_df.iloc[-rows:].reset_index(drop=True)
        if fwd:
            df['open'] /= to_df['open']
            df['hi'] /= to_df['hi']
            df['lo'] /= to_df['lo']
            df['close'] /= to_df['close']
        else:
            df['open'] *= to_df['open']
            df['hi'] *= to_df['hi']
            df['lo'] *= to_df['lo']
            df['close'] *= to_df['close']
    else:
        to_currency = in_cur

    title = from_cur + '/' + to_currency
    return plot2html(df, title, interval, log, line, ma)


@functools.lru_cache(maxsize=5)
def read_frame(url, time_zone_offset, **kwargs):
    print(url)
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns='time open hi lo close vol time_close a b c d e'.split())
    if time_zone_offset:
        df['time'] += time_zone_offset * 60 * 1000
    df = df.astype(dtype = {
            'open':  'float64',
            'close': 'float64',
            'hi':    'float64',
            'lo':    'float64',
            'time':  'datetime64[ms]'})
    return df


def plot2html(df, title, interval, log, line, ma):
    df = df.iloc[1:]
    up = df.close > df.open
    dn = df.open  > df.close

    kwargs = dict(
            title = title,
            tools = 'xpan, xwheel_zoom, box_zoom, reset',
            active_drag = 'box_zoom')
    if log:
        kwargs['y_axis_type'] = 'log'
    plot = figure(x_axis_type='datetime', sizing_mode='stretch_both', **kwargs)
    plot.toolbar.active_scroll = plot.select_one(WheelZoomTool)
    plot.background_fill_alpha = 0
    plot.border_fill_alpha = 0
    plot.grid.grid_line_alpha = 0.2
    plot.outline_line_alpha = 0.4
    plot.xaxis.axis_line_color = 'whitesmoke'
    plot.yaxis.axis_line_color = 'whitesmoke'
    plot.xaxis.axis_line_alpha = 0
    plot.yaxis.axis_line_alpha = 0
    plot.xaxis.major_tick_line_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0
    plot.xaxis.minor_tick_line_alpha = 0
    plot.yaxis.minor_tick_line_alpha = 0
    dtf = DatetimeTickFormatter()
    dtf.milliseconds = ['%T']
    dtf.seconds = dtf.minsec = ['%T']
    dtf.hours = dtf.hourmin = dtf.minutes = ['%R']
    dtf.days = ['%F']
    dtf.months = ['%F']
    dtf.years = ['%F']
    plot.xaxis.formatter = dtf

    if line:
        plot.line(df.time, df.close, color='#55bb77')
    else:
        pass

    if ma:
        for i,n in enumerate([50, 200]):
            dma = df.close.rolling(n).mean()
            col = bokeh.palettes.Category20[20][i%20]
            plot.line(df.time, dma, color=col, legend_label='MA-%i'%n)
        plot.legend.background_fill_color = '#222222'
        plot.legend.background_fill_alpha = 0.6
        plot.legend.label_text_color = 'whitesmoke'

    if not line:
        totime = {'1m':60, '5m':5*60, '15m':15*60, '30m':30*60, '1h':60*60, '2h':2*60*60, '4h':4*60*60, '6h':6*60*60, '12h':12*60*60, '1d':24*60*60, '1w':7*24*60*60}
        w = totime[interval] * 0.7 * 1000
        plot.segment(df.time[up], df.hi[up], df.time[up], df.lo[up], color='#33dd99')
        plot.segment(df.time[dn], df.hi[dn], df.time[dn], df.lo[dn], color='#ff8866')
        plot.vbar(df.time[up], w, df.open[up], df.close[up], fill_color='#558866', line_color='#33dd99')
        plot.vbar(df.time[dn], w, df.open[dn], df.close[dn], fill_color='#cc9988', line_color='#ff8866')

    script,div = plot_html(plot)
    return div + script
