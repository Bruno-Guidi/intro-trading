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
    parser.add_argument("data_path", type=str, help="Filepath for .csv file used as input by the bot")
    parser.add_argument("from_date", type=str, help="First day used from data_path. Must be in YYYYMMDD format")
    parser.add_argument("to_date", type=str, help="Last day used from data_path. Must be in YYYYMMDD format")
    parser.add_argument("initial_cash", type=float, help="Initial cash available to the bot")
    parser.add_argument("take_profit", type=float, help="% of positions to sell after price objective is reached")
    parser.add_argument("commission", type=float, help="Commission taken by the broker")
    parser.add_argument("log_level", type=str, help="Log level to be used by the bot")
    parser.add_argument("--plot", type=bool, default=False, help="If True, call cerebro.plot()")
    args = parser.parse_args()

    _config_logger(args.log_level)
    _logger = logging.getLogger()

    _logger.info(
        "Parsed arguments: data_path=%s, from_date=%s, to_date=%s, initial_cash=%.4f, commission=%.4f, log_level=%s",
        args.data_path, args.from_date, args.to_date, args.initial_cash, args.commission, args.log_level)

    # Backtrader set up.
    cerebro = bt.Cerebro()

    cerebro.addstrategy(
        EMACrossWithKD,
        fast_period=10,
        slow_period=20,
        stop_loss=0.06,
        take_profit=args.take_profit,
        hold_days=2
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

    cerebro.broker.setcash(float(args.initial_cash))
    cerebro.broker.setcommission(float(args.commission))

    # Print out the starting conditions
    _logger.info('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    _logger.info('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if args.plot:
        cerebro.plot()


if __name__ == "__main__":
    main()
