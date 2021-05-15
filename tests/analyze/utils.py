from LogsMonitor2000.event import WebLogEvent


def buildEvent(time: int) -> WebLogEvent:
    """ Construct commonly required Event content where only time matters """
    return WebLogEvent(
        time=time,
        priority=WebLogEvent.Priority.MEDIUM,
        message="mymsg",
        rfc931=None,
        authuser=None,
        status=None,
        size=None,
        section="/api",
        source="GCHQ",
        request=None,
    )
