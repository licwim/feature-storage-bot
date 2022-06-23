# !/usr/bin/env python

from asyncio.exceptions import TimeoutError


class BaseFsbException(Exception):
    message = ''

    def __init__(self, message: str = None):
        if not self.message:
            self.message = message
        super().__init__(self.message)


class DisconnectFailedError(BaseFsbException):
    message = "Disconnect error"


class ExitHandlerException(BaseFsbException):
    def __init__(self, handler_class: str = None, reason: str = None):
        message = f"Exit from {handler_class if handler_class else 'Handler'}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)
        self.reason = reason
        self.handler_class = handler_class


class RequiredAttributeError(BaseFsbException, AttributeError):
    pass


class OptionalAttributeError(BaseFsbException, AttributeError):
    pass


class ConversationTimeoutError(BaseFsbException, TimeoutError):
    message = "Долго думаешь."


class InputValueError(BaseFsbException, ValueError):
    message = "Чет какую-то хрень ты написал, давай по-новой"


class DuplicateHandlerError(BaseFsbException):
    def __init__(self, handler_name: str, pipeline_name: str = None):
        super().__init__(f"{handler_name} is duplicated in {pipeline_name}")
