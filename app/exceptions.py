class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class OpenManusError(Exception):
    """Base exception for all OpenManus errors"""


class TokenLimitExceeded(OpenManusError):
    """Exception raised when the token limit is exceeded"""


class ApiError(Exception, RuntimeError):
    pass


class HttpFailed(ApiError):
    """HTTP status code is not 2xx."""

    def __init__(self, status_code):
        self.status_code = status_code


class ActionFailed(ApiError):
    """
    Action failed to execute.

    >>> except ActionFailed as e:
    >>>     if e.code > 0:
    >>>         pass  # error code returned by HTTP API
    >>>     elif e.code < 0:
    >>>         pass  # error code returned by CoolQ
    """

    def __init__(self, code, info=None):
        self.code = code
        self.info = info


class NetworkError(Exception, IOError):
    pass
