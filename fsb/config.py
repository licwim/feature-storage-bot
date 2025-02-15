# !/usr/bin/env python

import os

from bestconfig import Config
from bestconfig.converters import BoolConverter

config = Config('config.yml')

config.set('BUILD', config.get('BUILD_VERSION', default_value='Unknown'))
config.set('FSB_DEV_MODE', config.get('FSB_DEV_MODE', cast=BoolConverter(), default_value=False))
config.set('ROOT_FOLDER', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config.set('FOOL_DAY', config.get('FOOL_DAY', cast=BoolConverter(), default_value=False))
