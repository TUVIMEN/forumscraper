# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from .common import ForumExtractor, ForumExtractorIdentify
from .identify import ForumIdentify

from .smf import smf, smf1, smf2
from .phpbb import phpbb
from .xmb import xmb
from .xenforo import (
    xenforo,
    xenforo1,
    xenforo2,
)
from .invision import invision


class Extractor(ForumExtractorIdentify):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.smf = smf(self.session, **self.settings)
        self.phpbb = phpbb(self.session, **self.settings)
        self.xmb = xmb(self.session, **self.settings)
        self.xenforo = xenforo(self.session, **self.settings)
        self.invision = invision(self.session, **self.settings)

        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [
                    r"([?/&;]topic[=,]|-t)\d+",
                    r"/?viewtopic.php.*[\&\?]t=\d+",
                    r"/viewthread.php\?tid=\d+$",
                    r"[/?](thread|topic)s?/",
                ],
            },
            {"func": "get_board", "exprs": [r"/forums?/$"]},
            {
                "func": "get_forum",
                "exprs": [
                    r"([?/&;]board[=,]|-t)\d+",
                    r"/viewforum.php",
                    r"/forumdisplay.php\?fid=\d+$",
                    r"[/?]forums?/",
                ],
            },
            {"func": "get_tag", "exprs": [r"[/?]tags?/"]},
            {"func": "get_board", "exprs": None},
        ]

    def identify_page(self, url, rq, cookies):
        return ForumIdentify(self, url, rq, cookies)
