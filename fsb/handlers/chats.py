# !/usr/bin/env python

from fsb.handlers import ChatActionHandler
from fsb.services import ChatService


class JoinChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()

        repository = ChatService(self.client)
        await repository.create_chat(event=self.telegram_event)
