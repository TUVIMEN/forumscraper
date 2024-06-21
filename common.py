# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
import json
import re
import warnings
from reliq import reliq

from utils import strtosha256
from net import Session

def get_first_html(extractor,url,rq=None):
    if rq is None:
        return extractor.session.get_html(url,extractor.trim)
    if isinstance(rq,reliq):
        return rq
    return reliq(rq)

class ItemExtractor():
    def __init__(self,session):
        self.path_format = '{}'
        self.match = [None,0]
        self.trim = False

        self.session = session

    def get_url(self,url):
        return url

    def get_first_html(self,url,rq=None):
        return get_first_html(self,url,rq)

    def get_improper_url(self,url,rq):
        warnings.warn('improper url - "{}"'.format(url))
        return [None,0]

    def get(self,url,rq=None,**kwargs):
        r = re.fullmatch(self.match[0],url)
        if r is None:
            rq, t_id = self.get_improper_url(url,rq)
            if not rq:
                return None
        else:
            t_id = int(r[self.match[1]])

        path = self.path_format.format(str(t_id))

        if os.path.exists(path):
            return

        url = self.get_url(url)
        rq = self.get_first_html(url,rq)

        with open(path,'x') as f:
            f.write(json.dumps(self.get_contents(rq,url,t_id,**kwargs)))

    def get_contents(self,rq,url,t_id,**kwargs):
        return {}

class ForumExtractor():
    def __init__(self,session=None,**kwargs):
        self.thread = None
        self.user = None

        self.forum_threads_expr = None
        self.forum_forums_expr = None
        self.tag_threads_expr = None
        self.board_forums_expr = None

        self.trim = False

        if session:
            self.session = session
        else:
            self.session = Session(**kwargs)

    url_base = None #blank function

    def get_first_html(self,url,rq=None):
        return get_first_html(self,url,rq)

    def get_thread(self,url,rq=None,**kwargs):
        return self.thread.get(url,rq,**kwargs)

    def get_user(self,url,rq=None,**kwargs):
        return self.user.get(url,rq,**kwargs)

    @staticmethod
    def url_base_merge(urlbase,url):
        if len(url) == 0 or len(urlbase) == 0 or re.search(r'^https?://',url):
            return url

        if urlbase[-1] == '/':
            urlbase = urlbase[:-1]
        if url[0] == '/':
            url = url[1:]

        return '{}/{}'.format(urlbase,url)

    def get_next(self,rq):
        pass

    def get_forum_next(self,rq):
        self.get_next(rq)

    def get_tag_next(self,rq):
        self.get_next(rq)

    def go_through_page(self,baseurl,rq,func,**kwargs):
        for i in rq.search(expr).split('\n')[:-1]:
            url = i
            if self.url_base:
                url = self.url_base_merge(urlbase,i)

            func(url,**kwargs)

    def go_through_pages(self,url,threads_expr,forums_expr,func_next,rq=None,**kwargs):
        rq = self.get_first_html(url,rq)

        urlbase = None
        if self.url_base:
            urlbase = self.url_base(url)

        uses_board = callable(forums_expr)
        if uses_board:
            forums_expr(self,url,rq,**kwargs)

        while True:
            if forums_expr and not uses_board:
                go_through_page(self,baseurl,rq,self.get_thread,**kwargs)

            if threads_expr:
                go_through_page(self,baseurl,rq,self.get_forum,**kwargs)

            if not func_next:
                break

            nexturl = func_next(rq)
            if len(nexturl) == 0:
                break
            if urlbase:
                nexturl = self.url_base_merge(urlbase,nexturl)
            rq = self.get_first_html(nexturl)

    def get_forum(self,url,rq=None,**kwargs):
        return go_through_pages(
                self,
                url,
                self.forum_threads_expr,
                self.forum_forums_expr,
                self.get_forum_next,
                rq,
                **kwargs)

    def get_tag(self,url,rq=None,**kwargs):
        if not self.tag_threads_expr:
            return
        return go_through_pages(
                self,
                url,
                self.tag_threads_expr,
                None,
                self.get_tag_next,
                rq,
                **kwargs)

    def get_board(self,url,rq=None,**kwargs):
        if not self.board_forums_expr:
            return
        return go_through_pages(
                self,
                url,
                None,
                self.board_forums_expr,
                None,
                rq,
                **kwargs)

    def get_from_url(self,url,**kwargs):
        pass
