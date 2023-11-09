# !/usr/bin/env python

from fsb.db.models import Chat
from fsb.handlers import ChatActionHandler
from fsb.services import ChatService


class JoinChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()

        repository = ChatService(self.client)
        await repository.create_chat(event=self.telegram_event)


class NewTitleChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()

        chat = Chat.get_by_telegram_id(self.chat.id)
        chat.name = self.new_title
        chat.save()
