from event import Event


class Action:
    """ Interface for taking action based on events """

    def notify(cls, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    """ Show notification messages in terminal """

    class Colors:
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BOLD = "\033[1m"
        ENDC = "\033[0m"

    _HEADER_WDTH = 80

    def __init__(cls):
        # Print header at start
        # ================================================================================
        # |                              Logs Monitor 2000                               |
        # ================================================================================
        print("=" * TerminalNotifier._HEADER_WDTH)
        print(
            "|"
            + cls.Colors.BOLD
            + "Logs Monitor 2000".center(TerminalNotifier._HEADER_WDTH - 2)
            + cls.Colors.ENDC
            + "|"
        )
        print("=" * TerminalNotifier._HEADER_WDTH)

    def notify(cls, e: Event) -> None:
        """ Not exactly sophisticated but it does the job"""
        if e.priority > Event.Priority.MEDIUM:
            color = cls.Colors.RED
        else:
            color = cls.Colors.BOLD

        print(f"{color}{e.time}{cls.Colors.ENDC} - {e.message}")
