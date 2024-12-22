# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from .common import ForumExtractorIdentify

from .smf import smf, smf1, smf2
from .phpbb import phpbb
from .xmb import xmb
from .xenforo import xenforo, xenforo1, xenforo2
from .invision import invision
from .hackernews import hackernews
from .stackexchange import stackexchange


class Extractor(ForumExtractorIdentify):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.smf = smf(self.session, **self.settings)
        self.phpbb = phpbb(self.session, **self.settings)
        self.xmb = xmb(self.session, **self.settings)
        self.xenforo = xenforo(self.session, **self.settings)
        self.invision = invision(self.session, **self.settings)
        self.hackernews = hackernews(self.session, **self.settings)
        self.stackexchange = stackexchange(self.session, **self.settings)

        self.extractors = [
            self.hackernews,
            self.phpbb,
            self.invision,
            self.xmb,
            self.xenforo,
            self.smf,
            self.stackexchange,
            self.vbulletin,
        ]

        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [
                    r"([?/&;]topic[=,]|-t)\d+",
                    r"/?viewtopic\.php.*[\&\?]t=\d+",
                    r"/viewthread\.php\?tid=\d+$",
                    r"/showthread\.php\?",
                    r"[/?](thread|topic)s?/",
                    r"/questions/(\d+)",
                ],
            },
            {"func": "get_board", "exprs": [r"/forums?(/|\.php(\?[^/]*)?)$"]},
            {"func": "get_tag", "exprs": [r"[/?]tags?/"]},
            {
                "func": "get_user",
                "exprs": [r"/users/(\d+)"],
            },
            {
                "func": "get_forum",
                "exprs": [
                    r"([?/&;]board[=,]|-t)\d+",
                    r"/viewforum\.php",
                    r"/forumdisplay\.php(\?|/)",
                    r"[/?]forums?/([^/]+/?)?$",
                ],
            },
            {
                "func": "get_thread",
                "exprs": [
                    r"(/[^/]+){2,}/\d+-[^/]+$",
                    r"(/[^/]+){2,}/[^/]+-\d+(\.html|/)$",
                ],
            },
            {"func": "get_forum", "exprs": [r"(/[^/]+){3,}/$"]},
            {"func": "get_board", "exprs": None},
        ]
