# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from ..utils import url_valid


def search_cookies(func, arg, cookies):
    for i in cookies:
        if func(i[0], arg):
            return True
    return False


def identify_forum(expr, func, arg, rq, cookies):
    if expr is not None and rq is not None:
        t = rq.search(expr)
        if len(t) != 0:
            return True

    if arg and func:
        return search_cookies(func, arg, cookies)

    return False


def identify_phpbb(url, rq, cookies):
    return identify_forum(
        r"""
        i>body #i>phpbb | "t",
        i>meta i>name=i>copyright i>content=ia>phpbb | "t",
        * Ei>(class|id)=i>copyright m@i>"phpbb" | "t"
    """,
        str.startswith,
        "phpbb_",
        rq,
        cookies,
    )


def identify_xenforo1(url, rq, cookies):
    return identify_forum(r'html #XenForo | "t"', None, None, rq, cookies)


def identify_xenforo2(url, rq, cookies):
    return identify_forum(r'html #XF | "t"', None, None, rq, cookies)


def identify_smf1(url, rq, cookies):
    return identify_forum(
        r'* title="Simple Machines Forum" m@>"Powered by SMF 1." | "t"',
        None,
        None,
        rq,
        cookies,
    )


def identify_smf2(url, rq, cookies):
    return identify_forum(
        r"""
        * title=E>"Simple Machines( Forum)?" | "t",
        script m@B>"[^a-zA-Z0-9]smf_" | "t"
    """,
        None,
        None,
        rq,
        cookies,
    )


def identify_xmb(url, rq, cookies):
    return identify_forum(None, str.__eq__, "xmblva", rq, cookies)


def identify_invision(url, rq, cookies):
    return identify_forum(
        r"""
        * Ei>(class|id)=iE>(el)?copyright m@iE>"(invision|IP\.Board)" | "t"
    """,
        str.startswith,
        "ips4_",
        rq,
        cookies,
    )


def identify_stackexchange(url, rq, cookies):
    return identify_forum(
        r'div .header; h3; [0] a href="https://stackexchange.com/sites" m@f>"more stack exchange communities" | "t"',
        None,
        None,
        rq,
        cookies,
    )


def identify_hackernews(url, rq, cookies):
    base, rest = url_valid(url, base=True)
    if base == "https://news.ycombinator.com":
        return True
    return False


def listIdentify(extractor, url, rq, cookies, ilist):
    items = cookies.items()
    for i in ilist:
        if i[0](url, rq, items):
            return i[1]

    return None


def xenforoIdentify(extractor, url, rq, cookies):
    ilist = [
        (identify_xenforo1, extractor.v1),
        (identify_xenforo2, extractor.v2),
    ]
    return listIdentify(extractor, url, rq, cookies, ilist)


def smfIdentify(extractor, url, rq, cookies):
    ilist = [
        (identify_smf1, extractor.v1),
        (identify_smf2, extractor.v2),
    ]
    return listIdentify(extractor, url, rq, cookies, ilist)


def ForumIdentify(extractor, url, rq, cookies):
    ilist = [
        (identify_hackernews, extractor.hackernews),
        (identify_phpbb, extractor.phpbb),
        (identify_invision, extractor.invision),
        (identify_xmb, extractor.xmb),
        (identify_xenforo1, extractor.xenforo.v1),
        (identify_xenforo2, extractor.xenforo.v2),
        (identify_smf1, extractor.smf.v1),
        (identify_smf2, extractor.smf.v2),
        (identify_stackexchange, extractor.stackexchange),
    ]
    return listIdentify(extractor, url, rq, cookies, ilist)
