# !/usr/bin/env python

from random import randint
from time import sleep

import click
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName

from fsb.config import config
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
    """Sending a dude message to chats"""

    sticker_set_name = config.dude.sticker_set_name
    stickers_ids = config.dude.sticker_set_documents_ids

    if sticker_set_name and stickers_ids:
        sticker_set = await client.request(GetStickerSetRequest(InputStickerSetShortName(sticker_set_name)))
        stickers = [sticker for sticker in sticker_set.documents if sticker.id in stickers_ids]
        message = stickers[randint(0, len(stickers) - 1)]
        is_file = True
    else:
        message = 'It is Wednesday, my dudes!'
        is_file = False

    for chat in Chat.select().where(Chat.dude):
        await client.send_message(chat.telegram_id, message, is_file=is_file)
        sleep(1)
