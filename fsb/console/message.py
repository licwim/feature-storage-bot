# !/usr/bin/env python

from datetime import datetime
from time import sleep

import click
from pymorphy3 import MorphAnalyzer

from fsb.console import client, coro
from fsb.db.models import Chat


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
                        query = query.orwhere(Chat.type == Chat.USER_TYPE)
                    case 'channel':
                        query = query.orwhere(Chat.type.in_([Chat.CHAT_TYPE, Chat.CHANNEL_TYPE]))
                    case _:
                        if chat.isnumeric():
                            chats_ids.append(int(chat))
                        else:
                            raise ValueError(f'Invalid chat argument: "{chat}"')

            if chats_ids:
                query = query.where(Chat.id.in_(chats_ids))
    else:
        return

    for chat in query:
        await client.send_message(chat.telegram_id, text)
        sleep(1)


@click.command('send-message')
@click.argument('text', type=str, default='')
@click.argument('chats', type=str, default='')
@coro
async def send_message_command(text, chats):
    await send_message(text, chats)


@click.command('countdown')
@click.argument('text', type=str, default='')
@click.argument('date', type=str, default='')
@click.argument('chats', type=str, default='')
@coro
async def countdown(text, date, chats):
    """Sending a message with countdown to chats"""
    if date:
        now = datetime.now().replace(hour=0, minute=0, second=0)
        date = datetime.fromisoformat(date).replace(hour=0, minute=0, second=0)

        left_days = abs((date - now).days)

        day_word_lexeme = MorphAnalyzer(lang='ru').parse('день')[0]
        day_word = day_word_lexeme.make_agree_with_number(left_days).word

        text = text.format(day_word=day_word, left_days=left_days)

    await send_message(text, chats)
