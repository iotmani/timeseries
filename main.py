from parse import HTTPLogParser
from analyze import HTTPEventProcessor
from action import TerminalNotifier
from argparse import ArgumentParser

""" Extract data from logs, analyze them and take appropriate actions """


def main():
    argsParser = ArgumentParser()
    argsParser.add_argument(
        "--log", help="Log file path", default="tests/small_sample_csv.txt"
    )
    args = argsParser.parse_args()
    HTTPLogParser(HTTPEventProcessor(TerminalNotifier()), path=args.log).parse()


if __name__ == "__main__":
    main()