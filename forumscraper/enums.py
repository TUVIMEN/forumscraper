# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from enum import Enum, auto
from importlib.metadata import version

__version__ = version(__package__ or __name__)


class Outputs(Enum):
    threads = auto()
    forums = auto()
    dict = auto()
    id = auto()
    hash = auto()
