# !/usr/bin/env python

from asyncio.exceptions import TimeoutError
from typing import Union


class BaseFsbException(Exception):
    message = ''

    def __init__(self, message: str = None):
        if not self.message:
            self.message = message
        super().__init__(self.message)


class DisconnectFailedError(BaseFsbException):
    message = "Disconnect error"


class ExitControllerException(BaseFsbException):
    def __init__(self, object_context: Union[str, object] = None, reason: str = None):
        if not isinstance(object_context, str) and object_context is not None:
            object_context = object_context.__class__.__name__

        message = f"Exit{' from ' + object_context if object_context else ''}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)
        self.reason = reason
        self.class_name = object_context


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
