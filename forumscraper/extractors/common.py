# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
import json
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from reliq import reliq

from ..utils import strtosha256, get_settings, url_valid, url_merge
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


def handle_error(self, exception, url, settings, for_pedantic=False):
    if isinstance(exception, AlreadyVisitedError):
        return None

    undisturbed = settings["undisturbed"]
    pedantic = False
    if for_pedantic and settings["pedantic"]:
        pedantic = True

    failed = settings["failed"]
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


def get_first_html(extractor, url, settings, state, rq=None, return_cookies=False):
    if rq is None:
        return extractor.session.get_html(
            url, settings, state, extractor.trim, return_cookies
        )

    if isinstance(rq, reliq):
        return rq
    return reliq(rq)


def state_add_url(typekey, url, state, settings):
    if settings["output"] | Outputs.save_urls:
        state["urls"][typekey].append(url)


def item_file_check_r(url, path_format, i_id, output, force):
    path = None

    if path_format and Outputs.write_by_id in output:
        path = path_format.format(str(i_id))
    elif Outputs.write_by_hash in output:
        path = strtosha256(url)

    if path and not force and os.path.exists(path) and os.path.getsize(path) != 0:
        return
    return path


def item_file_check(url, path_format, i_id, settings):
    return item_file_check_r(
        url, path_format, i_id, settings["output"], settings["force"]
    )


class ItemExtractor:
    def __init__(self, session):
        self.path_format = "{}"
        self.match = [None, 0]
        self.trim = False

        self.session = session
        self.common_exceptions = common_exceptions

    def state_add_url(self, keytype, url, state, settings):
        return state_add_url(keytype, url, state, settings)

    def get_url(self, url):
        return url

    def handle_error(self, exception, url, settings, for_pedantic=False):
        return handle_error(self, exception, url, settings, for_pedantic)

    def get_first_html(self, url, settings, state, rq=None, return_cookies=False):
        return get_first_html(self, url, settings, state, rq, return_cookies)

    def get_improper_url(self, url, rq, settings, state):
        warnings.warn('improper url - "{}"'.format(url))
        return [None, 0]

    def get(self, typekey, url, settings, state, rq=None):
        outtype = settings["output"]
        if Outputs.only_urls_forums in outtype:
            return

        r = url_valid(url, regex=self.match[0], base=True)

        if Outputs.only_urls_threads in outtype:
            self.state_add_url(typekey, url, state, settings)
            return state

        if not r:
            rq, i_id = self.get_improper_url(url, rq, settings, state)
            if not rq:
                return
        else:
            i_id = int(r[1][self.match[1]])

        path = item_file_check(url, self.path_format, i_id, settings)

        if not path and Outputs.data not in outtype:
            return state

        url = self.get_url(url)
        rq = self.get_first_html(url, settings, state, rq)

        contents = self.get_contents(rq, settings, state, url, i_id)
        if contents is None:
            return

        if Outputs.data in outtype:
            self.state_add_url(typekey, url, state, settings)
            state["data"][typekey].append(contents)

        if path:
            with open(path, "w") as file:
                file.write(json.dumps(contents))
            self.state_add_url(typekey, url, state, settings)
            state["files"][typekey].append(path)

        return state

    def get_contents(self, rq, settings, state, url, i_id):
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
            "pages_forums_max": 0,
            "output": Outputs.write_by_id
            | Outputs.urls
            | Outputs.threads
            | Outputs.users,
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
        self.settings = self.get_settings(kwargs)

        if session:
            self.session = session
        else:
            self.session = Session(**self.settings)

        self.findroot_expr = None
        self.findroot_board = False
        self.findroot_board_expr = None

    def get_settings(self, settings):
        ret = get_settings(self.settings, **settings)

        if (
            Outputs.only_urls_threads in ret["output"]
            or Outputs.only_urls_forums in ret["output"]
        ):
            ret["force"] = True

        if ret["user-agent"]:
            ret["headers"].update({"User-Agent": ret["user-agent"]})

        return ret

    @staticmethod
    def create_state(state):
        if state:
            return state
        return {
            "files": {
                "boards": [],
                "tags": [],
                "forums": [],
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
            "data": {
                "boards": [],
                "tags": [],
                "forums": [],
                "threads": [],
                "users": [],
            },
            "visited": set(),
            "scraper": None,
            "scraper-method": None,
        }

    def handle_error(self, exception, url, settings, for_pedantic=False):
        return handle_error(self, exception, url, settings, for_pedantic)

    def get_first_html(self, url, settings, state, rq=None, return_cookies=False):
        return get_first_html(self, url, settings, state, rq, return_cookies)

    def get_thread(self, url, rq=None, state=None, depth=0, **kwargs):
        settings = self.get_settings(kwargs)
        state = self.create_state(state)
        try:
            return self.thread.get("threads", url, settings, state, rq)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

    def get_user(self, url, rq=None, state=None, depth=0, **kwargs):
        settings = self.get_settings(kwargs)
        state = self.create_state(state)
        try:
            return self.user.get("users", url, settings, state, rq)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

    get_next_page = None  # empty functions
    get_forum_next_page = None
    get_tag_next_page = None

    def get_next(self, url, rq):
        return url_merge(url, self.get_next_page(rq))

    def get_forum_next(self, url, rq):
        if self.get_forum_next_page is None:
            return self.get_next(url, rq)
        return url_merge(url, self.get_forum_next_page(rq))

    def get_tag_next(self, url, rq):
        if self.get_tag_next_page is None:
            return self.get_next(url, rq)
        return url_merge(url, self.get_tag_next_page(rq))

    def go_through_page_thread(self, url, settings, state, depth):
        try:
            return self.get_thread(url, None, state, depth + 1, **settings)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

    def go_through_page_threads(self, refurl, rq, settings, state, expr, depth):
        if (
            Outputs.threads not in settings["output"]
            and Outputs.only_urls_threads not in settings["output"]
        ):
            return
        urls = rq.search(expr).split("\n")[:-1]
        urls_len = len(urls)
        if (
            settings["pages_threads_max"] > 0
            and urls_len >= settings["pages_threads_max"]
        ):
            urls_len = settings["pages_threads_max"]
            urls = urls[:urls_len]

        urls_len = len(urls)
        urls = list(map(lambda x: url_merge(refurl, x), urls))

        if settings["max_workers"] > 1 and urls_len > 0:
            with ThreadPoolExecutor(max_workers=settings["max_workers"]) as executor:
                list(
                    executor.map(
                        lambda x: self.go_through_page_thread(
                            x, settings, state, depth
                        ),
                        urls,
                    )
                )
        else:
            for url in urls:
                self.go_through_page_thread(url, settings, state, depth)

    def go_through_page_forums(self, refurl, rq, settings, state, expr, depth):
        max_forums = settings["pages_forums_max"]

        for num, url in enumerate(rq.search(expr).split("\n")[:-1]):
            if max_forums > 0 and num >= max_forums:
                break

            url = url_merge(refurl, url)

            if (
                settings["pages_max_depth"] == 0
                or settings["pages_max_depth"] > depth + 1
            ):
                try:
                    self.get_forum(url, None, state, depth + 1, **settings)
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
        process_func=None,
        **kwargs,
    ):
        settings = self.get_settings(kwargs)
        state = self.create_state(state)
        try:
            rq = self.get_first_html(url, settings, state, rq)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

        page = 0
        state_add_url(typekey, url, state, settings)

        if process_func:
            process_func(url, rq, settings, state)

        if forums_expr:
            self.go_through_page_forums(url, rq, settings, state, forums_expr, depth)

        if (
            threads_expr
            and (
                Outputs.threads in settings["output"]
                or Outputs.only_urls_threads in settings["output"]
                or Outputs.forums in settings["output"]
                or Outputs.tags
            )
            and Outputs.only_urls_forums not in settings["output"]
        ):
            while True:
                self.go_through_page_threads(
                    url, rq, settings, state, threads_expr, depth
                )

                if not func_next:
                    break

                page += 1
                if settings["pages_max"] > 0 and page >= settings["pages_max"]:
                    break
                nexturl = func_next(url, rq)
                if nexturl is None:
                    break
                try:
                    rq = self.get_first_html(nexturl, settings, state)
                except self.common_exceptions as ex:
                    self.handle_error(ex, nexturl, settings)
                    break

                if process_func:
                    process_func(nexturl, rq, settings, state)

        return state

    def process_forum_r(self, url, rq, settings, state):
        pass

    def process_tag_r(self, url, rq, settings, state):
        pass

    def process_board_r(self, url, rq, settings, state):
        pass

    def process_page(
        self, url, rq, settings, state, prefix, typekey, process_func, otype
    ):
        output = settings["output"]
        if otype not in output or (
            output & Outputs.writers == 0 and Outputs.data not in output
        ):
            return

        path = None

        if output & Outputs.writers != 0:
            path = item_file_check_r(
                url, "", 0, Outputs.write_by_hash, settings["force"]
            )
            if path is None:
                return
            path = "{}-{}".format(prefix, path)

        data = process_func(url, rq, settings, state)

        if Outputs.data in output:
            state["data"][typekey].append(data)
        if path:
            with open(path, "w") as file:
                file.write(json.dumps(data))
            state["files"][typekey].append(path)

    def process_forum(self, url, rq, settings, state):
        return self.process_page(
            url,
            rq,
            settings,
            state,
            "f",
            "forums",
            self.process_forum_r,
            Outputs.forums,
        )

    def process_tag(self, url, rq, settings, state):
        return self.process_page(
            url,
            rq,
            settings,
            state,
            "t",
            "tags",
            self.process_tag_r,
            Outputs.tags,
        )

    def process_board(self, url, rq, settings, state):
        return self.process_page(
            url,
            rq,
            settings,
            state,
            "b",
            "boards",
            self.process_board_r,
            Outputs.boards,
        )

    def get_forum(self, url, rq=None, state=None, depth=0, process_func=None, **kwargs):
        if process_func is None:
            process_func = self.process_forum
        return self.go_through_pages(
            "forums",
            url,
            self.forum_threads_expr,
            self.forum_forums_expr,
            self.get_forum_next,
            depth,
            rq,
            state,
            process_func,
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
            self.process_tag,
            **kwargs,
        )

    def get_board(self, url, rq=None, state=None, depth=0, **kwargs):
        if not self.board_forums_expr:
            return self.get_forum(url, rq, state, depth, self.process_board, **kwargs)
        return self.go_through_pages(
            "boards",
            url,
            None,
            self.board_forums_expr,
            None,
            depth,
            rq,
            state,
            self.process_board,
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
        return

    def guess(self, url, state=None, **kwargs):
        rest = url_valid(url)
        if rest is None:
            return

        state = self.create_state(state)
        func = self.guess_search(rest)

        if func:
            state["scraper-method"] = func
            return func(url, state=state, **kwargs)
        return

    def findroot_r(self, url, rq, teststate, settings):
        rest = url_valid(url, base=True)
        if rest is None:
            return

        if self.findroot_board:
            settings["output"] = Outputs.only_urls_forums
            settings["pages_max_depth"] = 1
            self.get_board(
                url,
                rq,
                teststate,
                **settings,
            )
            if len(teststate["urls"]["forums"]) > 0 and (
                not self.findroot_board_expr
                or (
                    len(rest) == 0
                    or rest == "/"
                    or re.search(
                        self.findboard_board_expr,
                        rest,
                    )
                )
            ):
                return url

        newurl = rq.search(self.findroot_expr)
        return url_merge(url, newurl)

    def findroot(self, url, rq=None, state=None, **kwargs):
        settings = self.get_settings(kwargs)
        teststate = self.create_state(None)

        try:
            rq = self.get_first_html(url, settings, teststate, rq)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

        url = self.findroot_r(url, rq, teststate, settings)
        if url is None:
            return

        url = re.sub(r"[?&](sid|PHPSESSID)=[a-zA-Z0-9]+", r"", url)
        index1 = url.find("?")
        index2 = url.find("&")
        if index1 == -1 and index2 != -1:
            url = url[:index2] + "?" + url[(index2 + 1) :]
        url = re.sub(r"&", r"?", url, count=1)
        if url[-1] == "?":
            url = url[:-1]
        return url


class ForumExtractorIdentify(ForumExtractor):
    def identify_page(self, url, rq, cookies):
        pass

    def get_unknown(self, func_name, url, rq=None, state=None, **kwargs):
        settings = self.get_settings(kwargs)

        if Outputs.write_by_hash in settings["output"] and (
            func_name == "get_thread" or func_name == "get_user"
        ):
            if not item_file_check(url, None, None, settings):
                return

        state = self.create_state(state)

        try:
            rq, cookies = self.get_first_html(url, settings, state, rq, True)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

        forum = self.identify_page(url, rq, cookies)
        if forum is None:
            return
        state["scraper"] = forum

        if func_name is None:
            return state

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

    def identify(self, url, rq=None, state=None, **kwargs):
        r = self.get_unknown(None, url, rq, None, **kwargs)
        if r is None:
            return
        return r["scraper"]

    def findroot(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("findroot", url, rq, None, **kwargs)
