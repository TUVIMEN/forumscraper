# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import copy
import hashlib
import re


def dict_add(dest, src):
    for i in src.items():
        dest[i[0]] = i[1]


def strtosha256(string):
    if isinstance(string, str):
        string = string.encode()

    return hashlib.sha256(string).hexdigest()


def settings_copy(
    settings,
):  # function necessary because copy.deepcopy is too stupid to handle TextIOWrapper
    ret = copy.copy(settings)

    for i in settings.keys():
        if isinstance(i, (dict, list, set)):
            ret[i] = copy.deepcopy(ret[i])

    return ret


def get_settings(settings, **kwargs):
    ret = settings_copy(settings)

    for i in settings.keys():
        val = kwargs.get(i)
        if val:
            if isinstance(ret[i], dict) and isinstance(val, dict):
                ret[i].update(val)
            else:
                ret[i] = val
    return ret


def url_valid(string, regex=None, basegroups=False):
    pattern = r"https?://(localhost|([a-zA-Z0-9-]{1,256}\.)+[a-zA-Z]{1,6})(:\d+)?"
    baseg = re.search(pattern, string)
    if not baseg:
        return

    string = string[baseg.end() :]

    if not regex:
        if basegroups:
            return baseg
        else:
            return string

    groups = re.search(regex, string)
    if not groups:
        return
    if basegroups:
        return [baseg, groups]
    return groups
