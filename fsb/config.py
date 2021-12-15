# !/usr/bin/env python


class Config:
    CONFIG_FILE = 'C:\\acode\\feature-storage-bot\\config.json'

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
