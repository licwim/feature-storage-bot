# !/usr/bin/env python

from fsb import logger
from fsb.config import Config
from fsb.error import ExitHandlerException
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class Handler:

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._loop = client.loop
        self.entity = None
        self._handler_name = self.__class__.__name__
        self._debug = False

    def listen(self):
        logger.info(f"Add handler: {self._handler_name}")

    async def handle(self, event):
        logger.info(f"Start handle {self._handler_name}")

    def handle_decorator(callback: callable):
        async def handle(self, event):
            try:
                await callback(self, event)
            except ExitHandlerException as ex:
                if ex.handler_class:
                    logger.warning(ex.message)
                pass
            except AttributeError as ex:
                logger.exception(ex.args)
        return handle
    handle_decorator = staticmethod(handle_decorator)


class MessageHandler(Handler):

    def listen(self):
        self._client.add_messages_handler(self.handle)
        super().listen()

    async def handle(self, event):
        if self._debug and event.sender.username not in Config.contributors:
            raise ExitHandlerException(self._handler_name, "Debug handler. Sender not in contributors")
        await super().handle(event)

        logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_event(event)
        )
        self.entity = await self._client.get_entity(event.chat_id)

        if not self.entity:
            raise ExitHandlerException(self._handler_name, f"Entity not found by chat id: {event.chat_id}")
        elif event.message.out:
            raise ExitHandlerException
