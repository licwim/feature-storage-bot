# !/usr/bin/env python


class BaseException(Exception):

    def __init__(self, message):
        super().__init__()
        self.message = message


class DisconnectFailedError(BaseException):

    def __init__(self):
        super().__init__("Disconnect error")


class ExitHandlerException(BaseException):

    def __init__(self, handler_class: str = None, reason: str = None):
        message = f"Exit from {handler_class if handler_class else 'Handler'}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)
        self.reason = reason
        self.handler_class = handler_class
