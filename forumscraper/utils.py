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
        if val is not None:
            if isinstance(ret[i], dict) and isinstance(val, dict):
                ret[i].update(val)
            else:
                ret[i] = val
    return ret


def url_valid(url, regex=None, base=False):
    if url is None or len(url) == 0:
        return

    pattern = r"^https?://(localhost|([a-zA-Z0-9-]{1,256}\.)+[a-zA-Z]{1,6})(:\d+)?"
    baseg = re.search(pattern, url)
    if not baseg:
        return

    rest = url[baseg.end() :]

    if not regex:
        if base:
            return [baseg[0], rest]
        else:
            return rest

    groups = re.search(regex, rest)
    if not groups:
        return
    if base:
        return [baseg, groups]
    return groups


def url_merge(ref, url):
    if url is None or len(url) == 0:
        return

    url = url.replace("&amp;", "&")
    ref = ref.replace("&amp;", "&")

    if ref[:2] == "//":
        ref = "https:" + ref

    refvalid = url_valid(ref, base=True)
    refbase = None
    refprotocol = "https"
    if refvalid is not None:
        refbase = refvalid[0]
        refprotocol = refbase[: refbase.index(":")]

    if url[:2] == "//":
        return refprotocol + ":" + url
    if url_valid(url) is not None or url[:11] == "data:image/":
        return url

    if ref is None or refvalid is None:
        return

    if ref[-3:] == "/./":
        ref = ref[:-2]

    if (url[:1] != "/" and ref[-1:] != "/") or url[:2] == "./":
        if ref.count("/") > 2:
            ref = re.sub(r"[^/]*$", r"", ref)
        if url[:1] == ".":
            url = url[2:]
    else:
        ref = refbase

    if ref[-3:] == "/./":
        ref = ref[:-3]
    if ref[-1] == "/":
        ref = ref[:-1]

    if url[:1] == "/":
        url = url[1:]

    return "{}/{}".format(ref, url)


def url_merge_r(ref, url):
    '''Same as url_merge() but instead of returning None on failure returns ""'''
    r = url_merge(ref, url)
    if r is None:
        return ""
    return r


def conv_short_size(string):
    letter = string[-1:]
    num = 0
    try:
        if letter.isdigit():
            num = float(string)
        else:
            num = float(string[:-1])
            if letter == "M":
                num *= 1000000
            elif letter == "K" or letter == "k":
                num *= 1000
    except ValueError:
        pass
    return int(num)
