#!/usr/bin/env python3

import bokeh
import coinplot
from flask import Flask, render_template, make_response


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('coinplot.html', bokeh_version=bokeh.__version__, fetchpath='/coinplot')


@app.route('/coinplot/<currency>/<to_currency>')
def currency(currency='BTC_USDT', to_currency='USDT'):
    html = coinplot.plot(currency, to_currency)
    resp = make_response(html)
    resp.cache_control.max_age = 10*60
    return resp


app.run(host='0.0.0.0', port=5001, threaded=True)
