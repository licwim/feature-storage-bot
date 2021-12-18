# !/usr/bin/env python

from time import sleep
from typing import Any
from typing import Union

from telethon import TelegramClient
from telethon import errors
from telethon import events
from telethon.tl.types import Message

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

    async def send_message(self, entity, message: Any, reply_to: Message = None, force: bool = False):
        try:
            if not force and FSB_DEV_MODE:
                await self._send_debug_message(entity, message, reply_to)
                return
            if isinstance(message, str):
                message = message.rstrip('\t \n')
                if message:
                    await self._client.send_message(entity=entity, message=message, reply_to=reply_to)
            else:
                if message:
                    await self._client.send_file(entity=entity, file=message, reply_to=reply_to)
        except errors.PeerFloodError as e:
            logger.info(f"{entity}: PeerFloodError")
            raise e
        except errors.UsernameInvalidError as e:
            logger.info(f"{entity}: UsernameInvalidError")
            raise e
        except ValueError as e:
            logger.info(f"{entity}: ValueError")
            raise e

    async def _send_debug_message(self, entity, message: Any, reply_to: Message = None):
        logger.debug(InfoBuilder.build_debug_message_info(entity, message, reply_to))
        if Config.developer:
            await self.send_message(await self.get_entity(Config.developer), message, reply_to, True)

    async def get_entity(self, uid: Union[str, int]):
        try:
            if not uid:
                raise ValueError
            return await self._client.get_entity(uid)
        except ValueError:
            return None

    def add_messages_handler(self, handler: callable, *args, **kwargs):
        self._client.add_event_handler(
            handler,
            events.NewMessage(*args, **kwargs)
        )

    async def request(self, data):
        return await self._client(data)

    async def get_dialog_members(self, entity, with_bot: bool = False) -> list:
        members = []

        for member in await self._client.get_participants(entity):
            if member.username == self._current_user.username or (not with_bot and member.bot):
                continue
            members.append(member)

        return members
