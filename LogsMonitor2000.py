import logging
from parse import HTTPLogParser
from action import TerminalNotifier
from analyze import StatsProcessor
from argparse import ArgumentParser


def main():
    """ Extract data from logs, analyze them and take appropriate actions """
    argsParser = ArgumentParser(description="Parse HTTP logs and monitor traffic")
    argsParser.add_argument("logfile", help="HTTP log path, e.g. tests/sample_csv.txt")
    argsParser.add_argument("--verbose", help="Print DEBUG lines", action="store_true")
    argsParser.add_argument(
        "--stats_interval",
        help="Print general stats every x seconds",
        type=int,
        default=10,
    )
    argsParser.add_argument(
        "--high_traffic_threshold",
        help="Number of requests to exceed within a time interval in order to trigger an alert",
        type=int,
        default=10,
    )
    argsParser.add_argument(
        "--high_traffic_time_interval",
        help="Window length in seconds in which we check for high traffic",
        type=int,
        default=120,
    )

    argsParser.add_argument(
        "--monitor",
        help="continuous file watching for updates",
        action="store_true",
    )

    args = argsParser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Construct HTTP-specific logs parser, to be analyzed by a stats processor, and displayed in a terminal notification handler
    HTTPLogParser(
        StatsProcessor(
            TerminalNotifier(),
            statsInterval=args.stats_interval,
            highTrafficAvgThreshold=args.high_traffic_threshold,
            highTrafficInterval=args.high_traffic_time_interval,
        ),
        path=args.logfile,
        isMonitorMode=args.monitor,
    ).parse()


if __name__ == "__main__":
    main()