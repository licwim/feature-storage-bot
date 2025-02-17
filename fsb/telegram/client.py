# !/usr/bin/env python

import json
import logging
from time import sleep, time
from typing import Any, Union

from telethon import TelegramClient, errors, functions
from telethon.events.common import EventBuilder
from telethon.tl.types import (
    Message,
    InputPeerUser, InputPeerChat, InputPeerChannel,
    InputChannel, InputUser
)

from fsb.config import config
from fsb.db.models import User, Chat
from fsb.errors import (
    DisconnectFailedError
)
from fsb.helpers import InfoBuilder


class TelegramApiClient:
    MAX_RELOGIN_COUNT = 3
    DISCONNECT_TIMEOUT = 15
    PARTICIPANTS_LIMIT = 200
    PARTICIPANTS_CACHE_TIME = 60

    def __init__(self, name: str = None, cli: bool = False):
        self.name = name
        self._client = TelegramClient(name, config.API_ID, config.API_HASH)
        self.loop = self._client.loop
        self._relogin_count = 0
        self._current_user = None
        self.cli = cli
        self.logger = logging.getLogger('main')

        self._chat_members_cache = {}

    def start(self):
        self._client.run_until_disconnected()

    async def connect(self, is_bot: bool = False):
        await self._client.connect()
        bot_token = None if await self._client.is_user_authorized() or not is_bot else config.BOT_TOKEN
        await self._client.start(bot_token=bot_token)
        self._current_user = await self._client.get_me()
        self.logger.info(f"Welcome, {self.name}! Telegram Client is connected")

    async def exit(self, logout: bool = False):
        try:
            if logout:
                await self._client.log_out()
            await self._client.disconnect()
            for _ in range(self.MAX_RELOGIN_COUNT):
                if not self._client.is_connected():
                    break
                sleep(1)
            else:
                raise DisconnectFailedError()
        except ConnectionError:
            self.logger.info("Connection error")
        self.logger.info("Logout")

    async def send_message(self, entity, message: Any, reply_to: Message = None, buttons=None, is_file: bool = False, **kwargs):
        try:
            if isinstance(entity, Union[str, int]):
                entity = await self.get_entity(entity)

            if config.FSB_DEV_MODE:
                self.logger.debug(InfoBuilder.build_debug_message_info(entity, message, reply_to))
            elif self.cli:
                self.logger.info(InfoBuilder.build_debug_message_info(entity, message, reply_to))

            new_message = None
            if isinstance(message, str):
                message = message.rstrip('\t \n')
            if message:
                if is_file:
                    new_message = await self._client.send_file(entity=entity, file=message, reply_to=reply_to, buttons=buttons, **kwargs)
                else:
                    new_message = await self._client.send_message(entity=entity, message=message, reply_to=reply_to, buttons=buttons, **kwargs)
            return new_message
        except errors.PeerFloodError as e:
            self.logger.error(f"{entity}: PeerFloodError")
            raise e
        except errors.UsernameInvalidError as e:
            self.logger.error(f"{entity}: UsernameInvalidError")
            raise e
        except ValueError as e:
            self.logger.error(f"{entity}: ValueError")
            raise e

    async def get_entity(self, uid: Union[str, int], with_full: bool = True):
        entity = None
        try:
            if uid:
                entity = await self._client.get_entity(uid)
        except ValueError:
            if with_full:
                db_entity = Chat.get_or_none(Chat.telegram_id == uid)
                if not db_entity:
                    db_entity = User.select().where(
                        (User.nickname == uid) | (User.telegram_id == uid)
                    ).get_or_none()

                if db_entity and db_entity.input_peer:
                    metadata = json.loads(db_entity.input_peer)
                    match metadata['_']:
                        case InputPeerUser.__name__:
                            input_peer = InputUser(metadata['user_id'], metadata['access_hash'])
                            await self.request(functions.users.GetFullUserRequest(input_peer))
                        case InputPeerChat.__name__:
                            await self.request(functions.messages.GetFullChatRequest(metadata['chat_id']))
                        case InputPeerChannel.__name__:
                            input_peer = InputChannel(metadata['channel_id'], metadata['access_hash'])
                            await self.request(functions.channels.GetFullChannelRequest(input_peer))

                entity = await self.get_entity(uid, False)
        return entity

    def add_event_handler(self, handler: callable, event: EventBuilder):
        self._client.add_event_handler(handler, event)

    async def request(self, data):
        return await self._client(data)

    async def get_dialog_members(self, entity, with_bot: bool = None, use_cache: bool = True) -> list:
        if isinstance(entity, Union[str, int]):
            entity = await self.get_entity(entity)

        if with_bot is None:
            with_bot = True if config.FSB_DEV_MODE else False
        else:
            with_bot = False

        members_cache = self._chat_members_cache.get(entity.id)
        now = int(time())

        if not use_cache or not members_cache or members_cache['time'] + self.PARTICIPANTS_CACHE_TIME < now:
            members = []

            for member in await self._client.get_participants(entity, aggressive=False, limit=self.PARTICIPANTS_LIMIT):
                if member.username == self._current_user.username or (not with_bot and member.bot):
                    continue
                members.append(member)

            self._chat_members_cache.update({entity.id: {'time': now, 'members': members}})
        else:
            members = members_cache['members']

        return members
