# !/usr/bin/env python
from fsb import logger
from fsb.telegram.client import TelegramApiClient


class Handler:

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._loop = client.loop
        self.entity = None

    def listen(self):
        logger.info(f"Add handler: {self.__class__.__name__}")

    async def handle(self, event):
        pass


class MessageHandler(Handler):

    def listen(self):
        self._client.add_messages_handler(self.handle)
        super().listen()

    async def handle(self, event):
        self.entity = await self._client.get_entity(event.chat_id)
        if self.entity and not event.message.out:
            return True
        else:
            return False
