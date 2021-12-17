# !/usr/bin/env python

import re

from . import MessageHandler, Handler
from ..error import ExitHandlerException
from ..telegram.client import TelegramApiClient


class BaseWatcher(MessageHandler):

    def __init__(self, client: TelegramApiClient, filter: callable):
        super().__init__(client)
        self._filter = filter

    async def handle(self, event):
        if event.message.text.startswith('/'):
            raise ExitHandlerException(self._handler_name, "Is command")
        elif not self._filter(event):
            raise ExitHandlerException(self._handler_name, "Filtered out")
        await super().handle(event)


class MentionWatcher(BaseWatcher):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, self.filter)

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        members = await self._client.get_dialog_members(self.entity)
        members_usernames = [member.username for member in members]
        members_usernames.remove(event.sender.username)
        mention = re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text).group(2)

        if mention == 'all':
            await self._client.send_message(
                self.entity,
                ' '.join([f"@{username}" for username in members_usernames]),
                event.message
            )

    def filter(self, event):
        if re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text):
            return True
        else:
            return False
