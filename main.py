from parse import HTTPLogParser
from analyze import HTTPEventProcessor
from action import TerminalNotifier


""" Extract data from logs, analyze them and take appropriate actions """


def main():
    HTTPLogParser(HTTPEventProcessor(TerminalNotifier())).parse()


if __name__ == "__main__":
    main()