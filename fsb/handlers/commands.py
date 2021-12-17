# !/usr/bin/env python

from fsb.telegram.client import TelegramApiClient
from . import MessageHandler, Handler
from ..error import ExitHandlerException
from ..helpers import InfoBuilder


class BaseCommand(MessageHandler):

    def __init__(self, client: TelegramApiClient, name: str):
        super().__init__(client)
        self.name = name
        self.args = []

    async def handle(self, event):
        args = event.message.text.split(' ')
        if args[0] != f"/{self.name}":
            raise ExitHandlerException(self._handler_name, "Unsuited command")
        args.pop(0)
        self.args = args
        await super().handle(event)


class StartCommand(BaseCommand):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'start')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        await self._client.send_message(self.entity, "Ну дарова!")


class EchoCommand(BaseCommand):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'echo')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        text = ' '.join(self.args)
        if text:
            await self._client.send_message(self.entity, text)


class EntityInfoCommand(BaseCommand):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'entity-info')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        self.args = ['this'] if not self.args else self.args
        for entity_uid in self.args:
            entity_uid = int(entity_uid) if entity_uid.isnumeric() else entity_uid
            entity = event.chat if entity_uid == 'this' else await self._client.get_entity(entity_uid)
            await self._client.send_message(self.entity, InfoBuilder.build_entity_info(entity))
