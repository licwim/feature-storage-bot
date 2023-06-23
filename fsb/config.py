# !/usr/bin/env python

import os

from bestconfig import Config

config = Config('config.yml')

VERSION = os.getenv('RELEASE') if os.getenv('RELEASE') else 'Unknown'
BUILD = os.getenv('BUILD_VERSION') if os.getenv('BUILD_VERSION') else 'Unknown'
FSB_DEV_MODE = bool(int(os.getenv('FSB_DEV_MODE'))) if os.getenv('FSB_DEV_MODE') else False
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config.update_from_locals()
