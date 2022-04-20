# !/usr/bin/env python

from asyncio import sleep
from typing import Type

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

    MAX_WAITING = 60 * 2

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._loop = client.loop
        self.entity = None
        self.event = None
        self._handler_name = self.__class__.__name__
        self._debug = False
        self._area = self.ALL
        self._waiting_list = {}

    def listen(self):
        logger.info(f"Add handler: {self._handler_name}")

    async def handle(self, event):
        if event.chat.id in self._waiting_list:
            time = 0
            while self._waiting_list[event.chat.id]:
                await sleep(1)
                time += 1
                if time >= self.MAX_WAITING:
                    raise TimeoutError
        await self._init_filter(event)
        logger.info(f"Start handle {self._handler_name}")

    @staticmethod
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

    async def _init_filter(self, event):
        self.event = event
        self.entity = event.chat

        area_check = True
        if self._area != self.ALL:
            match event.chat.__class__.__name__:
                case 'Chat' | 'Channel':
                    area_check = self._area == self.ONLY_CHAT
                case 'User':
                    area_check = self._area == self.ONLY_USER
                case _:
                    area_check = False
        if not area_check:
            raise ExitHandlerException

    def set_wait(self, value: bool):
        self._waiting_list[self.entity.id] = value


class MessageHandler(Handler):

    def listen(self):
        self._client.add_message_handler(self.handle)
        super().listen()

    async def _init_filter(self, event):
        await super()._init_filter(event)
        if self._debug and event.sender.username not in Config.contributors:
            raise ExitHandlerException(self._handler_name, "Debug handler. Sender not in contributors")

        if event.message.out:
            raise ExitHandlerException

    async def handle(self, event):
        await super().handle(event)
        logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_message_event(event)
        )


class CallbackQueryHandler(Handler):

    def __init__(self, client: TelegramApiClient, event_class: Type[QueryEvent]):
        super().__init__(client)
        self._event_class = event_class
        self.query_event = None

    def listen(self):
        self._client.add_callback_query_handler(self.handle)
        super().listen()

    async def _init_filter(self, event):
        await super()._init_filter(event)
        query_event = QueryEvent.find_and_create(int(event.data))
        if not isinstance(query_event, self._event_class):
            raise ExitHandlerException
        self.query_event = query_event

    async def handle(self, event):
        await super().handle(event)
        logger.info(
            "Callback Query event:\n" +
            InfoBuilder.build_message_info_by_query_event(event, self.query_event)
        )


class BaseMenu(CallbackQueryHandler):
    INPUT_TIMEOUT = 60

    def __init__(self, client: TelegramApiClient, event_class: Type[QueryEvent]):
        super().__init__(client, event_class)
        self._menu_message = None
        self._sender = None

    async def _init_filter(self, event):
        await super()._init_filter(event)
        sender = event.sender.id
        if self.query_event.sender and self.query_event.sender != sender:
            raise ExitHandlerException
        self._sender = sender
        self._menu_message = await self._client._client.get_messages(self.entity, ids=event.query.msg_id)


class ChatActionHandler(Handler):
    def __init__(self, client: TelegramApiClient, only_self: bool = True):
        super().__init__(client)
        self._only_self = only_self

    def listen(self):
        self._client.add_chat_action_handler(self.handle)
        super().listen()

    async def _init_filter(self, event):
        await super()._init_filter(event)
        if self._only_self and self._client._current_user.id not in event.user_ids:
            raise ExitHandlerException

    async def handle(self, event):
        await super().handle(event)
        logger.info(
            f"Chat Action event:\n" +
            InfoBuilder.build_message_info_by_chat_action(event)
        )
