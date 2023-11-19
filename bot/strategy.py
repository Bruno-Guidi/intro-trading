import datetime

from backtrader import Strategy, Order
from backtrader.indicators import ExponentialMovingAverage, Stochastic

from bot.util import debug, info, warning, order_size


class EMACrossWithKD(Strategy):

    def __init__(self, fast_period: int, slow_period: int, stop_loss: float, hold_days: int):
        pass

    @property
    def today(self):
        return self.datas[0].datetime.date(0)

    @property
    def close_price(self):
        return self.datas[0].close

    @property
    def cash(self):
        return self.broker.get_cash()

    def submit_buy(self, price, size, exec_type):
        if size == 0:
            return
        order = self.buy(size=size, price=price, exectype=exec_type)

        amount = size*price
        msg = "price={:.2f}, size={}, amount={:.2f}, cash={:.2f}".format(
            amount/size, size, amount, self.cash
        )
        info(self, msg)

        return order

    def submit_sell(self, price, size, exec_type):
        if size == 0:
            return
        order = self.sell(size=size, price=price, exectype=exec_type, plimit=price)

        amount = size*price
        msg = "price={:.2f}, size={}, amount={:.2f}, cash={:.2f}".format(
            amount/size, size, amount, self.cash
        )
        info(self, msg)

        return order

    def _buy_signal(self):
        pass

    def _sell_signal(self):
        pass

    def _adjust_stop_loss(self):
        pass

    def next(self):
        pass

    def notify_order(self, order):
        pass
