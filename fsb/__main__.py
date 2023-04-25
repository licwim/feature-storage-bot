# !/usr/bin/env python

from fsb.app import FeatureStorageBot
from fsb.config import init_config, Config
from fsb.logger import init_logger


def main():
    init_logger(False, Config)
    init_config()
    app = FeatureStorageBot()
    app.run()


if __name__ == '__main__':
    main()
