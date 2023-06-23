# !/usr/bin/env python

from functools import update_wrapper

import click

from fsb.config import config
from fsb.telegram.client import TelegramApiClient

client = TelegramApiClient(config.BOT_USERNAME + '-cli', True)


@click.group()
def cli():
    client.loop.run_until_complete(client.connect(True))


def exit_with_message(message: str = None, code: int = 1):
    print(message)
    exit(code)


def coro(f):
    def wrapper(*args, **kwargs):
        return client.loop.run_until_complete(f(*args, **kwargs))
    return update_wrapper(wrapper, f)
