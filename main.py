import argparse
import datetime
import logging

import backtrader as bt

from bot.strategy import EMACrossWithKD


def _config_logger(level: str):
    formatter = logging.Formatter('%(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.getLevelNamesMapping().get(level, logging.INFO)
    logging.basicConfig(level=logging.getLevelNamesMapping().get(level, logging.INFO), handlers=[console_handler])


def main():
    # Script set up.
    parser = argparse.ArgumentParser(description="Algorithm trading bot")
    parser.add_argument("--data-path", type=str, help="Filepath for .csv file used as input by the bot")
    parser.add_argument("--from-date", type=str, help="First day used from data_path. Must be in YYYYMMDD format")
    parser.add_argument("--to-date", type=str, help="Last day used from data_path. Must be in YYYYMMDD format")
    parser.add_argument("--cash", type=float, help="Initial cash available to the bot")
    parser.add_argument("--take-profit", type=float, help="%% of positions to sell after price objective is reached")
    parser.add_argument("--vol-to-avg-vol-ratio", type=float, help="Ratio between volume and its 5D avg to signal buy")
    parser.add_argument("--commission", type=float, help="Commission taken by the broker")
    parser.add_argument("--log-level", type=str, help="Log level to be used by the bot", default="INFO")
    parser.add_argument("--plot", type=bool, default=False, help="If True, call cerebro.plot()")
    args = parser.parse_args()

    _config_logger(args.log_level)
    _logger = logging.getLogger()

    # Backtrader set up.
    cerebro = bt.Cerebro()

    cerebro.addstrategy(
        EMACrossWithKD,
        fast_period=10,
        slow_period=20,
        stop_loss=0.06,
        take_profit=args.take_profit,
        hold_days=2,
        vol_to_avg_vol_ratio=args.vol_to_avg_vol_ratio,
    )

    data = bt.feeds.YahooFinanceCSVData(
        dataname=args.data_path,
        # Do not pass values before this date
        fromdate=datetime.datetime.strptime(args.from_date, "%Y%m%d"),
        # Do not pass values after this date
        todate=datetime.datetime.strptime(args.to_date, "%Y%m%d"),
        reverse=False
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(float(args.cash))
    cerebro.broker.setcommission(float(args.commission))

    portfolio_start = cerebro.broker.getvalue()

    cerebro.run()

    # Run details.
    _logger.info(f"{args.data_path=}")
    _logger.info(f"{args.from_date=}")
    _logger.info(f"{args.to_date=}")
    _logger.info(f"{args.cash=}")
    _logger.info(f"{args.take_profit=}")
    _logger.info(f"{args.vol_to_avg_vol_ratio=}")
    _logger.info(f"{args.commission=}")
    _logger.info(f"{args.log_level=}")
    _logger.info(f"{args.plot=}")
    _logger.info(f"{portfolio_start=}")
    portfolio_end = cerebro.broker.getvalue()
    _logger.info(f"{portfolio_end=:.2f}")

    if args.plot:
        cerebro.plot()


if __name__ == "__main__":
    main()
