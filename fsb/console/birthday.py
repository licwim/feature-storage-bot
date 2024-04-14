# !/usr/bin/env python

from time import sleep

import click

from fsb.console import client, coro
from fsb.db.models import Chat
from fsb.services import BirthdayService


@click.group('birthday')
def birthday():
    """Birthday commands"""
    pass


@click.command('congratulation')
@coro
async def congratulation():
    """Sending a birthday message to chats"""

    birthday_service = BirthdayService(client)

    for chat in Chat.select().where(Chat.birthday):
        await birthday_service.send_message(chat)
        sleep(1)


birthday.add_command(congratulation)
