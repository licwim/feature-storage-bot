# !/usr/bin/env python

import logging
import logging.config

from fsb.config import config


class LevelFilter(logging.Filter):
    def __init__(self, level):
        if isinstance(level, str):
            level = logging.getLevelName(level)
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


def init_logger(console: bool):
    logging_config = config.logging
    logger_config_key = 'console' if console else 'app'
    logging_config['loggers']['main'] = logging_config['loggers'][logger_config_key]
    logging_config['loggers'].pop('app')
    logging_config['loggers'].pop('console')

    for handler_name, handler in logging_config.handlers.items():
        if 'filename' in handler.keys() and '{dir}' in handler['filename']:
            logging_config['handlers'][handler_name]['filename'] = handler['filename'].format(dir=config.LOG_FOLDER)

    logging.config.dictConfig(logging_config)

    logger = logging.getLogger('main')

    if config.FSB_DEV_MODE:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
