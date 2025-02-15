# !/usr/bin/env python

import logging
import logging.config
import os

from fsb.config import config


class LevelFilter(logging.Filter):
    def __init__(self, level):
        if isinstance(level, str):
            level = logging.getLevelName(level)
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


def init_logger(console: bool):
    logging_config = config.logging.to_dict()
    logger_config_key = 'console' if console else 'app'

    for opt_name, opt_value in logging_config['loggers'][logger_config_key].items():
        logging_config['root'][opt_name] = opt_value

    logging_config.pop('loggers')
    _dir = os.path.abspath(config.get('LOG_FOLDER', default_value=config.ROOT_FOLDER + '/logs'))
    os.makedirs(_dir, exist_ok=True)

    for handler_name, handler in logging_config['handlers'].items():
        if 'filename' in handler.keys() and '{log_dir}' in handler['filename']:
            logging_config['handlers'][handler_name]['filename'] = os.path.abspath(handler['filename'].format(log_dir=_dir))

    config.set('logging', logging_config)
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('main')

    if config.FSB_DEV_MODE:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
