# !/usr/bin/env python

import inspect
import logging
import re
from asyncio import sleep
from datetime import datetime
from typing import Type

from peewee import DoesNotExist
from telethon.events import NewMessage, CallbackQuery, ChatAction

from fsb.config import config
from fsb.db.models import QueryEvent, Role, Chat, Module
from fsb.errors import ExitControllerException
from fsb.events.common import (
    EventDTO, MessageEventDTO, CallbackQueryEventDTO, MenuEventDTO, ChatActionEventDTO, CommandEventDTO,
    MentionEventDTO
)
from fsb.events.cron import CronQueryEvent
from fsb.events.modules import ModuleQueryEvent
from fsb.events.ratings import RatingQueryEvent
from fsb.events.roles import RoleQueryEvent
from fsb.handlers import Handler, FoolHandler
from fsb.handlers.commands import (
    StartCommandHandler, PingCommandHandler, EntityInfoCommandHandler, AboutInfoCommandHandler
)
from fsb.handlers.cron import CronSettingsCommandHandler, CronSettingsQueryHandler
from fsb.handlers.mentions import AllMentionHandler, CustomMentionHandler
from fsb.handlers.modules import ModulesSettingsCommandHandler, ModulesSettingsQueryHandler
from fsb.handlers.ratings import (
    RatingsSettingsCommandHandler, RatingCommandHandler, StatRatingCommandHandler,
    RatingsSettingsQueryHandler
)
from fsb.handlers.roles import RolesSettingsCommandHandler, RolesSettingsQueryHandler
from fsb.helpers import InfoBuilder, Helper
from fsb.services import ChatService
from fsb.telegram.client import TelegramApiClient


class Controller:
    MAX_WAITING = 60

    _event_class = EventDTO
    _from_bot = False
    _from_user = True

    def __init__(self, client: 'TelegramApiClient'):
        self._client = client
        self._loop = client.loop
        self._controller_name = self.__class__.__name__
        self._waiting_list = {}
        self.logger = logging.getLogger('main')

    def listen(self):
        handle_names = []
        for handle_name, handle in self.get_handle_list():
            self._listen_handle(handle)
            handle_names.append(handle_name.replace('_handle', '', -1))
        self.logger.info(f"Add controller: {self._controller_name} [{', '.join(handle_names)}]")

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

        db_chat = await ChatService(self._client).create_chat(event=event, update=True)

        if not db_chat or db_chat.is_deleted():
            raise ExitControllerException

        self.check_module(event)

        self.logger.info(f"Start controller {self._controller_name}")

    @staticmethod
    def check_module(event, module_name: str = None, raise_exit_exception: bool = True) -> bool:
        module_name = module_name if module_name else event.module_name
        module = Module.get_by_id(module_name)
        result = False
        exception = None

        if not module.active:
            exception = ExitControllerException(sending_message='Модуль "{module_name}" не активен'
                                          .format(module_name=module.get_readable_name()))
        elif not Chat.get_by_telegram_id(event.telegram_event.chat.id).is_enabled_module(module_name):
            exception = ExitControllerException(sending_message='В чате не включен модуль "{module_name}"'
                                          .format(module_name=module.get_readable_name()))
        else:
            result = True

        if exception and raise_exit_exception:
            raise exception

        return result

    @staticmethod
    def handle_decorator(callback: callable):
        async def handle(self, event):
            try:
                event = self._event_class(event)
                await callback(self, event)
            except ExitControllerException as ex:
                if ex.class_name or ex.reason:
                    self.logger.warning(ex.message)

                if ex.sending_message:
                    await self._client.send_message(event.telegram_event.chat.id, ex.sending_message)
            except DoesNotExist as ex:
                self.logger.warning(ex.__class__.__name__.replace(DoesNotExist.__name__, '') + ' does not exist')
            except Exception as ex:
                self.logger.exception(ex.args)
            finally:
                self.stop_wait(event.chat.id)
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

    def _set_wait(self, chat_id: int, value: bool):
        self._waiting_list[chat_id] = value

    def start_wait(self, chat_id: int):
        self._set_wait(chat_id, True)

    def stop_wait(self, chat_id: int):
        if chat_id in self._waiting_list:
            self._set_wait(chat_id, False)

    async def run_handler(self, event: EventDTO, handler_class: Type[Handler]):
        return await handler_class(event, self._client).run()


class MessageController(Controller):
    _event_class = MessageEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_event_handler(handle, NewMessage(forwards=False))

    async def _init_filter(self, event: MessageEventDTO):
        await super()._init_filter(event)
        if (event.debug and event.sender.username not in config.contributors) \
                or (event.message.out and not self._from_bot) or (not event.message.out and not self._from_user):
            raise ExitControllerException

    async def handle(self, event: MessageEventDTO):
        await super().handle(event)
        self.logger.info(
            "Message event:\n" +
            InfoBuilder.build_message_info_by_message_event(event)
        )


class CallbackQueryController(Controller):
    _event_class = CallbackQueryEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_event_handler(handle, CallbackQuery())

    async def _init_filter(self, event: CallbackQueryEventDTO):
        await super()._init_filter(event)

        query_event = QueryEvent.find_and_create(int(event.data))

        if not isinstance(query_event, event.query_event_class):
            raise ExitControllerException

        event.query_event = query_event

    async def handle(self, event: CallbackQueryEventDTO):
        await super().handle(event)

        event.query_event.last_usage_date = datetime.now()
        event.query_event.save()

        self.logger.info(
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
        event.module_name = Module.MODULE_ROLES
        await super().handle(event)
        await self.run_handler(event, RolesSettingsQueryHandler)

    @Controller.handle_decorator
    async def ratings_menu_handle(self, event: MenuEventDTO):
        event.area = event.ONLY_CHAT
        event.query_event_class = RatingQueryEvent
        event.module_name = Module.MODULE_RATINGS
        await super().handle(event)
        await self.run_handler(event, RatingsSettingsQueryHandler)

    @Controller.handle_decorator
    async def modules_menu_handle(self, event: MenuEventDTO):
        event.query_event_class = ModuleQueryEvent

        await super().handle(event)
        await self.run_handler(event, ModulesSettingsQueryHandler)

    @Controller.handle_decorator
    async def cron_menu_handle(self, event: MenuEventDTO):
        event.query_event_class = CronQueryEvent
        event.module_name = Module.MODULE_CRON

        await super().handle(event)
        await self.run_handler(event, CronSettingsQueryHandler)


class ChatActionController(Controller):
    _event_class = ChatActionEventDTO

    def _listen_handle(self, handle: callable):
        self._client.add_event_handler(handle, ChatAction())

    @Controller.handle_decorator
    async def chat_action_handle(self, event: ChatActionEventDTO):
        await super().handle(event)
        self.logger.info(
            f"Chat Action event:\n" +
            InfoBuilder.build_message_info_by_chat_action(event)
        )


class CommandController(MessageController):
    _event_class = CommandEventDTO
    PREFIX = '/'
    _from_bot = True

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
        event.debug = False

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
        event.module_name = Module.MODULE_ROLES

        await super().handle(event)
        await self.run_handler(event, RolesSettingsCommandHandler)

    @Controller.handle_decorator
    async def ratings_settings_handle(self, event: CommandEventDTO):
        event.command_names = ['ratings']
        event.area = event.ONLY_CHAT
        event.module_name = Module.MODULE_RATINGS

        await super().handle(event)
        await self.run_handler(event, RatingsSettingsCommandHandler)

    @Controller.handle_decorator
    async def ratings_handle(self, event: CommandEventDTO):
        event.command_names = [
            RatingCommandHandler.DAY_COMMAND, RatingCommandHandler.MONTH_COMMAND,
            RatingCommandHandler.YEAR_COMMAND,
        ]
        event.area = event.ONLY_CHAT
        event.module_name = Module.MODULE_RATINGS

        await super().handle(event)
        self.start_wait(event.chat.id)
        await self.run_handler(event, RatingCommandHandler)
        self.stop_wait(event.chat.id)

    @Controller.handle_decorator
    async def ratings_stats_handle(self, event: CommandEventDTO):
        event.command_names = [StatRatingCommandHandler.STAT_COMMAND, StatRatingCommandHandler.STAT_ALL_COMMAND]
        event.area = event.ONLY_CHAT
        event.module_name = Module.MODULE_RATINGS

        await super().handle(event)
        await self.run_handler(event, StatRatingCommandHandler)

    @Controller.handle_decorator
    async def modules_settings_handle(self, event: CommandEventDTO):
        event.command_names = ['modules']

        await super().handle(event)
        await self.run_handler(event, ModulesSettingsCommandHandler)

    @Controller.handle_decorator
    async def cron_settings_handle(self, event: CommandEventDTO):
        event.command_names = ['cron']
        event.module_name = Module.MODULE_CRON

        await super().handle(event)
        await self.run_handler(event, CronSettingsCommandHandler)


class MentionController(MessageController):
    _event_class = MentionEventDTO

    async def _init_filter(self, event: MentionEventDTO):
        await super()._init_filter(event)
        if event.message.text.startswith(CommandController.PREFIX) \
                or not re.search(r"(\s+|^)@([^\s]+)", event.message.text):
            raise ExitControllerException
        event.mentions = [matches[1] for matches in re.findall(r"(\s+|^)@([^\s@]+)", event.message.text)]

    @Controller.handle_decorator
    async def mention_handle(self, event: MentionEventDTO):
        await super().handle(event)

        if self._mention_filter('all', event):
            members_mentions_chunks = await self._all_mention_handle(event)
            messages = ['📣' + ''.join(members_mentions) for members_mentions in members_mentions_chunks]
        else:
            members_mentions_chunks = await self._custom_mention_handle(event)
            messages = [', '.join(members_mentions) for members_mentions in members_mentions_chunks]

        for message in messages:
            await self._client.send_message(
                event.chat,
                message,
                event.message
            )

    def _mention_filter(self, mentions: list|str, event: MentionEventDTO):
        mentions = [mentions] if isinstance(mentions, str) else mentions

        for mention in mentions:
            if mention in event.mentions:
                return True
        return False

    async def _all_mention_handle(self, event: MentionEventDTO):
        mentions = await self.run_handler(event, AllMentionHandler)

        return Helper.split_chunks(mentions, AllMentionHandler.MESSAGE_MENTION_LIMIT)

    async def _custom_mention_handle(self, event: MentionEventDTO):
        if not self.check_module(event, Module.MODULE_ROLES, False):
            return []

        chat = Chat.get_by_telegram_id(event.chat.id)

        members_mentions = []
        mention_list = [role.nickname for role in Role.find_by_chat(chat)]

        if self._mention_filter(mention_list, event):
            members_mentions = await self.run_handler(event, CustomMentionHandler)

        return Helper.split_chunks(members_mentions, CustomMentionHandler.MESSAGE_MENTION_LIMIT)


class FoolCommandController(CommandController):
    async def run_handler(self, event: EventDTO, handler_class: Type[Handler]):
        return await FoolHandler(event, self._client).run()


class FoolMentionController(MentionController):
    @Controller.handle_decorator
    async def mention_handle(self, event: MentionEventDTO):
        await super().handle(event)
        mention_list = ([role.nickname for role in Role.find_by_chat(Chat.get_by_telegram_id(event.chat.id))]
                        + ['all', 'allrank'])

        if self._mention_filter(mention_list, event):
            return await FoolHandler(event, self._client).run()
