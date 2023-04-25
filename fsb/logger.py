# !/usr/bin/env python

import logging
import logging.config

import yaml


class LevelFilter(logging.Filter):
    def __init__(self, level):
        if isinstance(level, str):
            level = logging.getLevelName(level)
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


def init_logger(console: bool, config):
    with open(config.ROOT_FOLDER + '/config/logging.yml', 'rt') as file:
        logging_config = yaml.safe_load(file.read())
        logger_config_key = 'console' if console else 'app'
        logging_config['loggers']['main'] = logging_config['loggers'][logger_config_key]
        logging_config['loggers'].pop('app')
        logging_config['loggers'].pop('console')
        logging.config.dictConfig(logging_config)

    logger = logging.getLogger('main')

    if config.FSB_DEV_MODE:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
