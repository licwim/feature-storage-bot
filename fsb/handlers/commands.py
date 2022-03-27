# !/usr/bin/env python

from telethon.tl.functions.users import GetFullUserRequest

from fsb.error import ExitHandlerException
from fsb.handlers import Handler
from fsb.handlers import MessageHandler
from fsb.helpers import InfoBuilder
from fsb.telegram.client import TelegramApiClient


class BaseCommand(MessageHandler):
    def __init__(self, client: TelegramApiClient, name: str):
        super().__init__(client)
        self.name = name
        self.args = []

    async def handle(self, event):
        args = event.message.text.split(' ')
        acceptable_commands = [
            f"/{self.name}",
            f"/{self.name}@{self._client._current_user.username}",
        ]
        if args[0] not in acceptable_commands:
            raise ExitHandlerException
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
