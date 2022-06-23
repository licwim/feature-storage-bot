# !/usr/bin/env python

from fsb.error import DuplicateHandlerError
from fsb.factories import Factory
from fsb.handlers import ChatActionHandler, Handler
from fsb.handlers.chats import JoinChatHandler
from fsb.handlers.ratings import CreateRatingsOnJoinChat
from fsb.telegram.client import TelegramApiClient

initiated_handlers = {}


class Pipeline:
    _available_handlers = []

    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self.factory = Factory(client, self._available_handlers)
        self._init_handlers()

    def _init_handlers(self):
        classname = self.__class__.__name__
        initiated_handlers[classname] = []

        for handler_class in self._available_handlers:
            for pipeline_classname, initiated_handlers_classes in initiated_handlers.items():
                if handler_class in initiated_handlers_classes:
                    raise DuplicateHandlerError(handler_class.__name__, pipeline_classname)
            if self.factory.create_object(handler_class):
                initiated_handlers[classname].append(handler_class)

    async def handle_all(self, event):
        handlers = self.factory.get_objects()
        for handler_class in self._available_handlers:
            await handlers[handler_class].handle(event)


class JoinChatPipeline(Pipeline, ChatActionHandler):
    _available_handlers = [
        JoinChatHandler,
        CreateRatingsOnJoinChat,
    ]

    @Handler.handle_decorator
    async def handle(self, event):
        await self.handle_all(event)
