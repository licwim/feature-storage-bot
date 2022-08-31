# !/usr/bin/env python

from fsb.db.models import Chat, User, Member
from fsb.handlers import ChatActionHandler
from fsb.helpers import Helper


class JoinChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()
        chat = Chat.get_or_create(
            telegram_id=self.chat.id,
            defaults={
                'name': self.chat.title,
                'type': Chat.get_chat_type(self.chat)
            }
        )[0]

        for tg_member in await self.client.get_dialog_members(self.chat):
            user = User.get_or_create(
                telegram_id=tg_member.id,
                defaults={
                    'name': Helper.make_member_name(tg_member, with_username=False),
                    'nickname': tg_member.username
                }
            )[0]
            Member.get_or_create(chat=chat, user=user)
