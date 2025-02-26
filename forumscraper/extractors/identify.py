# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from ..utils import url_valid


def search_cookies(func, arg, cookies):
    for i in cookies.items():
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
        * Ei>(class|id)=i>copyright i@i>"phpbb" | "t"
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
        r'* title="Simple Machines Forum" i@>"Powered by SMF 1." | "t"',
        None,
        None,
        rq,
        cookies,
    )


def identify_smf2(url, rq, cookies):
    return identify_forum(
        r"""
        * title=E>"Simple Machines( Forum)?" | "t",
        script i@B>"[^a-zA-Z0-9]smf_" | "t"
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
        * Ei>(class|id)=iE>(el)?copyright i@iE>"(invision|IP\.Board)" | "t"
    """,
        str.startswith,
        "ips4_",
        rq,
        cookies,
    )


def identify_stackexchange(url, rq, cookies):
    return identify_forum(
        r'div .header; h3; [0] a href="https://stackexchange.com/sites" i@f>"more stack exchange communities" | "t"',
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


def identify_vbulletin(url, rq, cookies):
    return identify_forum(
        r"""
            html #vbulletin_html | "t",
            style #vbulletin_css | "t",
            div #footer_copyright | "t",
            meta content=b>"vBulletin" | "t",
            script src=a>"/vbulletin_" | "t"
        """,
        None,
        None,
        rq,
        cookies,
    )
