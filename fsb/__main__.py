# !/usr/bin/env python

import json

from fsb import logger
from fsb.error import OptionalAttributeError
from fsb.error import RequiredAttributeError
from .app import FeatureStorageBot
from .config import Config


def init_config():
    try:
        if not Config.CONFIG_FILE:
            raise EnvironmentError
        with open(Config.CONFIG_FILE, 'r', encoding='utf8') as fp:
            configs_by_json = json.load(fp)

        missing_attributes = []
        for key in Config.REQUIRED_ATTRIBUTES:
            if key not in configs_by_json.keys():
                missing_attributes.append(key)
        if missing_attributes:
            raise RequiredAttributeError(f"Missing required config parameter: {', '.join(missing_attributes)}")

        for key in configs_by_json.copy():
            if key in Config.get_attributes().keys():
                setattr(Config, key, configs_by_json.pop(key))
        if configs_by_json:
            raise OptionalAttributeError(f"Unknown config parameters: {', '.join(configs_by_json.keys())}")

    except FileNotFoundError:
        exit(f"All configs and secrets should be in the {Config.CONFIG_FILE}")
    except EnvironmentError:
        exit("Not found environment variable FSB_CONFIG_FILE. You should add it to .env in root project directory")
    except (RequiredAttributeError, OptionalAttributeError) as err:
        if isinstance(err, RequiredAttributeError):
            exit(err.message)
        elif isinstance(err, OptionalAttributeError):
            logger.warning(err.message)


def main():
    init_config()
    app = FeatureStorageBot()
    app.run()


if __name__ == '__main__':
    main()
