# !/usr/bin/env python
import json
import os
from logging import Logger

from fsb.error import OptionalAttributeError
from fsb.error import RequiredAttributeError


class Config:
    CONFIG_FILE = os.getenv('FSB_CONFIG_FILE')

    bot_token: str
    api_id: int
    api_hash: str

    bot_username: str
    developer: str
    contributors: list

    db_user: str
    db_password: str
    db_host: str
    db_name: str

    MAX_DB_CONNECTIONS = 10

    dev_chats: list

    REQUIRED_ATTRIBUTES = [
        'bot_token',
        'api_id',
        'api_hash',
        'db_user',
        'db_password',
        'db_host',
        'db_name',
    ]

    @staticmethod
    def get_annotations() -> dict:
        return Config.__annotations__


def init_config(logger: Logger):
    try:
        if not Config.CONFIG_FILE:
            raise EnvironmentError
        with open(Config.CONFIG_FILE, 'r', encoding='utf8') as fp:
            configs_by_json = json.load(fp)

        unknown_configs = configs_by_json.copy()
        required_attributes = Config.REQUIRED_ATTRIBUTES.copy()
        config_annotations = Config.get_annotations()
        for key, var_type in config_annotations.items():
            value = None
            env_value = os.getenv(key.upper())

            if env_value is not None:
                value = var_type(env_value)
            elif key in configs_by_json:
                value = configs_by_json[key]
                unknown_configs.pop(key)

            if value is not None:
                setattr(Config, key, value)
                if key in required_attributes:
                    required_attributes.remove(key)

        if unknown_configs:
            raise OptionalAttributeError(f"Unknown config parameters: {', '.join(unknown_configs.keys())}")

        if required_attributes:
            raise RequiredAttributeError(f"Missing required config parameter: {', '.join(required_attributes)}")

    except FileNotFoundError:
        exit(f"All configs and secrets should be in the {Config.CONFIG_FILE}")
    except EnvironmentError:
        exit("Not found environment variable FSB_CONFIG_FILE. You should add it to .env in root project directory")
    except RequiredAttributeError as err:
        exit(err.message)
    except OptionalAttributeError as err:
        logger.warning(err.message)
