# !/usr/bin/env python
import os


class Config:
    CONFIG_FILE = os.getenv('FSB_CONFIG_FILE')

    bot_username: str = None
    bot_token: str
    api_id: int
    api_hash: str
    developer: str = None
    contributors: list = []

    REQUIRED_ATTRIBUTES = [
        'bot_token',
        'api_id',
        'api_hash',
    ]

    @staticmethod
    def get_attributes() -> dict:
        return Config.__annotations__
