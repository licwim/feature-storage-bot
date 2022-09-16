# !/usr/bin/env python

import asyncio
from functools import update_wrapper

import asyncclick as click

from fsb.config import Config
from fsb.telegram.client import TelegramApiClient

client = TelegramApiClient(Config.bot_username)
client.loop.run_until_complete(client.connect(True))


@click.group()
async def cli():
    pass


def exit_with_message(message: str = None, code: int = 1):
    print(message)
    exit(code)


def coro(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))
    return update_wrapper(wrapper, f)
