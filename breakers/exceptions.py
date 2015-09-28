class BreakerException(Exception):
    """All Breaker Exceptions subclass this exception."""
    pass


class BreakerOpen(BreakerException):
    pass
