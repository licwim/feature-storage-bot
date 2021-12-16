# !/usr/bin/env python
import os


class Config:
    CONFIG_FILE = os.getenv('FSB_CONFIG_FILE')

    bot_username = str()
    bot_token = str()
    api_id = int()
    api_hash = str()

    REQUIRED_ATTRIBUTES = [
        'bot_username',
        'bot_token',
        'api_id',
        'api_hash',
    ]
