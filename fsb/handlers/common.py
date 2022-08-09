# !/usr/bin/env python

from asyncio import sleep
from typing import Type

from fsb import logger
from fsb.config import Config
from fsb.db.models import QueryEvent
from fsb.error import ExitHandlerException
from fsb.handlers.events import EventDTO, MessageEventDTO, CallbackQueryEventDTO, MenuEventDTO, ChatActionEventDTO
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class Handler:
    # Handlers areas
    ALL = 0
    ONLY_CHAT = 1
    ONLY_USER = 2

    MAX_WAITING = 60 * 2

    _debug = False
    _area = ALL
    _event_class = EventDTO

    def __init__(self, client: 'TelegramApiClient'):
        self._client = client
        self._loop = client.loop
        self._handler_name = self.__class__.__name__
        self._waiting_list = {}

    def listen(self):
        logger.info(f"Add handler: {self._handler_name}")

    async def handle(self, event: EventDTO):
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
                event = self._event_class(event)
                await callback(self, event)
            except ExitHandlerException as ex:
                if ex.handler_class:
                    logger.warning(ex.message)
                pass
            except AttributeError as ex:
                logger.exception(ex.args)
        return handle

    async def _init_filter(self, event: EventDTO):
        area_check = True

        if self._area != self.ALL:
            match event.chat_type:
                case 'Chat' | 'Channel':
                    area_check = self._area == self.ONLY_CHAT
                case 'User':
                    area_check = self._area == self.ONLY_USER
                case _:
                    area_check = False
        if not area_check:
            raise ExitHandlerException

    def set_wait(self, chat_id: int, value: bool):
        self._waiting_list[chat_id] = value


class MessageHandler(Handler):
    _event_class = MessageEventDTO

    def listen(self):
        self._client.add_message_handler(self.handle)
        super().listen()

    async def _init_filter(self, event: MessageEventDTO):
        await super()._init_filter(event)
        if self._debug and event.sender.username not in Config.contributors:
            raise ExitHandlerException(self._handler_name, "Debug handler. Sender not in contributors")

        if event.message.out:
            raise ExitHandlerException

    async def handle(self, event: MessageEventDTO):
        await super().handle(event)
        logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_message_event(event)
        )


class CallbackQueryHandler(Handler):
    _event_class = CallbackQueryEventDTO

    def __init__(self, client: 'TelegramApiClient', query_event_class: Type[QueryEvent]):
        super().__init__(client)
        self._query_event_class = query_event_class

    def listen(self):
        self._client.add_callback_query_handler(self.handle)
        super().listen()

    async def _init_filter(self, event: CallbackQueryEventDTO):
        await super()._init_filter(event)
        query_event = QueryEvent.find_and_create(int(event.data))
        if not isinstance(query_event, self._query_event_class):
            raise ExitHandlerException
        event.query_event = query_event

    async def handle(self, event: CallbackQueryEventDTO):
        await super().handle(event)
        logger.info(
            "Callback Query event:\n" +
            InfoBuilder.build_message_info_by_query_event(event)
        )


class BaseMenu(CallbackQueryHandler):
    _event_class = MenuEventDTO

    INPUT_TIMEOUT = 60

    def __init__(self, client: 'TelegramApiClient', query_event_class: Type[QueryEvent]):
        super().__init__(client, query_event_class)

    async def _init_filter(self, event: MenuEventDTO):
        await super()._init_filter(event)
        sender = event.sender.id
        if event.query_event.sender and event.query_event.sender != sender:
            raise ExitHandlerException
        event.menu_message = await self._client._client.get_messages(event.chat, ids=event.source_message_id)


class ChatActionHandler(Handler):
    _event_class = ChatActionEventDTO

    def __init__(self, client: 'TelegramApiClient', only_self: bool = True):
        super().__init__(client)
        self._only_self = only_self

    def listen(self):
        self._client.add_chat_action_handler(self.handle)
        super().listen()

    async def _init_filter(self, event: ChatActionEventDTO):
        await super()._init_filter(event)
        if self._only_self and self._client._current_user.id not in event.user_ids:
            raise ExitHandlerException

    async def handle(self, event: ChatActionEventDTO):
        await super().handle(event)
        logger.info(
            f"Chat Action event:\n" +
            InfoBuilder.build_message_info_by_chat_action(event)
        )
