# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re

from .common import ForumExtractor
from .identify import ForumIdentify

from .smf import smfExtractor as smf
from .phpbb import phpbbExtractor as phpbb
from .xmb import xmbExtractor as xmb
from .xenforo import xenforoExtractor as xenforo
from .invision import invisionExtractor as invision


class Extractor(ForumExtractor):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.smf = smf(self.session, **self.settings)
        self.phpbb = phpbb(self.session, **self.settings)
        self.xmb = xmb(self.session, **self.settings)
        self.xenforo = xenforo(self.session, **self.settings)
        self.invision = invision(self.session, **self.settings)

    def identify(self, rq):
        return ForumIdentify(self, rq)

    def _get_unknown(self, func_name, url, rq=None, **kwargs):
        settings = self.get_settings(**kwargs)
        rq = self.get_first_html(url, rq)
        forum = self.identify(rq)
        if not forum:
            return None

        func = getattr(forum, func_name)
        return func(url, rq, **settings)

    def get_thread(self, url, rq=None, **kwargs):
        return self._get_unknown("get_thread", url, rq, **kwargs)

    def get_user(self, url, rq=None, **kwargs):
        return self._get_unknown("get_user", url, rq, **kwargs)

    def get_forum(self, url, rq=None, **kwargs):
        return self._get_unknown("get_forum", url, rq, **kwargs)

    def get_tag(self, url, rq=None, **kwargs):
        return self._get_unknown("get_tag", url, rq, **kwargs)

    def get_board(self, url, rq=None, **kwargs):
        return self._get_unknown("get_board", url, rq, **kwargs)

    def guess(self, url, **kwargs):
        if not re.search(r"^https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+", url):
            return None

        guesslist = [
            {
                "func": self.get_thread,
                "exprs": [
                    r"([?/&;]topic[=,]|-t)\d+",
                    r"/?viewtopic.php.*[\&\?]t=\d+",
                    r"/viewthread.php\?tid=\d+$",
                    r"[/?](thread|topic)s?/",
                ],
            },
            {"func": self.get_board, "exprs": [r"/forums?/$"]},
            {
                "func": self.get_forum,
                "exprs": [
                    r"([?/&;]board[=,]|-t)\d+",
                    r"/viewforum.php",
                    r"/forumdisplay.php\?fid=\d+$",
                    r"[/?]forums?/",
                ],
            },
            {"func": self.get_tag, "exprs": [r"[/?]tags?/"]},
        ]

        for i in guesslist:
            func = i["func"]
            exprs = i["exprs"]

            for expr in exprs:
                if re.search(expr, url):
                    return func(url, **kwargs)

        return self.get_board(url, **kwargs)
