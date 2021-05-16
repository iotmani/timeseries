from .event import Event
from datetime import datetime


class Action:
    """ Interface for taking action based on events """

    def notify(self, message: Event) -> None:
        raise NotImplementedError()


class TerminalNotifier(Action):
    """ Show notification messages in terminal """

    class Colors:
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BOLD = "\033[1m"
        ENDC = "\033[0m"

    _HEADER_WDTH = 80

    def __init__(self):
        # Print header at start
        # ================================================================================
        # |                              Logs Monitor 2000                               |
        # ================================================================================
        print("=" * TerminalNotifier._HEADER_WDTH)
        print(
            "|"
            + self.Colors.BOLD
            + "Logs Monitor 2000".center(TerminalNotifier._HEADER_WDTH - 2)
            + self.Colors.ENDC
            + "|"
        )
        print("=" * TerminalNotifier._HEADER_WDTH)

    def notify(self, e: Event) -> None:
        """Print to alert to console, high priority colored accordingly"""
        # Not exactly sophisticated but it does the job nicely
        if e.priority > Event.Priority.MEDIUM:
            color = self.Colors.RED
        else:
            color = self.Colors.BOLD

        print(
            f"{color}{datetime.fromtimestamp(e.time)}{self.Colors.ENDC} - {e.message}"
        )
