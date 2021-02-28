import logging
from event import Event

""" One interface for different types notification delivery """


class Action:
    def notify(cls, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    def __init__(cls):
        logging.basicConfig(level=logging.INFO)

    """ Show notification messages in terminal """

    def notify(cls, message: Event) -> None:
        if message.priority > Event.Priority.MEDIUM:
            logging.warn(message)
        else:
            logging.info(message)
