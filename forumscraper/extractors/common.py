# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

import os
import json
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import batched

from ..utils import strtosha256, get_settings, url_valid
from ..net import Session
from ..defs import Outputs, reliq
from ..exceptions import *

common_exceptions = (
    AttributeError,
    ValueError,
    IndexError,
    KeyError,
    RequestError,
    AlreadyVisitedError,
)

BUNDLE_SIZE = 500


def write_file(path, data, settings):
    if settings["compress_func"] is None:
        with open(path, "w") as file:
            file.write(data)
    else:
        with open(path, "wb") as file:
            out = settings["compress_func"](data.encode())
            file.write(out)


def write_json(path, data, settings):
    write_file(path, json.dumps(data, separators=(",", ":")), settings)


def write_html(path, rq, settings):
    if not settings["html"]:
        return

    write_file(path + ".html", rq.get_data(), settings)


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

    if not isinstance(rq, reliq):
        rq = reliq(rq, ref=url)

    return rq


def state_add_url(typekey, url, state, settings):
    if settings["output"] | Outputs.save_urls:
        state["urls"][typekey].append(url)


def item_file_check_r(url, path_format, i_id, output, force):
    path = None

    if path_format and Outputs.write_by_id in output:
        path = path_format.format(i_id)
    elif Outputs.write_by_hash in output:
        path = strtosha256(url)

    if path and not force and os.path.exists(path) and os.path.getsize(path) != 0:
        return
    return path


def item_file_check(url, path_format, i_id, settings):
    return item_file_check_r(
        url, path_format, i_id, settings["output"], settings["force"]
    )


def get_baseurl(url):
    r = url_valid(url, base=True)
    if r is None:
        return ""

    base, rest = r
    p = base.find("//")
    if p == -1:
        return ""
    return base[p + 2 :]


class ItemExtractor:
    def __init__(self, session):
        self.path_format = "{}"
        self.match = [(None, 0)]
        self.trim = False

        self.session = session
        self.common_exceptions = common_exceptions

        self.get_next = None

    def state_add_url(self, keytype, url, state, settings):
        return state_add_url(keytype, url, state, settings)

    def get_url(self, url):
        return url

    def handle_error(self, exception, url, settings, for_pedantic=False):
        return handle_error(self, exception, url, settings, for_pedantic)

    def get_first_html(self, url, settings, state, rq=None, return_cookies=False):
        return get_first_html(self, url, settings, state, rq, return_cookies)

    def get_improper_url(self, url, rq, settings, state):
        print('improper url - "{}"'.format(url), file=settings["logger"])
        return [None, 0]

    def url_get_id(self, url):
        for i in self.match:
            r = url_valid(url, regex=i[0], base=True, matchwhole=True)
            if r is not None:
                return r[1][i[1]]

    def next(self, rq, settings, state, path, **kwargs):
        yield rq

        k = {"trim": self.trim}
        k.update(kwargs)
        page = 1

        while self.get_next:
            if (
                settings["thread_pages_max"] != 0
                and page >= settings["thread_pages_max"]
            ):
                break

            nexturl = self.get_next(rq)
            if nexturl is None:
                break

            try:
                rq = self.session.get_html(nexturl, settings, state, **k)
            except AlreadyVisitedError:
                break

            write_html(path + "-" + str(page), rq, settings)

            yield rq

            page += 1

    def get(self, typekey, url, settings, state, rq=None):
        outtype = settings["output"]
        if Outputs.only_urls_forums in outtype:
            return

        if Outputs.only_urls_threads in outtype:
            self.state_add_url(typekey, url, state, settings)
            return state

        i_id = self.url_get_id(url)

        if i_id is None:
            i_id = 0
            if Outputs.write_by_id in outtype:
                rq, i_id = self.get_improper_url(url, rq, settings, state)
                if not rq:
                    return

        path = item_file_check(url, self.path_format, i_id, settings)

        if not path and Outputs.data not in outtype:
            return state

        url = self.get_url(url)
        rq = self.get_first_html(url, settings, state, rq)

        write_html(path, rq, settings)

        contents = self.get_contents(rq, settings, state, url, i_id, path)
        if contents is None:
            return

        if Outputs.data in outtype:
            self.state_add_url(typekey, url, state, settings)
            state["data"][typekey].append(contents)

        if path:
            write_json(path, contents, settings)
            self.state_add_url(typekey, url, state, settings)
            state["files"][typekey].append(path)

        return state

    def get_contents(self, rq, settings, state, url, i_id, path):
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
        self.domains = []
        self.domain_guess_mandatory = False

        self.trim = False

        self.identify_func = None

        self.common_exceptions = common_exceptions

        self.settings = {
            "thread_pages_max": 0,
            "html": False,
            "pages_max": 0,
            "pages_max_depth": 0,
            "pages_threads_max": 0,
            "pages_forums_max": 0,
            "output": Outputs.write_by_id | Outputs.urls | Outputs.threads,
            "max_workers": 1,
            "undisturbed": False,
            "pedantic": False,
            # requests settings
            "force": False,
            "verify": True,
            "allow_redirects": False,
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
            "compress_func": None,
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

        if ret["user-agent"] is not None:
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

    def _get_item(self, typekey, url, obj, rq=None, state=None, depth=0, **kwargs):
        settings = self.get_settings(kwargs)
        state = self.create_state(state)
        try:
            return obj.get(typekey, url, settings, state, rq)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

    def get_thread(self, url, rq=None, state=None, depth=0, **kwargs):
        return self._get_item("threads", url, self.thread, rq, state, depth, **kwargs)

    def get_user(self, url, rq=None, state=None, depth=0, **kwargs):
        return self._get_item("users", url, self.user, rq, state, depth, **kwargs)

    get_next_page = None  # empty functions
    get_forum_next_page = None
    get_tag_next_page = None

    def get_next(self, rq):
        url = self.get_next_page(rq)
        if len(url) == 0:
            return
        return reliq.decode(rq.ujoin(url))

    def get_forum_next(self, rq):
        if self.get_forum_next_page is None:
            return self.get_next(rq)
        url = self.get_forum_next_page(rq)
        if len(url) == 0:
            return
        return reliq.decode(rq.ujoin(url))

    def get_tag_next(self, rq):
        if self.get_tag_next_page is None:
            return self.get_next(rq)
        url = self.get_tag_next_page(rq)
        if len(url) == 0:
            return
        return reliq.decode(rq.ujoin(url))

    def go_through_page_thread(self, url, settings, state, depth):
        try:
            return self.get_thread(url, None, state, depth + 1, **settings)
        except self.common_exceptions as ex:
            return self.handle_error(ex, url, settings)

    def go_through_page_threads(self, rq, settings, state, expr, depth):
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
        urls = list(map(lambda x: rq.ujoin(x).replace("&amp;", "&"), urls))

        if settings["max_workers"] > 1 and urls_len > 0:
            with ThreadPoolExecutor(max_workers=settings["max_workers"]) as executor:
                for i in batched(
                    urls, BUNDLE_SIZE
                ):  # I've seen threads with 11000 pages - this is necessary
                    for j in executor.map(
                        lambda x: self.go_through_page_thread(
                            x, settings, state, depth
                        ),
                        i,
                    ):
                        pass
        else:
            for url in urls:
                self.go_through_page_thread(url, settings, state, depth)

    def go_through_page_forums(self, rq, settings, state, expr, depth):
        max_forums = settings["pages_forums_max"]

        for num, url in enumerate(rq.search(expr).split("\n")[:-1]):
            if max_forums > 0 and num >= max_forums:
                break

            url = rq.ujoin(url).replace("&amp;", "&")

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
            self.go_through_page_forums(rq, settings, state, forums_expr, depth)

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
                self.go_through_page_threads(rq, settings, state, threads_expr, depth)

                if not func_next:
                    break

                page += 1
                if settings["pages_max"] > 0 and page >= settings["pages_max"]:
                    break
                nexturl = func_next(rq)
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
                url, "", "0", Outputs.write_by_hash, settings["force"]
            )
            if path is None:
                return
            path = "{}-{}".format(prefix, path)

        data = process_func(url, rq, settings, state)

        if Outputs.data in output:
            state["data"][typekey].append(data)
        if path:
            write_json(path, data, settings)
            write_html(path, rq, settings)
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

    def guess_in_domain(self, url):
        base = get_baseurl(url)
        if base == "":
            return

        if base in self.domains:
            return self

    def guess_search(self, url, found_domain, **kwargs):
        if found_domain is False:
            d = self.guess_in_domain(url)
            if d is not None:
                c = d.guess(url, found_domain=True)
                return c

            if self.domain_guess_mandatory is True:
                print(
                    "url {} was not found in domain list, refusing to guess".format(
                        url
                    ),
                    file=self.get_settings(kwargs)["logger"],
                )
                return

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

    def guess(self, url, rq=None, state=None, found_domain=False, **kwargs):
        rest = url_valid(url)
        if rest is None:
            return

        state = self.create_state(state)
        func = self.guess_search(url, found_domain, **kwargs)

        if found_domain:
            return func

        if func:
            state["scraper-method"] = func
            return func(url, rq=rq, state=state, **kwargs)
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

        if self.findroot_expr is None:
            return

        newurl = rq.search(self.findroot_expr)
        if len(newurl) == 0:
            return
        return rq.ujoin(newurl)

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

    def identify_page(self, url, rq, cookies):
        if self.identify_func is None:
            return

        d = self.guess_in_domain(url)
        if d is not None:
            return d

        if self.domain_guess_mandatory is True:
            return

        r = self.identify_func(url, rq, cookies)
        if r is True:
            return self
        if r is False:
            return
        return r


class ForumExtractorIdentify(ForumExtractor):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = self.listIdentify

        self.extractors = []

    def guess_in_domain(self, url):
        base = get_baseurl(url)
        if base == "":
            return

        for i in self.extractors:
            r = i.guess_in_domain(url)

            if r is not None:
                return r

    def listIdentify(self, url, rq, cookies):
        for i in self.extractors:
            if i.identify_func is None:
                continue

            r = i.identify_page(url, rq, cookies)
            if r is not None:
                return r

    def get_unknown(self, func_name, url, rq=None, state=None, **kwargs):
        settings = self.get_settings(kwargs)

        if Outputs.write_by_hash in settings["output"] and (
            func_name == "get_thread" or func_name == "get_user"
        ):
            if not item_file_check(url, None, None, settings):
                return

        state = self.create_state(state)

        try:
            r = self.get_first_html(url, settings, state, rq, return_cookies=True)
            cookies = {}
            if rq is None:
                rq = r[0]
                cookies = r[1]
            else:
                rq = r
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

    def guess(self, url, rq=None, state=None, **kwargs):
        return self.get_unknown("guess", url, rq, state, **kwargs)

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
