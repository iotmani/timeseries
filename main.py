import logging
from parse import HTTPLogParser
from action import TerminalNotifier
from analyze import HTTPEventProcessor
from argparse import ArgumentParser


def main():
    """ Extract data from logs, analyze them and take appropriate actions """

    logging.basicConfig(level=logging.INFO)
    argsParser = ArgumentParser()
    argsParser.add_argument("logfile", help="HTTP log path, e.g. tests/sample_csv.txt")
    args = argsParser.parse_args()

    # Construct HTTP specific logs parser, processor and a terminal notification handler
    HTTPLogParser(HTTPEventProcessor(TerminalNotifier()), path=args.logfile).parse()


if __name__ == "__main__":
    main()