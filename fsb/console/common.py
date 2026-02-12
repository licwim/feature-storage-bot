# !/usr/bin/env python

from random import randint
from time import sleep

import click
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName, DocumentAttributeVideo

from fsb.config import config
from fsb.console import client, coro
from fsb.db.models import Chat, Module
from fsb.services import FoolService


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

    fool_service = FoolService(client)

    for chat in Chat.with_enabled_module(Module.MODULE_DUDE):
        if config.FOOL_DAY:
            await fool_service.send_message(chat.telegram_id)
        else:
            await client.send_message(chat.telegram_id, message, is_file=is_file)

        sleep(1)


@click.command('new-year-broadcast')
@coro
async def new_year_broadcast():
    """Sending New year message to chats"""
    film = None
    gif = None

    if config.content.new_year_film:
        film = await client._client.upload_file(config.content.new_year_film, file_name='Happy New Year.mp4')

    if config.content.new_year_gif:
        gif = await client._client.upload_file(config.content.new_year_gif, file_name='Happy New Year.gif')

    for chat in Chat.with_enabled_module(Module.MODULE_HAPPY_NEW_YEAR):
        if gif:
            await client.send_message(chat.telegram_id, gif, is_file=True)
        else:
            await client.send_message(chat.telegram_id, 'Happy New Year!')
        sleep(1)

        if film:
            await client.send_message(chat.telegram_id, film, is_file=True, caption='Новогодно-короткометражный подгон', attributes=(DocumentAttributeVideo(0, 426, 240),))
