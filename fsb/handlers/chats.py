# !/usr/bin/env python

from fsb.handlers import ChatActionHandler
from fsb.services import Repository


class JoinChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()

        repository = Repository(self.client)
        await repository.create_chat(event=self.telegram_event)
