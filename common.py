# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
import json
import re
import warnings
from reliq import reliq

from utils import strtosha256
from net import Session
from enums import Outputs

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
        self.output = Outputs.id

    def get_url(self,url):
        return url

    def get_first_html(self,url,rq=None):
        return get_first_html(self,url,rq)

    def get_improper_url(self,url,rq):
        warnings.warn('improper url - "{}"'.format(url))
        return [None,0]

    def get(self,settings,url,rq=None,**kwargs):
        r = re.fullmatch(self.match[0],url)
        if r is None:
            rq, t_id = self.get_improper_url(url,rq)
            if not rq:
                return None
        else:
            t_id = int(r[self.match[1]])

        path = None

        if settings['output'] == Outputs.id:
            path = self.path_format.format(str(t_id))
        elif settings['output'] == Outputs.hash:
            path = strtosha256(url)

        if path and os.path.exists(path):
            return

        url = self.get_url(url)
        rq = self.get_first_html(url,rq)

        contents = self.get_contents(settings,rq,url,t_id)
        if not path:
            if settings['output'] != Outputs.dict:
                return None
            return contents

        with open(path,'x') as f:
            f.write(json.dumps(contents))
        return path

    def get_contents(self,settings,rq,url,t_id):
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

        #threads=1
        #thread_pages_max=0
        #pages_max=0
        #pages_maxthreads=0
        #pages_threads_max=0
        #output=pages_threads,pages_forums,pages_dict,pages_ids,pages_hashes
        self.settings = {
            'threads': 1,
            'thread_pages_max': 0,
            'pages_max': 0,
            'pages_max_depth': 0,
            'pages_threads_max': 0,
            'accumulate': False,
            'output': Outputs.id,
            'nousers': False,
            'noreactions': False
        }
        self.settings = self.get_settings(**kwargs)

    def get_settings(self,**kwargs):
        ret = self.settings
        for i in self.settings.keys():
            val = kwargs.get(i)
            if val:
                ret[i] = val

        if ret['output'] == Outputs.threads or ret['output'] == Outputs.forums or ret['output'] == Outputs.dict:
            ret['accumulate'] = True
            ret['nousers'] = True

        return ret

    url_base = None #blank function

    def get_first_html(self,url,rq=None):
        return get_first_html(self,url,rq)

    def get_thread(self,url,rq=None,depth=0,**kwargs):
        settings = self.get_settings(**kwargs)
        return self.thread.get(settings,url,rq)

    def get_user(self,url,rq=None,depth=0,**kwargs):
        settings = self.get_settings(**kwargs)
        return self.user.get(settings,url,rq)

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
        return self.get_next(rq)

    def get_tag_next(self,rq):
        return self.get_next(rq)

    def go_through_page(self,settings,baseurl,rq,func_name,expr,depth):
        ret = []
        func = getattr(self,func_name)

        thread_count = 0

        for url in rq.search(expr).split('\n')[:-1]:
            if self.url_base:
                url = self.url_base_merge(baseurl,url)

            r = None
            if func_name == 'get_thread':
                thread_count += 1
                if settings['output'] == Outputs.threads:
                    r = url
                else:
                    r = func(url,None,depth+1,**settings)
            elif func_name == 'get_forum':
                r = []
                if settings['output'] == Outputs.forums:
                    r.append(url)
                if settings['pages_max_depth'] == 0 or settings['pages_max_depth'] > depth+1:
                    r2 = func(url,None,depth+1,**settings)
                    if r2:
                        r += r2

            if r and settings['accumulate']:
                if isinstance(r,list):
                    ret += r
                else:
                    ret.append(r)

            if settings['pages_threads_max'] != 0 and settings['pages_threads_max'] == thread_count:
                break

        return ret

    def go_through_pages(self,url,threads_expr,forums_expr,func_next,depth,rq=None,**kwargs):
        settings = self.get_settings(**kwargs)
        rq = self.get_first_html(url,rq)

        baseurl = None
        if self.url_base:
            baseurl = self.url_base(url)

        ret = []
        page = 0

        if forums_expr:
            if callable(forums_expr):
                ret = forums_expr(url,rq,**settings)
            else:
                r = self.go_through_page(settings,baseurl,rq,'get_forum',forums_expr,depth)
                if r:
                    ret += r

        if settings['output'] != Outputs.forums:
            while True:
                r = None

                if threads_expr:
                    r = self.go_through_page(settings,baseurl,rq,'get_thread',threads_expr,depth)

                if r and settings['accumulate']:
                    ret += r

                if not func_next:
                    break

                page += 1
                if settings['pages_max'] != 0 and page >= settings['pages_max']:
                    break
                nexturl = func_next(rq)
                if len(nexturl) == 0:
                    break
                if baseurl:
                    nexturl = self.url_base_merge(baseurl,nexturl)
                rq = self.get_first_html(nexturl)

        if settings['accumulate']:
            return ret
        return None

    def get_forum(self,url,rq=None,depth=0,**kwargs):
        return self.go_through_pages(
                url,
                self.forum_threads_expr,
                self.forum_forums_expr,
                self.get_forum_next,
                depth,
                rq,
                **kwargs)

    def get_tag(self,url,rq=None,depth=0,**kwargs):
        if not self.tag_threads_expr:
            return None
        return self.go_through_pages(
                url,
                self.tag_threads_expr,
                None,
                self.get_tag_next,
                depth,
                rq,
                **kwargs)

    def get_board(self,url,rq=None,depth=0,**kwargs):
        if not self.board_forums_expr:
            return self.get_tag(url,rq,depth,**kwargs)
        return self.go_through_pages(
                url,
                None,
                self.board_forums_expr,
                None,
                depth,
                rq,
                **kwargs)

    def guess(self,url,**kwargs):
        pass
