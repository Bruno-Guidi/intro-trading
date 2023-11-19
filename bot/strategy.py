import datetime

from backtrader import Strategy, Order
from backtrader.indicators import ExponentialMovingAverage, Stochastic

from bot.util import debug, info, warning, order_size


class EMACrossWithKD(Strategy):

    def __init__(self, fast_period: int, slow_period: int, stop_loss: float, hold_days: int):
        self._trend = ExponentialMovingAverage(self.datas[0], period=100)

        self._hold_days = datetime.timedelta(days=hold_days)  # Minimum days to hold a position.
        self._qty = 0
        self._buy_date = None

        self._stop_loss = stop_loss
        self._stop_loss_order = None

        self._fast_ema = ExponentialMovingAverage(self.datas[0], period=fast_period)
        self._slow_ema = ExponentialMovingAverage(self.datas[0], period=slow_period)

        self._lower_band, self._upper_band = 30, 70
        self._k = Stochastic(self.datas[0], upperband=self._upper_band, lowerband=self._lower_band)
        self._d = self._k.lines[1]

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
        if self._qty > 0:
            return False

        in_downtrend = self._trend[0] < self._trend[-1]

        oversold = self._k <= self._lower_band
        k_under_d_minus1 = self._k[-1] <= self._d[-1]
        k_under_d_minus0 = self._k[0] <= self._d[0]

        debug(self, f"{in_downtrend=}, {k_under_d_minus1=}, {k_under_d_minus0=:}, {oversold=}")

        return not in_downtrend and oversold and not k_under_d_minus1 and k_under_d_minus0

    def _sell_signal(self):
        if self._qty == 0:
            return False

        min_hold_elapsed = self.today - self._buy_date >= self._hold_days
        fast_over_slow_minus1 = self._fast_ema[-1] > self._slow_ema[-1]
        fast_over_slow_minus0 = self._fast_ema[0] > self._slow_ema[0]

        debug(self, f"{min_hold_elapsed=}, {fast_over_slow_minus1=}, {fast_over_slow_minus0=}")

        return min_hold_elapsed and fast_over_slow_minus1 and not fast_over_slow_minus0

    def _adjust_stop_loss(self):
        if self._stop_loss_order is None:
            return False

        overbought = self._k > self._upper_band
        k_under_d_minus1 = self._k[-1] <= self._d[-1]
        k_under_d_minus0 = self._k[0] <= self._d[0]

        debug(self, f"{k_under_d_minus1=}, {k_under_d_minus0=}, {overbought=}")

        return overbought and not k_under_d_minus1 and k_under_d_minus0

    def next(self):
        if self._buy_signal():
            info(self, "Triggered buy signal")
            size = order_size(self.close_price, self.cash, 97)
            self.submit_buy(self.close_price, size, Order.Limit)
        if self._sell_signal():
            info(self, "Triggered sell signal")
            self.submit_sell(self.close_price, self._qty, Order.Market)
        if self._adjust_stop_loss():
            pass

    def notify_order(self, order):
        action = "BUY" if order.isbuy() else "SELL"

        if order.status == order.Submitted:
            debug(self, f"Submitted {action} - {order.getordername()}")
            return None

        if order.status == order.Accepted:
            debug(self, f"Accepted {action} - {order.getordername()}")
            if order.issell():
                if order.exectype == Order.StopLimit:
                    self._stop_loss_order = order
                else:
                    info(self, "Stop lost cancelled")
                    self.cancel(self._stop_loss_order)
                    self._stop_loss_order = None
            return None

        if order.status == order.Partial:
            debug(self, f"Partial {action} - {order.getordername()}")
            return None

        if order.status == order.Completed:
            msg = "Executed {} - {}, size={}, price={:.2f}, amount={:.2f}, comm={:.2f}, cash={:.2f}".format(
                action, order.getordername(), order.executed.size, order.executed.price,
                order.executed.value, order.executed.comm, self.cash
            )
            info(self, msg)

            if order.isbuy():
                self._qty = order.executed.size
                self._buy_date = self.today

                # Put a stop loss order.
                price = order.executed.price - order.executed.price*self._stop_loss
                info(self, f"Stop loss active, {price=:.2f}")
                self.submit_sell(price, order.executed.size, Order.StopLimit)
            else:  # Other sell
                self._qty += order.executed.size  # Size of SELL is negative.
        if order.status == order.Margin:
            # The price went up, and we don't have enough money to make the planned buy.
            warning(self, f"Margin {action}: {self.close_price[0]=}")
            if self._buy_signal():
                size = order_size(self.close_price, self.cash, 100)
                self.submit_buy(self.close_price, size, Order.Limit)
        elif order.status in (order.Canceled, order.Rejected):
            warning(self, f"{order.getstatusname()} {action} - {order.getordername()}")
