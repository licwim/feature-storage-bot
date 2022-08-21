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


class ExitControllerException(BaseFsbException):
    def __init__(self, controller_class: str = None, reason: str = None):
        message = f"Exit from {controller_class if controller_class else 'Controller'}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)
        self.reason = reason
        self.controller_class = controller_class


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
