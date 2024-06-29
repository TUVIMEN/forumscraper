# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3


def _search_cookies(func, arg, cookies):
    for i in cookies:
        if func(i[0], arg):
            return True
    return False


def _identify_forum(expr, func, arg, rq, cookies):
    if expr and rq:
        t = rq.search(expr)
        if len(t) != 0:
            return True

    if arg and func:
        return _search_cookies(func, arg, cookies)

    return False


def identify_phpbb(rq, cookies):
    return _identify_forum(
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


def identify_xenforo1(rq, cookies):
    return _identify_forum(r'html #XenForo | "t"', None, None, rq, cookies)


def identify_xenforo2(rq, cookies):
    return _identify_forum(r'html #XF | "t"', None, None, rq, cookies)


def identify_smf1(rq, cookies):
    return _identify_forum(
        r'* l@[1] m@E>"Powered by SMF 1\.[^<]*<" | "t"', None, None, rq, cookies
    )


def identify_smf2(rq, cookies):
    return _identify_forum(
        r"""
        * title=E>"Simple Machines( Forum)?" | "t",
        script m@B>"[^a-zA-Z0-9]smf_" | "t"
    """,
        None,
        None,
        rq,
        cookies,
    )


def identify_xmb(rq, cookies):
    return _identify_forum(None, str.__eq__, "xmblva", rq, cookies)


def identify_invision(rq, cookies):
    return _identify_forum(
        r"""
        * Ei>(class|id)=iE>(el)?copyright m@iE>"(invision|IP\.Board)" | "t"
    """,
        str.startswith,
        "ips4_",
        rq,
        cookies,
    )


def listIdentify(extractor, rq, ilist):
    cookies = extractor.session.cookies.get_dict().items()

    for i in ilist:
        if i[0](rq, cookies):
            return i[1]

    return None


def xenforoIdentify(extractor, rq):
    ilist = [
        (identify_xenforo1, extractor.v1),
        (identify_xenforo2, extractor.v2),
    ]
    return listIdentify(extractor, rq, ilist)


def smfIdentify(extractor, rq):
    ilist = [
        (identify_smf1, extractor.v1),
        (identify_smf2, extractor.v2),
    ]
    return listIdentify(extractor, rq, ilist)


def ForumIdentify(extractor, rq):
    ilist = [
        (identify_phpbb, extractor.phpbb),
        (identify_invision, extractor.invision),
        (identify_xmb, extractor.xmb),
        (identify_xenforo1, extractor.xenforo.v1),
        (identify_xenforo2, extractor.xenforo.v2),
        (identify_smf1, extractor.smf.v1),
        (identify_smf2, extractor.smf.v2),
    ]
    return listIdentify(extractor, rq, ilist)
