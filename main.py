from parse import HTTPLogParser
from action import TerminalNotifier
from analyze import HTTPEventProcessor
from argparse import ArgumentParser


def main():
    """ Extract data from logs, analyze them and take appropriate actions """

    argsParser = ArgumentParser()
    argsParser.add_argument(
        "--log", help="Log file path", default="tests/small_sample_csv.txt"
    )
    args = argsParser.parse_args()

    # Construct HTTP logs specific parser, processor and notification handler
    HTTPLogParser(HTTPEventProcessor(TerminalNotifier()), path=args.log).parse()


if __name__ == "__main__":
    main()