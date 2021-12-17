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


logging.basicConfig(
    format='%(asctime)s::[%(name)s:%(levelname)s] %(message)s',
    level=logging.WARNING
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)