# !/usr/bin/env python

from random import randint
from time import sleep

import click
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName, DocumentAttributeVideo

from fsb.config import config
from fsb.console import client, coro
from fsb.db.models import Chat


@click.command('send-message')
@click.argument('text', type=str, default='')
@click.argument('chats_ids', type=str, default='')
@coro
async def send_message(text, chats):
    """Sending a message to chats"""

    if not text:
        return

    if chats:
        chats = [chat_id.strip() for chat_id in chats.split(',')]
        query = Chat.select()

        if 'all' not in chats:
            chats_ids = []

            for chat in chats:
                match chat:
                    case 'user':
                        query.orwhere(Chat.type == Chat.USER_TYPE)
                    case 'channel':
                        query.orwhere(Chat.type.in_([Chat.CHAT_TYPE, Chat.CHANNEL_TYPE]))
                    case _:
                        if chat.isnumeric():
                            chats_ids.append(int(chat))
                        else:
                            raise ValueError(f'Invalid chat argument: "{chat}"')

            if chats_ids:
                query.orwhere(Chat.id.in_(chats_ids))
    else:
        return

    for chat in query:
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


@click.command('new-year-broadcast')
@coro
async def new_year_broadcast():
    """Sending New year message to chats"""
    film = None

    if config.content.shrek_new_year_film:
        film = await client._client.upload_file(config.content.shrek_new_year_film, file_name='Happy New Year.mp4')

    for chat in Chat.select().where(Chat.happy_new_year):
        if config.content.shrek_new_year_gif:
            await client.send_message(chat.telegram_id, config.content.shrek_new_year_gif, is_file=True)
        else:
            await client.send_message(chat.telegram_id, 'Happy New Year!', is_file=False)
        sleep(1)

        if film:
            await client._client.send_file(chat.telegram_id, film, attributes=(DocumentAttributeVideo(0, 426, 240),))
