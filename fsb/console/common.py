# !/usr/bin/env python

import click
from time import sleep

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
