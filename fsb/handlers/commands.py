# !/usr/bin/env python

from telethon.tl.functions.users import GetFullUserRequest

from fsb.handlers import CommandHandler
from fsb.helpers import InfoBuilder
from fsb.services import ChatService, RatingService


class StartCommandHandler(CommandHandler):
    async def run(self):
        await super().run()

        chat_service = ChatService(self.client)
        rating_service = RatingService(self.client)
        chat = await chat_service.create_chat(event=self.telegram_event, update=True)
        rating_service.create_system_ratings(chat)


class PingCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        await self.client.send_message(self.chat, 'pong')


class EntityInfoCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        self.args = ['this'] if not self.args else self.args
        entity_uid = ' '.join(self.args)
        try:
            entity_uid = int(entity_uid)
        except ValueError:
            pass
        entity = self.chat if entity_uid == 'this' else await self.client.get_entity(entity_uid)
        await self.client.send_message(
            self.chat,
            InfoBuilder.build_entity_info(entity, view_type=InfoBuilder.YAML)
        )


class AboutInfoCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        bot = await self.client.request(GetFullUserRequest(self.client._current_user))
        await self.client.send_message(self.chat, InfoBuilder.build_about_info(bot))

