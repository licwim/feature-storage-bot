# !/usr/bin/env python

from typing import Union
from telethon.tl.functions.users import GetFullUserRequest

from fsb.error import ExitHandlerException
from fsb.handlers import Handler
from fsb.handlers import MessageHandler
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class BaseCommand(MessageHandler):
    def __init__(self, client: TelegramApiClient, names: Union[str, list]):
        super().__init__(client)
        if isinstance(names, str):
            self.names = [names]
        else:
            self.names = names
        self.command = None
        self.args = []

    async def handle(self, event):
        args = event.message.text.split(' ')
        command = args[0].replace(f'@{self._client._current_user.username}', '')
        if command not in self.names:
            raise ExitHandlerException
        args.pop(0)
        self.args = args
        self.command = command
        await super().handle(event)


class StartCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'start')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        await self._client.send_message(self.entity, "Ну дарова!")


class PingCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'ping')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        await self._client.send_message(self.entity, 'pong')


class EntityInfoCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'entityinfo')
        self._debug = True

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        self.args = ['this'] if not self.args else self.args
        entity_uid = ' '.join(self.args)
        try:
            entity_uid = int(entity_uid)
        except ValueError:
            pass
        entity = event.chat if entity_uid == 'this' else await self._client.get_entity(entity_uid)
        await self._client.send_message(
            self.entity,
            InfoBuilder.build_entity_info(entity, view_type=InfoBuilder.YAML)
        )


class AboutInfoCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'about')

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)

        bot = await self._client.request(GetFullUserRequest(self._client._current_user))
        await self._client.send_message(self.entity, InfoBuilder.build_about_info(bot))
