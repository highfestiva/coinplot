#!/usr/bin/env python3

import bokeh
from bokeh.embed import components as plot_html
from bokeh.plotting import figure
from bokeh.models import WheelZoomTool
from bokeh.models.formatters import DatetimeTickFormatter
from flask import Flask, request, render_template
import functools
import pandas as pd
import requests


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('main.html', bokeh_version=bokeh.__version__)


@app.route('/<currency>/<to_currency>')
def currency(currency='BTC_USDT', to_currency='USDT'):
    from_cur,in_cur = currency.split('_')
    symbol = currency.replace('_', '')
    interval = request.values.get('interval', '15m')
    log = request.values.get('log', 'false')
    log = log in ('true', '1', 'on', 'yes', 'y')
    line = request.values.get('line', 'false')
    line = line in ('true', '1', 'on', 'yes', 'y')
    url = 'https://www.binance.com/api/v1/klines?interval={interval}&symbol={symbol}'.format(interval=interval, symbol=symbol)
    df = read_frame(url)
    if in_cur != to_currency and from_cur != to_currency:
        fwd = in_cur in ('USDT', 'BTC')
        symbol = (to_currency + in_cur) if fwd else (in_cur + to_currency)
        if symbol == 'USDTBTC':
            fwd = not fwd
            symbol = 'BTCUSDT'
        url = 'https://www.binance.com/api/v1/klines?interval={interval}&symbol={symbol}'.format(interval=interval, symbol=symbol)
        to_df = read_frame(url)
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
    return plot2html(df, title, interval, log, line)


@functools.lru_cache()
def read_frame(url):
    print(url)
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns='time open hi lo close vol time_close a b c d e'.split())
    df = df.astype(dtype = {
            'open':  'float64',
            'close': 'float64',
            'hi':    'float64',
            'lo':    'float64',
            'time':  'datetime64[ms]'})
    return df


def plot2html(df, title, interval, log, line):
    df = df.iloc[1:]
    up = df.close > df.open
    dn = df.open  > df.close
    ma12 = df.close.rolling(12).mean()
    ma26 = df.close.rolling(26).mean()

    kwargs = dict(
            title = title,
            tools = 'xpan, xwheel_zoom, box_zoom, reset',
            sizing_mode = 'scale_width')
    if log:
        kwargs['y_axis_type'] = 'log'
    plot = figure(x_axis_type='datetime', plot_width=1000, plot_height=500, **kwargs)
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
    dtf.days = ['%R %a %b %e']
    dtf.months = ['%F']
    dtf.years = ['%F']
    plot.xaxis.formatter = dtf

    if line:
        plot.line(df.time, df.close, color='#55bb77')
    else:
        pass

    plot.line(df.time, ma12, color='#ffee33', legend='ma-12')
    plot.line(df.time, ma26, color='#3355ff', legend='ma-26')

    if not line:
        totime = {'1m':60, '5m':5*60, '15m':15*60, '30m':30*60, '1h':60*60, '2h':2*60*60, '4h':4*60*60, '6h':6*60*60, '12h':12*60*60, '1d':24*60*60}
        w = totime[interval] * 0.7 * 1000
        plot.segment(df.time[up], df.hi[up], df.time[up], df.lo[up], color='#33dd99')
        plot.segment(df.time[dn], df.hi[dn], df.time[dn], df.lo[dn], color='#ff8866')
        plot.vbar(df.time[up], w, df.open[up], df.close[up], fill_color='#558866', line_color='#33dd99')
        plot.vbar(df.time[dn], w, df.open[dn], df.close[dn], fill_color='#cc9988', line_color='#ff8866')

    plot.legend.background_fill_color = '#222222'
    plot.legend.background_fill_alpha = 0.6
    plot.legend.label_text_color = 'whitesmoke'

    script,div = plot_html(plot)
    return div + script


app.run(host='0.0.0.0', port=5000, threaded=True)
