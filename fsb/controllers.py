# !/usr/bin/env python

import inspect
import re
from asyncio import sleep
from typing import Type

from fsb import logger
from fsb.config import Config
from fsb.db.models import QueryEvent
from fsb.error import ExitControllerException
from fsb.events.common import (
    EventDTO, MessageEventDTO, CallbackQueryEventDTO, MenuEventDTO, ChatActionEventDTO, CommandEventDTO,
    WatcherEventDTO
)
from fsb.events.ratings import RatingQueryEvent
from fsb.events.roles import RoleQueryEvent
from fsb.handlers import Handler
from fsb.handlers.chats import JoinChatHandler
from fsb.handlers.commands import (
    StartCommandHandler, PingCommandHandler, EntityInfoCommandHandler, AboutInfoCommandHandler
)
from fsb.handlers.ratings import (
    CreateRatingsOnJoinChatHandler, RatingsSettingsCommandHandler, RatingCommandHandler, StatRatingCommandHandler,
    RatingsSettingsQueryHandler
)
from fsb.handlers.roles import RolesSettingsCommandHandler, RolesSettingsQueryHandler
from fsb.handlers.watchers import MentionWatcherHandler
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class Controller:
    MAX_WAITING = 60 * 2

    _event_class = EventDTO

    def __init__(self, client: 'TelegramApiClient'):
        self._client = client
        self._loop = client.loop
        self._controller_name = self.__class__.__name__
        self._waiting_list = {}

    def listen(self):
        handle_names = []
        for handle_name, handle in self.get_handle_list():
            self._listen_handle(handle)
            handle_names.append(handle_name.replace('_handle', '', -1))
        logger.info(f"Add controller: {self._controller_name} [{', '.join(handle_names)}]")

    def _listen_handle(self, handle: callable):
        pass

    def get_handle_list(self):
        handle_list = []
        for m in inspect.getmembers(self):
            if not m[0].startswith('_') and m[0].endswith('_handle'):
                if inspect.ismethod(m[1]) or inspect.isfunction(m[1]):
                    handle_list.append(m)
        return handle_list

    async def handle(self, event: EventDTO):
        if event.chat.id in self._waiting_list:
            time = 0
            while self._waiting_list[event.chat.id]:
                await sleep(1)
                time += 1
                if time >= self.MAX_WAITING:
                    raise TimeoutError
        await self._init_filter(event)
        logger.info(f"Start controller {self._controller_name}")

    @staticmethod
    def handle_decorator(callback: callable):
        async def handle(self, event):
            try:
                event = self._event_class(event)
                await callback(self, event)
            except ExitControllerException as ex:
                if ex.controller_class:
                    logger.warning(ex.message)
                pass
            except AttributeError as ex:
                logger.exception(ex.args)
        return handle

    async def _init_filter(self, event: EventDTO):
        area_check = True
        area = event.area

        if area != event.ALL:
            match event.chat_type:
                case 'Chat' | 'Channel':
                    area_check = area == event.ONLY_CHAT
                case 'User':
                    area_check = area == event.ONLY_USER
                case _:
                    area_check = False
        if not area_check:
            raise ExitControllerException

    def set_wait(self, chat_id: int, value: bool):
        self._waiting_list[chat_id] = value

    async def run_handler(self, event: EventDTO, handler_class: Type[Handler]):
        await handler_class(event, self._client).run()


class MessageController(Controller):
    _event_class = MessageEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_message_handler(handle)

    async def _init_filter(self, event: MessageEventDTO):
        await super()._init_filter(event)
        if event.debug and event.sender.username not in Config.contributors:
            raise ExitControllerException(self._controller_name, "Debug handler. Sender not in contributors")

        if event.message.out:
            raise ExitControllerException

    async def handle(self, event: MessageEventDTO):
        await super().handle(event)
        logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_message_event(event)
        )


class CallbackQueryController(Controller):
    _event_class = CallbackQueryEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_callback_query_handler(handle)

    async def _init_filter(self, event: CallbackQueryEventDTO):
        await super()._init_filter(event)
        query_event = QueryEvent.find_and_create(int(event.data))
        if not isinstance(query_event, event.query_event_class):
            raise ExitControllerException
        event.query_event = query_event

    async def handle(self, event: CallbackQueryEventDTO):
        await super().handle(event)
        logger.info(
            "Callback Query event:\n" +
            InfoBuilder.build_message_info_by_query_event(event)
        )


class MenuController(CallbackQueryController):
    _event_class = MenuEventDTO

    async def _init_filter(self, event: MenuEventDTO):
        await super()._init_filter(event)
        sender_id = event.sender.id
        if event.query_event.sender_id and event.query_event.sender_id != sender_id:
            raise ExitControllerException
        event.menu_message = await self._client._client.get_messages(event.chat, ids=event.source_message_id)

    @Controller.handle_decorator
    async def role_menu_handle(self, event: MenuEventDTO):
        event.area = event.ONLY_CHAT
        event.query_event_class = RoleQueryEvent
        await super().handle(event)
        await self.run_handler(event, RolesSettingsQueryHandler)

    @Controller.handle_decorator
    async def ratings_menu_handle(self, event: MenuEventDTO):
        event.area = event.ONLY_CHAT
        event.query_event_class = RatingQueryEvent
        await super().handle(event)
        await self.run_handler(event, RatingsSettingsQueryHandler)


class ChatActionController(Controller):
    _event_class = ChatActionEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_chat_action_handler(self.handle)

    async def _init_filter(self, event: ChatActionEventDTO):
        await super()._init_filter(event)
        if event.only_self and self._client._current_user.id not in event.user_ids:
            raise ExitControllerException

    async def handle(self, event: ChatActionEventDTO):
        await super().handle(event)
        logger.info(
            f"Chat Action event:\n" +
            InfoBuilder.build_message_info_by_chat_action(event)
        )

    @Controller.handle_decorator
    async def join_chat_pipeline_handle(self, event: ChatActionEventDTO):
        await super().handle(event)
        if not event.user_joined and not event.user_added:
            return
        await self._join_chat_handle(self, event.telegram_event)
        await self._create_ratings_on_join_chat_handle(self, event.telegram_event)

    @Controller.handle_decorator
    async def _join_chat_handle(self, event):
        await super().handle(event)
        await self.run_handler(event, JoinChatHandler)

    @Controller.handle_decorator
    async def _create_ratings_on_join_chat_handle(self, event):
        await super().handle(event)
        await self.run_handler(event, CreateRatingsOnJoinChatHandler)


class CommandController(MessageController):
    _event_class = CommandEventDTO
    PREFIX = '/'

    async def _init_filter(self, event: CommandEventDTO):
        await super()._init_filter(event)
        if event.message.text:
            args = event.message.text.split(' ')
            command = args[0].replace(f'@{self._client._current_user.username}', '').replace(self.PREFIX, '', 1)
            if args[0].startswith(self.PREFIX) and command in event.command_names:
                args.pop(0)
                event.args = args
                event.command = command
                return
        raise ExitControllerException

    @Controller.handle_decorator
    async def start_handle(self, event: CommandEventDTO):
        event.command_names = ['start']
        await super().handle(event)
        await self.run_handler(event, StartCommandHandler)

    @Controller.handle_decorator
    async def ping_handle(self, event: CommandEventDTO):
        event.command_names = ['ping']
        event.debug = True
        await super().handle(event)
        await self.run_handler(event, PingCommandHandler)

    @Controller.handle_decorator
    async def entity_info_handle(self, event: CommandEventDTO):
        event.command_names = ['entity']
        event.debug = True
        await super().handle(event)
        await self.run_handler(event, EntityInfoCommandHandler)

    @Controller.handle_decorator
    async def about_handle(self, event: CommandEventDTO):
        event.command_names = ['about']
        await super().handle(event)
        await self.run_handler(event, AboutInfoCommandHandler)

    @Controller.handle_decorator
    async def role_settings_handle(self, event: CommandEventDTO):
        event.command_names = ['roles']
        event.area = event.ONLY_CHAT
        await super().handle(event)
        await self.run_handler(event, RolesSettingsCommandHandler)

    @Controller.handle_decorator
    async def ratings_settings_handle(self, event: CommandEventDTO):
        event.command_names = ['ratings']
        event.area = event.ONLY_CHAT
        await super().handle(event)
        await self.run_handler(event, RatingsSettingsCommandHandler)

    @Controller.handle_decorator
    async def ratings_handle(self, event: CommandEventDTO):
        event.command_names = [
            RatingCommandHandler.PIDOR_COMMAND, RatingCommandHandler.CHAD_COMMAND,
            RatingCommandHandler.PIDOR_MONTH_COMMAND, RatingCommandHandler.CHAD_MONTH_COMMAND,
        ]
        event.area = event.ONLY_CHAT
        await super().handle(event)
        self.set_wait(event.chat.id, True)
        await self.run_handler(event, RatingCommandHandler)
        self.set_wait(event.chat.id, False)

    @Controller.handle_decorator
    async def ratings_stats_handle(self, event: CommandEventDTO):
        event.command_names = [
            StatRatingCommandHandler.PIDOR_STAT_COMMAND, StatRatingCommandHandler.CHAD_STAT_COMMAND,
            StatRatingCommandHandler.PIDOR_MONTH_STAT_COMMAND, StatRatingCommandHandler.CHAD_MONTH_STAT_COMMAND,
        ]
        await super().handle(event)
        event.area = event.ONLY_CHAT
        await self.run_handler(event, StatRatingCommandHandler)


class WatcherController(MessageController):
    _event_class = WatcherEventDTO

    async def _init_filter(self, event: WatcherEventDTO):
        await super()._init_filter(event)
        if event.message.text.startswith(CommandController.PREFIX) and '@' not in event.message.text:
            raise ExitControllerException

    @Controller.handle_decorator
    async def mention_handle(self, event: WatcherEventDTO):
        await super().handle(event)
        if re.search(r"(\s+|^)@([^\s]+)", event.message.text):
            await self.run_handler(event, MentionWatcherHandler)
