# by Dominik Stanisław Suchora <hexderm@gmail.com>
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


def smarttrim(src):
    # turns " \v i am a   \a \n \n \a test  \a " to "i am a test"

    return " ".join(
        src.translate(str.maketrans("\t\n\r\a\v\f\v", "       ", "")).split()
    )


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
        if val is not None:
            if isinstance(ret[i], dict) and isinstance(val, dict):
                ret[i].update(val)
            else:
                ret[i] = val
    return ret


def url_valid(url, regex=None, base=False, matchwhole=False):
    if url is None or len(url) == 0:
        return

    pattern = r"^https?://(localhost|([a-zA-Z0-9_-]{1,256}\.)+[a-zA-Z]{1,6})(:\d+)?"
    baseg = re.search(pattern, url)
    if not baseg:
        return

    rest = url[baseg.end() :]

    if not regex:
        if base:
            return [baseg[0], rest]
        else:
            return rest

    groups = re.search(regex, rest if not matchwhole else url)
    if not groups:
        return
    if base:
        return [baseg, groups]
    return groups


def conv_short_size(string):
    letter = string[-1:]
    num = 0
    try:
        if letter.isdigit():
            num = float(string)
        else:
            num = float(string[:-1])
            if letter == "M" or letter == "m":
                num *= 1000000
            elif letter == "K" or letter == "k":
                num *= 1000
    except ValueError:
        pass
    return int(num)


def conv_curl_header_to_requests(src):
    r = re.search(r"^\s*([A-Za-z0-9_-]+)\s*:(.*)$", src)
    if r is None:
        return None
    return {r[1]: r[2].strip()}


def conv_curl_cookie_to_requests(src):
    r = re.search(r"^\s*([A-Za-z0-9_-]+)\s*=(.*)$", src)
    if r is None:
        return None
    return {r[1]: r[2].strip()}
