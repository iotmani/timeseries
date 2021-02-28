import logging


""" One interface for different types notification delivery """


class Action:
    def notify(cls, message: str, isSevere: bool = False) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    def __init__(cls):
        logging.basicConfig(level=logging.INFO)

    """ Show notification messages in terminal """

    def notify(cls, message: str, isSevere: bool = False) -> None:
        if isSevere:
            logging.warn(message)
        else:
            logging.info(message)
