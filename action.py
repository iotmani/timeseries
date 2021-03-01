import logging
from event import Event


class Action:
    """ One interface for different types notification handling """

    def notify(cls, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    """ Show notification messages in terminal """

    def __init__(cls):
        logging.basicConfig(level=logging.INFO)

    def notify(cls, message: Event) -> None:
        if message.priority > Event.Priority.MEDIUM:
            logging.warn(message)
        else:
            logging.info(message)
