# !/usr/bin/env python

from time import sleep

import click

from fsb.console import client, coro
from fsb.db.models import Chat


@click.command('broadcast-message')
@click.argument('text', type=str, default='')
@coro
async def broadcast_message(text):
    """Sending a message to all chats"""

    if not text:
        return

    for chat in Chat.select():
        await client.send_message(chat.telegram_id, text)
        sleep(1)


@click.command('dude-broadcast')
@coro
async def dude_broadcast():
    """Sending a dude message to all chats"""

    for chat in Chat.select().where(Chat.dude):
        await client.send_message(chat.telegram_id, '', is_file=True)
        sleep(1)
