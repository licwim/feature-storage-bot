# !/usr/bin/env python

from fsb.db.models import Chat, User, Member
from fsb.handlers.common import ChatActionHandler, Handler
from fsb.helpers import Helper
from fsb.telegram.client import TelegramApiClient


class JoinChatHandler(ChatActionHandler):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client)

    @Handler.handle_decorator
    async def handle(self, event):
        if not event.user_joined and not event.user_added:
            return
        await super().handle(event)

        chat = Chat.get_or_create(
            telegram_id=self.entity.id,
            defaults={
                'name': self.entity.title,
                'type': Chat.get_chat_type(self.entity)
            }
        )[0]

        for tg_member in await self._client.get_dialog_members(self.entity):
            user = User.get_or_create(
                telegram_id=tg_member.id,
                defaults={
                    'name': Helper.make_member_name(tg_member, with_username=False),
                    'nickname': tg_member.username
                }
            )[0]
            Member.get_or_create(chat=chat, user=user)
