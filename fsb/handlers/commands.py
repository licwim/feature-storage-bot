# !/usr/bin/env python

from telethon.tl.functions.users import GetFullUserRequest

from fsb.db.models import Chat
from fsb.handlers import CommandHandler
from fsb.helpers import InfoBuilder
from fsb.services import ChatService, RatingService


class StartCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        await self.client.send_message(self.chat, 'OK')


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


class WednesdayCommandHandler(CommandHandler):
    MESSAGE_PATTERN = 'Дюдсовая среда теперь {state}!'

    async def run(self):
        await super().run()
        chat = Chat.get_by_telegram_id(self.chat.id)
        chat.dude = not chat.dude
        chat.save()

        if chat.dude:
            message = self.MESSAGE_PATTERN.format(state='ВКЛЮЧЕНА')
        else:
            message = self.MESSAGE_PATTERN.format(state='ВЫКЛЮЧЕНА')

        await self.client.send_message(self.chat, message)
