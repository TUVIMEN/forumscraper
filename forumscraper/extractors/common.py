# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
import json
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from reliq import reliq

from ..utils import strtosha256, get_settings, url_valid
from ..net import Session
from ..enums import Outputs
from ..exceptions import *

common_exceptions = (
    AttributeError,
    ValueError,
    IndexError,
    KeyError,
    RequestError,
    AlreadyVisitedError,
)


def handle_error(self, exception, url, for_pedantic=False, **kwargs):
    if isinstance(exception, AlreadyVisitedError):
        return None

    undisturbed = kwargs["undisturbed"]
    pedantic = False
    if for_pedantic and kwargs["pedantic"]:
        pedantic = True

    failed = kwargs["failed"]
    msg = "{} {}".format(url, exception.args[0])

    if failed:
        if isinstance(failed, list):
            failed.append(msg)
        else:
            print(msg, file=failed)

    if not undisturbed and (failed is None or pedantic):
        if isinstance(exception, RequestError):
            raise RequestError(msg)
        raise exception
    return


def get_first_html(extractor, url, rq=None, return_cookies=False, **kwargs):
    if rq is None:
        return extractor.session.get_html(url, extractor.trim, return_cookies, **kwargs)

    if isinstance(rq, reliq):
        return rq
    return reliq(rq)


def create_state(state):
    if state:
        return state
    return {
        "files": {
            "threads": [],
            "users": [],
        },
        "urls": {
            "threads": [],
            "users": [],
            "reactions": [],
            "forums": [],
            "tags": [],
            "boards": [],
        },
        "data": {"threads": [], "users": []},
        "scraper": None,
        "scraper-method": None,
    }


def state_add_url(typekey, url, state, **kwargs):
    if kwargs["output"] | Outputs.save_urls:
        state["urls"][typekey].append(url)


class ItemExtractor:
    def __init__(self, session):
        self.path_format = "{}"
        self.match = [None, 0]
        self.trim = False

        self.session = session
        self.common_exceptions = common_exceptions

    def state_add_url(self, keytype, url, state, **kwargs):
        return state_add_url(keytype, url, state, **kwargs)

    def get_url(self, url):
        return url

    def handle_error(self, exception, url, for_pedantic=False, **kwargs):
        return handle_error(self, exception, url, for_pedantic, **kwargs)

    def get_first_html(self, url, rq=None, return_cookies=False, **kwargs):
        return get_first_html(self, url, rq, return_cookies, **kwargs)

    def get_improper_url(self, url, rq, **kwargs):
        warnings.warn('improper url - "{}"'.format(url))
        return [None, 0]

    def get(self, typekey, url, state, rq=None, **kwargs):
        outtype = kwargs["output"]
        if Outputs.only_urls_forums in outtype:
            return

        r = url_valid(url, self.match[0], True)

        if Outputs.only_urls_threads in outtype:
            self.state_add_url(typekey, url, state, **kwargs)
            return state

        if not r:
            rq, t_id = self.get_improper_url(url, rq, **kwargs)
            if not rq:
                return
        else:
            t_id = int(r[1][self.match[1]])

        path = None

        if Outputs.write_by_id in outtype:
            path = self.path_format.format(str(t_id))
        elif Outputs.write_by_hash in outtype:
            path = strtosha256(url)
        elif Outputs.data not in outtype:
            return state

        file = None
        if (
            path
            and not kwargs["force"]
            and os.path.exists(path)
            and os.path.getsize(path) != 0
        ):
            return

        url = self.get_url(url)
        rq = self.get_first_html(url, rq, **kwargs)

        contents = self.get_contents(rq, state, url, t_id, **kwargs)
        if not contents:
            return

        if Outputs.data in outtype:
            self.state_add_url(typekey, url, state, **kwargs)
            state["data"][typekey].append(contents)

        if path:
            with open(path, "w") as file:
                file.write(json.dumps(contents))
                file.close()

                self.state_add_url(typekey, url, state, **kwargs)
                state["files"][typekey].append(path)

        return state

    def get_contents(self, rq, state, url, t_id, **kwargs):
        pass


class ForumExtractor:
    def __init__(self, session=None, **kwargs):
        self.thread = None
        self.user = None

        self.forum_threads_expr = None
        self.forum_forums_expr = None
        self.tag_threads_expr = None
        self.board_forums_expr = None
        self.guesslist = []

        self.trim = False

        self.common_exceptions = common_exceptions

        self.settings = {
            "thread_pages_max": 0,
            "pages_max": 0,
            "pages_max_depth": 0,
            "pages_threads_max": 0,
            "output": Outputs.write_by_id | Outputs.urls,
            "nousers": False,
            "noreactions": False,
            "max_workers": 1,
            "undisturbed": False,
            "pedantic": False,
            # requests settings
            "force": False,
            "verify": True,
            "timeout": 120,
            "proxies": {},
            "headers": {},
            "cookies": {},
            # net settings
            "user-agent": None,
            "wait": 0,
            "wait_random": 0,
            "logger": None,
            "failed": None,
            "retries": 3,
            "retry_wait": 60,
            "force": False,
        }
        self.settings = self.get_settings(**kwargs)

        if session:
            self.session = session
        else:
            self.session = Session(**self.settings)

    def get_settings(self, **kwargs):
        ret = get_settings(self.settings, **kwargs)

        if (
            Outputs.only_urls_threads in ret["output"]
            or Outputs.only_urls_forums in ret["output"]
        ):
            ret["force"] = True

        if ret["user-agent"]:
            ret["headers"].update({"User-Agent": ret["user-agent"]})

        return ret

    url_base = None  # blank function

    def handle_error(self, exception, url, for_pedantic=False, **kwargs):
        return handle_error(self, exception, url, for_pedantic, **kwargs)

    def get_first_html(self, url, rq=None, return_cookies=False, **kwargs):
        return get_first_html(self, url, rq, return_cookies, **kwargs)

    def get_thread(self, url, rq=None, state=None, depth=0, **kwargs):
        settings = self.get_settings(**kwargs)
        state = create_state(state)
        return self.thread.get("threads", url, state, rq, **settings)

    def get_user(self, url, rq=None, state=None, depth=0, **kwargs):
        settings = self.get_settings(**kwargs)
        state = create_state(state)
        return self.user.get("users", url, state, rq, **settings)

    @staticmethod
    def url_base_merge(urlbase, url):
        if len(url) == 0 or len(urlbase) == 0 or url_valid(url):
            return url

        if urlbase[-3:] == "/./":
            urlbase = urlbase[:-3]
        if urlbase[-1] == "/":
            urlbase = urlbase[:-1]
        if url[0:2] == "./":
            url = url[2:]
        if url[0] == "/":
            url = url[1:]

        return "{}/{}".format(urlbase, url)

    def get_next(self, rq):
        pass

    def get_forum_next(self, rq):
        return self.get_next(rq)

    def get_tag_next(self, rq):
        return self.get_next(rq)

    def go_through_page_thread(self, url, state, depth, **kwargs):
        try:
            return self.get_thread(url, None, state, depth + 1, **kwargs)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, **kwargs)

    def go_through_page_threads(self, baseurl, rq, state, expr, depth, **kwargs):
        thread_count = 0

        urls = rq.search(expr).split("\n")[:-1]
        urls_len = len(urls)
        if kwargs["pages_threads_max"] > 0 and urls_len >= kwargs["pages_threads_max"]:
            urls = urls[:urls_len]

        urls_len = len(urls)
        if self.url_base:
            urls = list(map(lambda x: self.url_base_merge(baseurl, x), urls))

        if kwargs["max_workers"] > 1 and urls_len > 0:
            with ThreadPoolExecutor(max_workers=kwargs["max_workers"]) as executor:
                list(
                    executor.map(
                        lambda x: self.go_through_page_thread(
                            x, state, depth, **kwargs
                        ),
                        urls,
                    )
                )
        else:
            for url in urls:
                thread_count += 1
                self.go_through_page_thread(url, state, depth, **kwargs)

    def go_through_page_forums(self, baseurl, rq, state, expr, depth, **kwargs):
        for url in rq.search(expr).split("\n")[:-1]:
            if self.url_base:
                url = self.url_base_merge(baseurl, url)

            if kwargs["pages_max_depth"] == 0 or kwargs["pages_max_depth"] > depth + 1:
                try:
                    self.get_forum(url, None, state, depth + 1, **kwargs)
                except (RequestError, AlreadyVisitedError):
                    continue

    def go_through_pages(
        self,
        typekey,
        url,
        threads_expr,
        forums_expr,
        func_next,
        depth,
        rq=None,
        state=None,
        **kwargs,
    ):
        settings = self.get_settings(**kwargs)
        state = create_state(state)
        rq = self.get_first_html(url, rq, **settings)

        baseurl = None
        if self.url_base:
            baseurl = self.url_base(url)

        page = 0
        state_add_url(typekey, url, state, **settings)

        if forums_expr:
            self.go_through_page_forums(
                baseurl, rq, state, forums_expr, depth, **settings
            )

        if threads_expr and Outputs.only_urls_forums not in settings["output"]:
            while True:
                self.go_through_page_threads(
                    baseurl, rq, state, threads_expr, depth, **settings
                )

                if not func_next:
                    break

                page += 1
                if settings["pages_max"] > 0 and page >= settings["pages_max"]:
                    break
                nexturl = func_next(rq)
                if len(nexturl) == 0:
                    break
                if baseurl:
                    nexturl = self.url_base_merge(baseurl, nexturl)
                try:
                    rq = self.get_first_html(nexturl, **settings)
                except RequestError as ex:
                    self.handle_error(ex, nexturl, **settings)
        return state

    def get_forum(self, url, rq=None, state=None, depth=0, **kwargs):
        return self.go_through_pages(
            "forums",
            url,
            self.forum_threads_expr,
            self.forum_forums_expr,
            self.get_forum_next,
            depth,
            rq,
            state,
            **kwargs,
        )

    def get_tag(self, url, rq=None, state=None, depth=0, **kwargs):
        if not self.tag_threads_expr:
            return None
        return self.go_through_pages(
            "tags",
            url,
            self.tag_threads_expr,
            None,
            self.get_tag_next,
            depth,
            rq,
            state,
            **kwargs,
        )

    def get_board(self, url, rq=None, state=None, depth=0, **kwargs):
        if not self.board_forums_expr:
            return self.get_tag(url, rq, state, depth, **kwargs)
        return self.go_through_pages(
            "boards",
            url,
            None,
            self.board_forums_expr,
            None,
            depth,
            rq,
            state,
            **kwargs,
        )

    def guess_search(self, url):
        func = None
        for i in self.guesslist:
            func = getattr(self, i["func"])
            exprs = i["exprs"]

            if exprs:
                for expr in exprs:
                    if re.search(expr, url):
                        return func
            else:
                return func

    def guess(self, url, state=None, **kwargs):
        rest = url_valid(url)
        if not rest:
            return None

        state = create_state(state)
        func = self.guess_search(rest)

        if func:
            state["scraper-method"] = func
            return func(url, state=state, **kwargs)
        return None


class ForumExtractorIdentify(ForumExtractor):
    def identify(self, url, rq, cookies):
        pass

    def get_unknown(self, func_name, url, rq=None, state=None, **kwargs):
        settings = self.get_settings(**kwargs)
        state = create_state(state)

        rq, cookies = self.get_first_html(url, rq, True, **settings)
        forum = self.identify(url, rq, cookies)
        if not forum:
            return
        state["scraper"] = forum

        func = getattr(forum, func_name)
        state["scraper-method"] = func
        return func(url, rq, state, **settings)

    def get_thread(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("get_thread", url, rq, state, **kwargs)

    def get_user(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("get_user", url, rq, state, **kwargs)

    def get_forum(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("get_forum", url, rq, state, **kwargs)

    def get_tag(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("get_tag", url, rq, state, **kwargs)

    def get_board(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("get_board", url, rq, state, **kwargs)
