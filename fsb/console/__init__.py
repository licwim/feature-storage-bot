# !/usr/bin/env python

from functools import update_wrapper

import click

from fsb.config import config
from fsb.services import ChatService
from fsb.telegram.client import TelegramApiClient

client = TelegramApiClient(config.BOT_USERNAME + '-cli', True)


@click.group()
def cli():
    async def before(client):
        await client.connect(True)

    client.loop.run_until_complete(before(client))


def coro(f):
    def wrapper(*args, **kwargs):
        return client.loop.run_until_complete(f(*args, **kwargs))
    return update_wrapper(wrapper, f)
