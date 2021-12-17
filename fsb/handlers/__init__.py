# !/usr/bin/env python
import json

from fsb import logger
from fsb.error import ExitHandlerException
from fsb.telegram.client import TelegramApiClient


class Handler:

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._loop = client.loop
        self.entity = None
        self._handler_name = self.__class__.__name__

    def listen(self):
        logger.info(f"Add handler: {self._handler_name}")

    async def handle(self, event):
        logger.info(f"Start handle {self._handler_name}")

    def handle_decorator(callback: callable):
        async def handle(self, event):
            try:
                await callback(self, event)
            except ExitHandlerException as ex:
                # @todo Раскоментить этот лог, когда в переменные окружения будет добавлен dev_mode.
                # logger.warning(ex.message)
                pass
            except AttributeError as ex:
                logger.exception(ex.args)
        return handle
    handle_decorator = staticmethod(handle_decorator)


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

        if not self.entity:
            raise ExitHandlerException(self._handler_name, f"Entity not found by chat id: {event.chat_id}")
        elif event.message.out:
            raise ExitHandlerException(self._handler_name, "Out message")
