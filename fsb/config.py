# !/usr/bin/env python
import json
import os
from logging import Logger

from fsb.error import OptionalAttributeError
from fsb.error import RequiredAttributeError


class MetaConfig(type):
    def __getattr__(cls, key):
        if key in cls.__annotations__.keys():
            return None
        else:
            raise AttributeError(key)


class Config(metaclass=MetaConfig):
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

    dudes_sticker_set_name: str
    dudes_sticker_set_documents_ids: list

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
            env_value = os.getenv(key.upper())
            config_value = configs_by_json[key] if key in configs_by_json else None
            value = env_value if env_value is not None else config_value

            if key in configs_by_json:
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
