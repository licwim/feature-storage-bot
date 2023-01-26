# !/usr/bin/env python
# ================================================= #
#                                                   #
#    ───╔═╗──╔══╗╔══╗╔═╗╔═╗╔═╗╔══╗╔═╗─────╔═╗───    #
#    ───║ ║──╚╗╔╝║╔═╝║ ║║ ║║ ║╚╗╔╝║ ║─────║ ║───    #
#    ───║ ║───║║─║║──║ ║║ ║║ ║─║║─║ ╚═╗ ╔═╝ ║───    #
#    ───║ ║───║║─║║──║ ║║ ║║ ║─║║─║ ╔═╗ ╔═╗ ║───    #
#    ───║ ╚═╗╔╝╚╗║╚═╗║ ╚╝ ╚╝ ║╔╝╚╗║ ║ ╚═╝ ║ ║───    #
#    ───╚═══╝╚══╝╚══╝╚══╝ ╚══╝╚══╝╚═╝─────╚═╝───    #
#                                                   #
#   __init__.py                                     #
#       By: licwim                                  #
#                                                   #
#   Created: 13-06-2021 11:56:01 by licwim          #
#   Updated: 13-06-2021 11:56:11 by licwim          #
#                                                   #
# ================================================= #

import logging
import os
import sys

from .config import init_config

VERSION = os.getenv('RELEASE') if os.getenv('RELEASE') else 'Unknown'
BUILD = os.getenv('BUILD_VERSION') if os.getenv('BUILD_VERSION') else 'Unknown'
FSB_DEV_MODE = bool(int(os.getenv('FSB_DEV_MODE'))) if os.getenv('FSB_DEV_MODE') else False


class LogFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


stdout_handler = logging.StreamHandler(sys.stdout)
stderr_handler = logging.StreamHandler(sys.stderr)
log_filter = LogFilter(logging.WARNING)
log_formatter = logging.Formatter('[%(name)s:%(levelname)s] %(message)s')
stdout_handler.addFilter(log_filter)
stdout_handler.setLevel(logging.NOTSET)
stdout_handler.setFormatter(log_formatter)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.addHandler(stdout_handler)
root_logger.addHandler(stderr_handler)
root_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

if FSB_DEV_MODE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

init_config(logger)
