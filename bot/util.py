import inspect
import logging
import math

_logger = logging.getLogger()


def debug(strategy, msg):
    caller = inspect.stack()[1].function
    _logger.debug("%s - %s: %s", strategy.datas[0].datetime.date(0), caller, msg)


def info(strategy, msg):
    caller = inspect.stack()[1].function
    _logger.info("%s - %s: %s", strategy.datas[0].datetime.date(0), caller, msg)


def warning(strategy, msg):
    caller = inspect.stack()[1].function
    _logger.warning("%s - %s: %s", strategy.datas[0].datetime.date(0), caller, msg)


def error(strategy, msg):
    caller = inspect.stack()[1].function
    _logger.error("%s - %s: %s", strategy.datas[0].datetime.date(0), caller, msg)


def order_size(price: float, capital: float, percentage: int) -> int:
    if not (0 < percentage <= 100):
        raise ValueError("percentage should be between 0 and 100 (inclusive)")

    capital = capital * percentage / 100
    return math.floor(capital / price)
