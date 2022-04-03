# !/usr/bin/env python

from fsb import logger
from fsb.config import Config
from fsb.db.models import QueryEvent
from fsb.error import ExitHandlerException
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class Handler:
    # Handlers areas
    ALL = 0
    ONLY_CHAT = 1
    ONLY_USER = 2

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._loop = client.loop
        self.entity = None
        self.event = None
        self._handler_name = self.__class__.__name__
        self._debug = False
        self._area = self.ALL

    def listen(self):
        logger.info(f"Add handler: {self._handler_name}")

    async def handle(self, event):
        logger.info(f"Start handle {self._handler_name}")
        self.event = event
        self.entity = event.chat

        if not self.entity:
            raise ExitHandlerException(self._handler_name, f"Entity not found by chat id: {event.chat_id}")

    @staticmethod
    def handle_decorator(callback: callable):
        async def handle(self, event):
            try:
                area_check = True
                if self._area != self.ALL:
                    match event.chat.__class__.__name__:
                        case 'Chat' | 'Channel':
                            area_check = self._area == self.ONLY_CHAT
                        case 'User':
                            area_check = self._area == self.ONLY_USER
                        case _:
                            area_check = False
                if area_check:
                    await callback(self, event)
            except ExitHandlerException as ex:
                if ex.handler_class:
                    logger.warning(ex.message)
                pass
            except AttributeError as ex:
                logger.exception(ex.args)
        return handle


class MessageHandler(Handler):

    def listen(self):
        self._client.add_message_handler(self.handle)
        super().listen()

    async def handle(self, event):
        if self._debug and event.sender.username not in Config.contributors:
            raise ExitHandlerException(self._handler_name, "Debug handler. Sender not in contributors")
        await super().handle(event)

        if event.message.out:
            raise ExitHandlerException

        logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_message_event(event)
        )


class CallbackQueryHandler(Handler):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self.query_event = None

    def listen(self):
        self._client.add_callback_query_handler(self.handle)
        super().listen()

    async def handle(self, event):
        await super().handle(event)

        self.query_event = QueryEvent.find_and_create(int(event.data))

        logger.info(
            "Callback Query event:\n" +
            InfoBuilder.build_message_info_by_query_event(event, self.query_event)
        )


class BaseMenu(CallbackQueryHandler):
    INPUT_TIMEOUT = 60

    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self._menu_message = None
        self._sender = None

    async def handle(self, event):
        await super().handle(event)

        self._sender = self.event.sender.id
        if self.query_event.sender and self.query_event.sender != self._sender:
            return

        self._menu_message = await self._client._client.get_messages(self.entity, ids=event.query.msg_id)
