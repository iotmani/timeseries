from event import Event


class Action:
    """ One interface for taking action based on events """

    def notify(cls, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    """ Show a notification messages in terminal """

    _HEADER_WDTH = 80

    def __init__(cls):
        print("=" * TerminalNotifier._HEADER_WDTH)
        print("|" + "Logs Monitor 2000".center(TerminalNotifier._HEADER_WDTH - 2) + "|")
        print("=" * TerminalNotifier._HEADER_WDTH)

    def notify(cls, e: Event) -> None:
        print(e)
