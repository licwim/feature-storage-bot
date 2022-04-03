# !/usr/bin/env python
import inspect
import json
import os
from logging import Logger

from .error import OptionalAttributeError
from .error import RequiredAttributeError


class Config:
    CONFIG_FILE = os.getenv('FSB_CONFIG_FILE')

    bot_token = os.getenv('BOT_TOKEN')
    api_id = int(os.getenv('API_ID')) if os.getenv('API_ID') else None
    api_hash = os.getenv('API_HASH')

    bot_username: str = None
    developer: str = None
    contributors: list = []

    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host: str = 'localhost'
    db_name: str = 'feature_storage'
    MAX_DB_CONNECTIONS = 10

    dev_chats: list = []

    REQUIRED_ATTRIBUTES = [
        'bot_token',
        'api_id',
        'api_hash',
        'db_user',
        'db_password'
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


def init_config(logger: Logger):
    try:
        if not Config.CONFIG_FILE:
            raise EnvironmentError
        with open(Config.CONFIG_FILE, 'r', encoding='utf8') as fp:
            configs_by_json = json.load(fp)

        unknown_configs_check = configs_by_json.copy()
        for key in configs_by_json.copy():
            if key in Config.get_attributes().keys():
                setattr(Config, key, configs_by_json[key])
                unknown_configs_check.pop(key)
        if unknown_configs_check:
            raise OptionalAttributeError(f"Unknown config parameters: {', '.join(unknown_configs_check.keys())}")

        missing_attributes = []
        for key in Config.REQUIRED_ATTRIBUTES:
            if getattr(Config, key) is None:
                missing_attributes.append(key)
        if missing_attributes:
            raise RequiredAttributeError(f"Missing required config parameter: {', '.join(missing_attributes)}")

    except FileNotFoundError:
        exit(f"All configs and secrets should be in the {Config.CONFIG_FILE}")
    except EnvironmentError:
        exit("Not found environment variable FSB_CONFIG_FILE. You should add it to .env in root project directory")
    except (RequiredAttributeError, OptionalAttributeError) as err:
        if isinstance(err, RequiredAttributeError):
            exit(err.message)
        elif isinstance(err, OptionalAttributeError):
            logger.warning(err.message)
