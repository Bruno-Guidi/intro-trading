import collections
import datetime
import math

from backtrader import Strategy, Order
from backtrader.indicators import ExponentialMovingAverage, Stochastic, RelativeStrengthIndex

from bot.util import debug, info, warning, order_size


class AvgVolume:
    """Average volume of the past N days."""
    def __init__(self, days):
        # Recent values are at the right end of the deque.
        self._deque = collections.deque(maxlen=days)
        self._max_size = days
        self._sum = 0

    def update(self, volume: float):
        if len(self._deque) == 5:
            self._sum -= self._deque.popleft()
        self._deque.append(volume)
        self._sum += volume

    @property
    def avg(self):
        return self._sum/len(self._deque)


class EMACrossWithKD(Strategy):

    def __init__(
            self,
            fast_period: int,
            slow_period: int,
            stop_loss: float,
            take_profit: float,
            hold_days: int,
            vol_to_avg_vol_ratio: float,
    ):
        self._trend = ExponentialMovingAverage(self.datas[0], period=100)

        self._hold_days = datetime.timedelta(days=hold_days)  # Minimum days to hold a position.
        self._qty = 0
        self._buy_date = None

        self._stop_loss = stop_loss
        self._stop_loss_order = None
        self._should_adjust_sl, self._adjusted_price = False, 0

        self._take_profit = take_profit

        self._fast_ema = ExponentialMovingAverage(self.datas[0], period=fast_period)
        self._slow_ema = ExponentialMovingAverage(self.datas[0], period=slow_period)

        self._lower_band, self._upper_band = 40, 70
        self._k = Stochastic(self.datas[0], upperband=self._upper_band, lowerband=self._lower_band)
        self._d = self._k.lines[1]

        self._avg_volume = AvgVolume(days=5)
        self._vol_to_avg_vol_ratio = vol_to_avg_vol_ratio

        self._rsi = RelativeStrengthIndex(self.datas[0])

    @property
    def today(self):
        return self.datas[0].datetime.date(0)

    @property
    def close_price(self):
        return self.datas[0].close

    @property
    def volume(self):
        return self.datas[0].volume

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

    def _buy_signal_kd(self):
        if self._qty > 0:
            return False

        in_downtrend = self._trend[0] < self._trend[-1]

        oversold = self._k <= self._lower_band
        k_under_d_minus1 = self._k[-1] <= self._d[-1]
        k_under_d_minus0 = self._k[0] <= self._d[0]

        debug(self, f"{in_downtrend=}, {k_under_d_minus1=}, {k_under_d_minus0=:}, {oversold=}")

        signal = not in_downtrend and oversold and k_under_d_minus1 and not k_under_d_minus0
        if signal:
            info(self, f"buy signal, {in_downtrend=}, {k_under_d_minus1=}, {k_under_d_minus0=:}, {oversold=}")
        return signal

    def _buy_signal_ema100(self):
        """Close price should cross over EMA100 with significant volume."""
        if self._qty > 0:
            return False

        in_downtrend = self._trend[0] < self._trend[-1]
        if in_downtrend:
            return False

        ma100_crossed = self.close_price[-1] < self._trend[0] and self.close_price[0] > self._trend[0]
        vol_to_avg_vol = self.volume[0]/self._avg_volume.avg
        debug(self, f"{ma100_crossed=}, vol={self.volume[0]:.0f}, avg_vol={self._avg_volume.avg:.0f}, {vol_to_avg_vol=:.2f}")

        signal = ma100_crossed and vol_to_avg_vol >= self._vol_to_avg_vol_ratio

        if signal:
            info(self, f"buy signal, {ma100_crossed=}, vol={self.volume[0]:.0f}, avg_vol={self._avg_volume.avg:.0f}, {vol_to_avg_vol=:.2f}")

        return signal

    def _sell_signal(self):
        if self._qty == 0:
            return False

        min_hold_elapsed = self.today - self._buy_date >= self._hold_days
        fast_over_slow_minus1 = self._fast_ema[-1] > self._slow_ema[-1]
        fast_over_slow_minus0 = self._fast_ema[0] > self._slow_ema[0]

        debug(self, f"{min_hold_elapsed=}, {fast_over_slow_minus1=}, {fast_over_slow_minus0=}")

        return min_hold_elapsed and fast_over_slow_minus1 and not fast_over_slow_minus0

    def _stop_loss_change(self):
        if self._stop_loss_order is None:
            return False

        overbought_minus1 = self._rsi[-1] > self._upper_band
        overbought_minus0 = self._rsi[0] > self._upper_band
        k_under_d_minus1 = self._k[-1] <= self._d[-1]
        k_under_d_minus0 = self._k[0] <= self._d[0]

        debug(self, f"{k_under_d_minus1=}, {k_under_d_minus0=}, {overbought_minus1=}")

        return overbought_minus1 and not overbought_minus0

    def next(self):
        self._avg_volume.update(self.volume[0])

        if self._buy_signal_kd() or self._buy_signal_ema100():
            size = order_size(self.close_price, self.cash, 97)
            self.submit_buy(self.close_price, size, Order.Limit)
            return
        if self._sell_signal():
            info(self, "Triggered sell signal")
            self.submit_sell(self.close_price, self._qty, Order.Market)

            # If we wait for the sell to be accepted for cancelling the SL, we
            # run into problems if both orders are executed the same day.
            self.cancel(self._stop_loss_order)
            self._should_adjust_sl = False
            return
        if self._stop_loss_change():
            self.cancel(self._stop_loss_order)
            self._adjusted_price = self.close_price - self.close_price*self._stop_loss
            self._should_adjust_sl = True
            return

    def notify_order(self, order):
        action = "BUY" if order.isbuy() else "SELL"

        if order.status == order.Submitted:
            debug(self, f"Submitted {action} - {order.getordername()}")
            return None
        elif order.status == order.Accepted:
            info(self, f"Accepted {action} - {order.getordername()}")
            if order.issell():
                if order.exectype == Order.StopLimit:
                    self._stop_loss_order = order
            return None
        elif order.status == order.Partial:
            debug(self, f"Partial {action} - {order.getordername()}")
            return None
        elif order.status == order.Completed:
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
            else:
                self._qty += order.executed.size  # Size of SELL is negative.
        elif order.status == order.Margin:
            # The price went up, and we don't have enough money to make the planned buy.
            warning(self, f"Margin {action}: {self.close_price[0]=}")
            if self._buy_signal_kd():
                size = order_size(self.close_price, self.cash, 100)
                self.submit_buy(self.close_price, size, Order.Limit)
        elif order.status == Order.Canceled and order.exectype == Order.StopLimit:  # Stop loss
            if self._should_adjust_sl:
                info(self, f"Stop loss adjusted, from={self._stop_loss_order.price:.2f}, to={self._adjusted_price:.2f}")

                # Take profit.
                size = math.floor(self._stop_loss_order.size * self._take_profit)
                self.submit_sell(self.close_price, size, Order.Market)

                # Adjusted stop loss.
                self.submit_sell(self._adjusted_price, self._stop_loss_order.size - size, Order.StopLimit)
                self._should_adjust_sl = False
            else:
                info(self, f"Stop loss cancelled")
                self._stop_loss_order = None
        else:
            warning(self, f"{order.getstatusname()} {action} - {order.getordername()}")
