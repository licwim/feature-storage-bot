# !/usr/bin/env python

import click

from fsb.config import Config
from fsb.telegram.client import TelegramApiClient

client = TelegramApiClient(Config.bot_username)
client.loop.run_until_complete(client.connect(True))


@click.group()
def cli():
    pass


def exit_with_message(message: str = None, code: int = 1):
    print(message)
    exit(code)
