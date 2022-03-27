# !/usr/bin/env python

from asyncio.exceptions import TimeoutError


class BaseException(Exception):
    message = ''

    def __init__(self, message: str = None):
        super().__init__()
        if not self.message:
            self.message = message


class DisconnectFailedError(BaseException):
    message = "Disconnect error"


class ExitHandlerException(BaseException):
    def __init__(self, handler_class: str = None, reason: str = None):
        message = f"Exit from {handler_class if handler_class else 'Handler'}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)
        self.reason = reason
        self.handler_class = handler_class


class RequiredAttributeError(BaseException, AttributeError):
    pass


class OptionalAttributeError(BaseException, AttributeError):
    pass


class ConversationTimeoutError(BaseException, TimeoutError):
    message = "Долго думаешь."


class InputValueError(BaseException, ValueError):
    message = "Чет какую-то хрень ты написал, давай по-новой"
