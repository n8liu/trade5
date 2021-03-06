from collections import deque
import datetime

import pytest

from src.executionhandler import naive_executionhandler
from src import event


@pytest.fixture
def broker():
    queue = deque()
    broker = naive_executionhandler.NaiveExecutionHandler(queue)
    return broker

def test_calculate_pip_value(broker):
    assert 0.089 < broker.calculate_pip_val('USD_JPY', 105.111, 1000) < 0.096, f'calculation does not equal pip value'
    assert 0.1312 < broker.calculate_pip_val('AUD_JPY', 76.000, 1000) < 0.1316, f'calculation does not equal pip value'
    assert 0.083 < broker.calculate_pip_val('EUR_USD', 1.18068, 1000) < 0.085, f'calculation does not equal pip value'
    assert 0.024 < broker.calculate_pip_val('USD_MXN', 20.63630, 5000) < 0.025, f'calculation does not equal pip value'
    assert 0.10 < broker.calculate_pip_val('USD_CHF', 0.91521, 1000) < 0.11, f'calculation does not equal pip value'

def test_convert_to_usd(broker):
    broker.set_conversion("EUR_USD", 1.18060)
    assert 1180.59 < broker.convert_to_usd("EUR_USD", 1000) < 1180.61, f'calculation does not equal conversion'
    assert 1180.59 < broker.convert_to_usd("EUR_TRY", 1000) < 1180.61, f'calculation does not equal conversion'
    broker.set_conversion("EUR_USD", 1.18068)
    assert 0.099 < broker.convert_to_usd("EUR_USD", 0.0846) < 0.11, f'calculation does not equal conversion'
    broker.set_conversion("EUR_USD", 1.18034)
    assert 1180.33 < broker.convert_to_usd("EUR_SEK", 1000) < 1180.35, f'calculation does not equal conversion'
    broker.set_conversion("USD_SEK", 8.64145)
    assert 999.99 < broker.convert_to_usd("USD_SEK", 1000) < 1000.01, f'calculation does not equal conversion'
    
def test_set_pip_val(broker):
    broker.set_conversion("EUR_USD", 1.18189)
    assert 0.10 < broker.set_pip_value("EUR_CHF", 1.08094, 1000) < 0.12, f'calculation does not equal conversion'
    assert 0.12 < broker.set_pip_value("EUR_GBP", 0.89830, 1000) < 0.14, f'calculation does not equal conversion'
    broker.set_conversion("GBP_USD", 1.31811)
    assert 0.06 < broker.set_pip_value("GBP_USD", 1.81412, 1000) < 0.08
    broker.set_conversion("USD_SGD", 1.34659)
    assert 0.09 < broker.set_pip_value("SGD_JPY", 77.552, 1000) < 0.11