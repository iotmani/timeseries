from event import Event


class Action:
    """ One interface for taking action based on events """

    def notify(cls, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    """ Show a notification messages in terminal """

    HEADER_WIDTH = 80

    def __init__(cls):
        print("=" * TerminalNotifier.HEADER_WIDTH)
        print("|" + "Logs Viewer 2000".center(TerminalNotifier.HEADER_WIDTH - 2) + "|")
        print("=" * TerminalNotifier.HEADER_WIDTH)

    def notify(cls, message: Event) -> None:
        if message.priority > Event.Priority.MEDIUM:
            print("Warning: " + str(message))
        else:
            print(message)
