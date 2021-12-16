# !/usr/bin/env python
import json

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
        logger.info(f"Start handle {self.__class__.__name__}")


class MessageHandler(Handler):

    def listen(self):
        self._client.add_messages_handler(self.handle)
        super().listen()

    async def handle(self, event):
        await super().handle(event)

        match event.chat.__class__.__name__:
            case 'Chat' | 'Channel':
                chat_info = {
                    'id': event.chat_id,
                    'title': event.chat.title,
                    'type': event.chat.__class__.__name__,
                    'sender': {
                        'id': event.sender.id,
                        'username': event.sender.username,
                    }
                }
            case 'User':
                chat_info = {
                    'id': event.chat_id,
                    'username': event.chat.username,
                    'type': event.chat.__class__.__name__,
                }
            case _:
                chat_info = None

        data_info = {
            'chat': chat_info,
            'text': event.message.text,
        }
        logger.info(f"Message event:\n{json.dumps(data_info, sort_keys=False, indent=2)}")
        self.entity = await self._client.get_entity(event.chat_id)
        if self.entity and not event.message.out:
            return True
        else:
            return False
