# !/usr/bin/env python

from fsb.telegram.client import TelegramApiClient
from . import MessageHandler


class BaseCommand(MessageHandler):

    def __init__(self, client: TelegramApiClient, name: str):
        super().__init__(client)
        self.name = name

    async def handle(self, event):
        if event.message.text.split(' ')[0] == f"/{self.name}" and await super().handle(event):
            return True
        else:
            return False


class StartCommand(BaseCommand):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'start')

    async def handle(self, event):
        try:
            if not await super().handle(event):
                return

            await self._client.send_message(self.entity, "Ну дарова!")
        except AttributeError as ex:
            print(ex.args)


class EchoCommand(BaseCommand):

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'echo')

    async def handle(self, event):
        try:
            if not await super().handle(event):
                return

            text = event.message.text.replace(f'/{self.name}', '', 1)
            if text:
                await self._client.send_message(self.entity, text)
        except AttributeError as ex:
            print(ex.args)
