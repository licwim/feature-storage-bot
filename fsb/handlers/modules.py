# !/usr/bin/env python

from inflection import underscore
from peewee import DoesNotExist

from fsb.db.models import Module, ChatModule, Chat
from fsb.events.modules import ModuleQueryEvent, GeneralMenuModuleEvent
from fsb.handlers import MenuHandler, CommandHandler
from fsb.helpers import Helper


class ModulesSettingsQueryHandler(MenuHandler):
    async def run(self):
        await super().run()

        if not isinstance(self.query_event, ModuleQueryEvent):
            return

        query_event_type = underscore(self.query_event.__class__.__name__.replace('ModuleEvent', ''))
        action = getattr(self, 'action_' + query_event_type)

        if action:
            await action()

    async def action_general_menu(self, new_message: bool = False):
        chat = self.query_event.get_chat()

        try:
            modules_names = [chat_module.module_id for chat_module in ChatModule.select().where(ChatModule.chat == chat)]
        except DoesNotExist:
            modules_names = []

        message, buttons = GeneralMenuModuleEvent.get_message_and_buttons(self.sender.id, chat.id, modules_names)

        if new_message:
            await self.client.send_message(self.chat, message, buttons=buttons)
        else:
            await self.menu_message.edit(message, buttons=buttons)

    async def action_enable(self):
        chat = self.query_event.get_chat()
        module_name = self.query_event.module_id

        chat.enable_module(module_name)
        await self.action_general_menu()

    async def action_disable(self):
        chat = self.query_event.get_chat()
        module_name = self.query_event.module_id

        chat.disable_module(module_name)
        await self.action_general_menu()


class ModulesSettingsCommandHandler(CommandHandler):
    async def run(self):
        await super().run()

        chat = Chat.get_by_telegram_id(self.chat.id)

        try:
            modules_names = [chat_module.module_id for chat_module in ChatModule.select().where(ChatModule.chat == chat)]
        except DoesNotExist:
            modules_names = []

        message, buttons = GeneralMenuModuleEvent.get_message_and_buttons(self.sender.id, chat.id, modules_names)

        await self.client.send_message(self.chat, message, buttons=buttons)
