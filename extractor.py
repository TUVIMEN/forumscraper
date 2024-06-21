# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import sys
import os
import json
import re
import warnings
from reliq import reliq

from net import Session
from common import ForumExtractor
from identify import ForumIdentify

from smf import smfExtractor as smf
from phpbb import phpbbExtractor as phpbb
from xmb import xmbExtractor as xmb
from xenforo import xenforoExtractor as xenforo
from invision import invisionExtractor as invision

class Extractor(ForumExtractor):
    def __init__(self,session=None,**kwargs):
        super().__init__(session,**kwargs)

        self.trim = True

        self.smf = smf(self.session)
        self.phpbb = phpbb(self.session)
        self.xmb = xmb(self.session)
        self.xenforo = xenforo(self.session)
        self.invision = invision(self.session)

    def identify(self,rq):
        return ForumIdentify(self,rq)

    def get_thread(self,url,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)
        forum = self.identify(rq)
        if not forum:
            return

        return forum.get_thread(url,rq,**kwargs)

    def get_user(self,url,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)
        forum = self.identify(rq)
        if not forum:
            return

        return forum.get_user(url,rq,**kwargs)

    def get_forum(self,url,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)
        forum = self.identify(rq)
        if not forum:
            return

        return forum.get_forum(url,rq,**kwargs)

    def get_tag(self,url,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)
        forum = self.identify(rq)
        if not forum:
            return

        return forum.get_tag(url,rq,**kwargs)

    def get_board(self,url,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)
        forum = self.identify(rq)
        if not forum:
            return

        return forum.get_board(url,rq,**kwargs)
