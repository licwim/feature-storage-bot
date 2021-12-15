# !/usr/bin/env python

import re

from fsb.handlers import MessageHandler
from .. import logger
from ..telegram.client import TelegramApiClient


class BaseWatcher(MessageHandler):

    def __init__(self, client: TelegramApiClient, filter: callable):
        super().__init__(client)
        self._filter = filter

    async def handle(self, event):
        if self._filter(event) and not event.message.text.startswith('/') and await super().handle(event):
            return True
        else:
            return False


class MentionWatcher(BaseWatcher):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, self.filter)

    async def handle(self, event):
        try:
            if not await super().handle(event):
                return

            members = await self._client.get_dialog_members(self.entity)
            members_usernames = [member.username for member in members]
            mention = re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text).group(2)

            if mention == 'all':
                await self._client.send_message(
                    self.entity,
                    ' '.join([f"@{username}" for username in members_usernames]),
                    event.message
                )
        except AttributeError as ex:
            logger.error(ex.args)

    def filter(self, event):
        if re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text):
            return True
        else:
            return False
