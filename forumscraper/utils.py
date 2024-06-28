# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import hashlib


def dict_add(dest, src):
    for i in src.items():
        dest[i[0]] = i[1]


def strtosha256(string):
    if isinstance(string, str):
        string = string.encode()

    return hashlib.sha256(string).hexdigest()


def get_settings(settings, **kwargs):
    ret = settings
    for i in settings.keys():
        val = kwargs.get(i)
        if val:
            ret[i] = val
    return ret
