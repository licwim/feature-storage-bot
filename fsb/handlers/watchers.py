# !/usr/bin/env python

import re

from . import Handler
from . import MessageHandler
from ..error import ExitHandlerException
from ..telegram.client import TelegramApiClient


class BaseWatcher(MessageHandler):

    def __init__(self, client: TelegramApiClient, filter: callable):
        super().__init__(client)
        self._filter = filter

    async def handle(self, event):
        if event.message.text.startswith('/') or not self._filter(event):
            raise ExitHandlerException
        await super().handle(event)


class MentionWatcher(BaseWatcher):

    UNKNOWN_NAME_REPLACEMENT = "ты"

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, self.filter)

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        members = await self._client.get_dialog_members(self.entity)
        members.remove(event.sender)
        mention = re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text).group(2)

        match mention:
            case 'all':
                result_mention = self._all(members)
            case 'allkek' | 'allrank':
                result_mention = self._all(members, True)
            case _:
                result_mention = None

        if result_mention:
            await self._client.send_message(
                self.entity,
                result_mention,
                event.message
            )

    @staticmethod
    def _all(members, rank_mention: bool = False):
        mentions = []
        for member in members:
            if rank_mention and member.participant.rank:
                mentions.append(f"[{member.participant.rank}](tg://user?id={str(member.id)})")
            elif member.username:
                mentions.append('@' + member.username)
            else:
                first_name = member.first_name if member.first_name else ''
                last_name = member.last_name if member.first_name else ''
                if first_name or last_name:
                    member_name = f"{first_name} {last_name}"
                else:
                    member_name = MentionWatcher.UNKNOWN_NAME_REPLACEMENT
                mentions.append(f"[{member_name}](tg://user?id={str(member.id)})")

        return ' '.join(mentions)

    @staticmethod
    def filter(event):
        if re.search(r"(\s+|^)@([^\s]+)(\s+|$)", event.message.text):
            return True
        else:
            return False
