# !/usr/bin/env python

from asyncio.exceptions import TimeoutError

from inflection import underscore
from telethon import events
from telethon.tl.custom.button import Button

from fsb.db.models import Chat
from fsb.db.models import CronJob
from fsb.errors import ConversationTimeoutError
from fsb.errors import InputValueError
from fsb.events.cron import (
    CronQueryEvent, GeneralMenuCronEvent, ListCronEvent, MenuCronEvent, DeleteCronEvent, ChangeCronEvent,
    ActiveToggleCronEvent
)
from fsb.handlers import CommandHandler, MenuHandler
from fsb.helpers import Helper
from fsb.services import CronService


class CronSettingsCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        text, buttons = GeneralMenuCronEvent.get_message_and_buttons(self.sender.id)
        await self.client.send_message(self.chat, text, buttons=buttons)


class CronSettingsQueryHandler(MenuHandler):
    INPUT_TIMEOUT = 300

    def __init__(self, event, client):
        super().__init__(event, client)
        self.cron_service = CronService(client)

    async def run(self):
        await super().run()

        if not isinstance(self.query_event, CronQueryEvent):
            return

        query_event_type = underscore(self.query_event.__class__.__name__.replace('CronEvent', ''))
        action = getattr(self, 'action_' + query_event_type)

        if action:
            await action()

    async def action_general_menu(self):
        text, buttons = GeneralMenuCronEvent.get_message_and_buttons(self.sender.id)
        await self.menu_message.edit(text, buttons=buttons)

    async def get_cron_job_params(self, conv, change: bool = False):
        hint = ' ("-" чтоб оставить старое)' if change else ''

        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.chat, from_users=self.sender.id),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи имя задачи' + hint)
        response_event = await response
        name = response_event.message.text

        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.chat, from_users=self.sender.id),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи сообщение для отправки' + hint)
        response_event = await response
        message = response_event.message.text

        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.chat, from_users=self.sender.id),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи расписание' + hint +
                                """
(как в crontab)

* * * * *
| | | | |
| | | | ----- день недели (0—7) (воскресенье = 0 или 7)
| | | ------- месяц (1—12)
| | --------- день месяца (1—31)
| ----------- час (0—23)
------------- минута (0—59)
""")
        response_event = await response
        schedule = response_event.message.text

        chat = Chat.get_by_telegram_id(self.chat.id)

        if CronJob.get_or_none(CronJob.chat == chat, CronJob.name == name):
            return None
        else:
            return name, chat, message, schedule

    async def action_create(self):
        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_cron_job_params(conv)

                if params:
                    name, chat, message, schedule = params
                    await conv.send_message(f"Создана задача: {name}")
                    cron_job = await self.cron_service.add_cron_job(name, chat, message, schedule)
                else:
                    await conv.send_message("Задача с таким именем уже существует")
                    return

                self.query_event.cron_job_id = cron_job.id
                await self.action_menu(True)
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

    async def action_list(self, new_message: bool = False):
        chat = Chat.get_by_telegram_id(self.chat.id)
        cron_jobs = CronJob.find_by_chat(chat)
        buttons = []

        for cron_job in cron_jobs:
            buttons.append((
                f"{cron_job.name}",
                MenuCronEvent(self.sender.id, cron_job.id).save_get_id()
            ))

        buttons = Helper.make_buttons_layout(buttons, (
            "<< В меню планировщика",
            GeneralMenuCronEvent(self.sender.id).save_get_id()
        ))
        text = "Список задач:"

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_menu(self, new_message: bool = False):
        cron_job = self.query_event.get_cron_job()
        text = f"Меню задачи **{cron_job.name}**:\n  Сообщение: {cron_job.message}\n  Расписание: {cron_job.schedule}"
        active_text = "Отключить" if cron_job.active else "Включить"

        buttons = [
            [
                Button.inline(active_text, ActiveToggleCronEvent(self.sender.id, cron_job.id).save_get_id()),
            ],
            [
                Button.inline('Изменить', ChangeCronEvent(self.sender.id, cron_job.id).save_get_id()),
                Button.inline('Удалить', DeleteCronEvent(self.sender.id, cron_job.id).save_get_id()),
            ],
            [
                Button.inline('<< К списку задач', ListCronEvent(self.sender.id).save_get_id())
            ],
        ]

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_active_toggle(self):
        cron_job = self.query_event.get_cron_job()

        if cron_job.active:
            self.cron_service.disable_cron(cron_job=cron_job)
        else:
            await self.cron_service.enable_cron(cron_job=cron_job)

        await self.action_menu()

    async def action_delete(self):
        cron_job = self.query_event.get_cron_job()
        self.cron_service.remove_cron_job(cron_job=cron_job)
        await self.client.send_message(self.chat, f"Удалена задача: {cron_job.name}")
        await self.action_list()

    async def action_change(self):
        cron_job = self.query_event.get_cron_job()

        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_cron_job_params(conv, True)

                if params:
                    name, chat, message, schedule = params
                    cron_job.name = cron_job.name if name == '-' else name
                    cron_job.message = cron_job.message if message == '-' else message
                    cron_job.schedule = cron_job.schedule if schedule == '-' else schedule
                    cron_job.save()
                    await conv.send_message(f"Изменена задача {cron_job.name}")
                else:
                    await conv.send_message("Такая роль уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

        await self.action_menu(True)

    async def action_truncate(self):
        pass
