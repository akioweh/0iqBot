__title__ = 'BotCord'
__author__ = 'Akioweh'
__version__ = '1.0.0'

from . import configs, errors, functions
from .botclient import BotClient
from .functions import *
from .utils import find, str_info

__all__ = ['configs', 'errors', 'BotClient'] + functions.__all__ + ['find', 'str_info']
