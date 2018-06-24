import logging.config

from . import __logging__
logging.config.dictConfig(__logging__)

log = logging.getLogger(__name__)
log.debug("logging setup")

from .config import SetDefaults
from .gisi import Gisi
from .signals import GisiSignal
