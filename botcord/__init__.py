__title__ = 'BotCord'
__author__ = 'KEN_2000'
__version__ = '1.0.0'

from . import configs, errors
from .botclient import BotClient
from .functions import *
from .utils import find, str_info

__all__ = ['configs', 'errors', 'BotClient'] + functions.__all__ + ['find', 'str_info']
