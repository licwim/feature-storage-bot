# !/usr/bin/env python

import json

from .app import FeatureStorageBot
from .config import Config


def init_config():
    try:
        if not Config.CONFIG_FILE:
            exit("Not found environment variable FSB_CONFIG_FILE. You should add it to .env in root project directory")
        with open(Config.CONFIG_FILE, 'r', encoding='utf8') as fp:
            configs_by_json = json.load(fp)
        for key in Config.REQUIRED_ATTRIBUTES:
            setattr(Config, key, configs_by_json.pop(key))
        if configs_by_json:
            raise AttributeError(f"Unknown config parameters: {', '.join(configs_by_json.keys())}")
    except FileNotFoundError:
        exit(f"All configs and secrets should be in the {Config.CONFIG_FILE}")
    except KeyError as err:
        if len(err.args) > 0:
            exit(f"Missing required config parameter: {err.args[0]}")
        else:
            raise
    except AttributeError as err:
        if len(err.args) > 0:
            exit(err.args[0])
        else:
            raise


def main():
    init_config()
    app = FeatureStorageBot()
    app.run()


if __name__ == '__main__':
    main()
