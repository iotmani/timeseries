import logging
from argparse import ArgumentParser

from .parse import HTTPLogParser
from .analyze import AnalyticsProcessor
from .action import TerminalNotifier


def main():
    """ Extract data from logs, analyze them and take appropriate actions """
    argsParser = ArgumentParser(description="Parse HTTP logs and monitor traffic")
    argsParser.add_argument("file", help="HTTP log path, e.g. tests/sample_csv.txt")
    argsParser.add_argument("--verbose", help="Print DEBUG lines", action="store_true")
    argsParser.add_argument(
        "--stats_interval",
        help="Print general requests statistics every x seconds",
        type=int,
        default=10,
    )
    argsParser.add_argument(
        "--high_traffic_interval",
        help="Monitor high traffic over window size of x seconds",
        type=int,
        default=120,
    )
    argsParser.add_argument(
        "--high_traffic_threshold",
        help="Number of requests to exceed within that interval in order to trigger an alert",
        type=int,
        default=10,
    )

    argsParser.add_argument(
        "--follow",
        help="Continuously watch file for updates, similar to `tail --follow`",
        action="store_true",
    )

    args = argsParser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Construct the HTTP-specific logs parser, to be analyzed by a stats processor, and
    # displayed in a terminal notification handler
    HTTPLogParser(
        AnalyticsProcessor(
            TerminalNotifier(),
            mostCommonStatsInterval=args.stats_interval,
            highTrafficInterval=args.high_traffic_interval,
            highTrafficThreshold=args.high_traffic_threshold,
        ),
        path=args.file,
        isFollowMode=args.follow,
    ).parse()


if __name__ == "__main__":
    main()