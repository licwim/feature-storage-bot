# !/usr/bin/env python

import json
from time import sleep
from typing import Any, Union

from telethon import TelegramClient, errors, events, functions
from telethon.tl.types import (
    Message,
    InputPeerUser, InputPeerChat, InputPeerChannel,
    InputChannel, InputUser
)

from fsb.db.models import User, Chat
from .. import FSB_DEV_MODE
from .. import logger
from ..config import Config
from ..error import (
    DisconnectFailedError
)
from ..helpers import InfoBuilder


class TelegramApiClient:
    MAX_RELOGIN_COUNT = 3
    DISCONNECT_TIMEOUT = 15

    def __init__(self, name: str = None):
        self.name = name
        self._client = TelegramClient(name, Config.api_id, Config.api_hash)
        self.loop = self._client.loop
        self._relogin_count = 0
        self._current_user = None
        self.cli = False

    def start(self):
        self._client.run_until_disconnected()

    async def connect(self, is_bot: bool = False):
        await self._client.connect()
        bot_token = None if await self._client.is_user_authorized() or not is_bot else Config.bot_token
        await self._client.start(bot_token=bot_token)
        self._current_user = await self._client.get_me()
        logger.info(f"Welcome, {self.name}! Telegram Client is connected")

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
            logger.info("Connection error")
        logger.info("Logout")

    async def send_message(self, entity, message: Any, reply_to: Message = None, force: bool = False, buttons=None, is_file: bool = False):
        try:
            if isinstance(entity, Union[str, int]):
                entity = await self.get_entity(entity)

            if FSB_DEV_MODE:
                logger.debug(InfoBuilder.build_debug_message_info(entity, message, reply_to))

                if not force and entity.id not in Config.dev_chats:
                    return None
            elif self.cli:
                logger.info(InfoBuilder.build_debug_message_info(entity, message, reply_to))

            new_message = None
            if isinstance(message, str):
                message = message.rstrip('\t \n')
            if message:
                if is_file:
                    new_message = await self._client.send_file(entity=entity, file=message, reply_to=reply_to, buttons=buttons)
                else:
                    new_message = await self._client.send_message(entity=entity, message=message, reply_to=reply_to, buttons=buttons)
            return new_message
        except errors.PeerFloodError as e:
            logger.error(f"{entity}: PeerFloodError")
            raise e
        except errors.UsernameInvalidError as e:
            logger.error(f"{entity}: UsernameInvalidError")
            raise e
        except ValueError as e:
            logger.error(f"{entity}: ValueError")
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

    def add_message_handler(self, handler: callable, *args, **kwargs):
        if FSB_DEV_MODE:
            blacklist_chats = False
        else:
            blacklist_chats = True
        self._client.add_event_handler(
            handler,
            events.NewMessage(forwards=False, chats=Config.dev_chats, blacklist_chats=blacklist_chats, *args, **kwargs)
        )

    def add_callback_query_handler(self, handler: callable, *args, **kwargs):
        if FSB_DEV_MODE:
            blacklist_chats = False
        else:
            blacklist_chats = True
        self._client.add_event_handler(
            handler,
            events.CallbackQuery(chats=Config.dev_chats, blacklist_chats=blacklist_chats, *args, **kwargs)
        )

    def add_chat_action_handler(self, handler: callable, *args, **kwargs):
        if FSB_DEV_MODE:
            blacklist_chats = False
        else:
            blacklist_chats = True
        self._client.add_event_handler(
            handler,
            events.ChatAction(chats=Config.dev_chats, blacklist_chats=blacklist_chats, *args, **kwargs)
        )

    async def request(self, data):
        return await self._client(data)

    async def get_dialog_members(self, entity, with_bot: bool = False) -> list:
        if isinstance(entity, Union[str, int]):
            entity = await self.get_entity(entity)

        members = []

        for member in await self._client.get_participants(entity):
            if member.username == self._current_user.username or (not with_bot and member.bot):
                continue
            members.append(member)

        return members
