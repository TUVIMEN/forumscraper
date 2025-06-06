# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from enum import Flag, auto
from importlib.metadata import version

from reliq import RQ

reliq = RQ(path="reliq",cached=True)

__version__ = version(__package__ or __name__)


class Outputs(Flag):
    write_by_id = auto()
    write_by_hash = auto()
    writers = write_by_id | write_by_hash

    data = auto()

    boards = auto()
    tags = auto()
    forums = auto()
    threads = auto()
    users = auto()
    reactions = auto()

    only_urls_threads = auto()
    only_urls_forums = auto()
    urls = auto()
    save_urls = only_urls_threads | only_urls_forums | urls
