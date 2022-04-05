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

from .config import init_config

VERSION = '1.1.5-beta'
FSB_DEV_MODE = bool(int(os.getenv('FSB_DEV_MODE'))) if os.getenv('FSB_DEV_MODE') else False

logging.basicConfig(
    format='%(asctime)s::[%(name)s:%(levelname)s] %(message)s',
    level=logging.WARNING
)

logger = logging.getLogger(__name__)

if FSB_DEV_MODE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

init_config(logger)
