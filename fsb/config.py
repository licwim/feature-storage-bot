# !/usr/bin/env python
import inspect
import os


class Config:
    CONFIG_FILE = os.getenv('FSB_CONFIG_FILE')

    bot_token = os.getenv('BOT_TOKEN')
    api_id = int(os.getenv('API_ID')) if os.getenv('API_ID') else None
    api_hash = os.getenv('API_HASH')

    bot_username: str = None
    developer: str = None
    contributors: list = []

    REQUIRED_ATTRIBUTES = [
        'bot_token',
        'api_id',
        'api_hash',
    ]

    @staticmethod
    def get_attributes() -> dict:
        attributes = {}
        for i in inspect.getmembers(Config):
            if not i[0].startswith('_'):
                if not inspect.ismethod(i[1]) and not inspect.isfunction(i[1]):
                    attributes.update([i])

        for i in inspect.get_annotations(Config):
            if not i.startswith('_') and i not in attributes.keys():
                attributes[i] = None

        return attributes
