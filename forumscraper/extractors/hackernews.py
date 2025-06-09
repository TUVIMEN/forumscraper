# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re
import copy

from ..defs import reliq
from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor, write_html
from .identify import identify_hackernews


def get_comments(rq):
    return rq.json(Path("hackernews/comments.reliq"))["comments"]


def get_post(rq):
    return rq.json(Path("hackernews/post.reliq"))


def get_page(rq):
    threads = []
    posts_list = rq.search(r'[1] table -#hnmain; tr l@[1] | "%A\0"').split("\0")[:-1]
    size = len(posts_list)
    i = 0
    while i < size and size - i >= 3:
        inp = posts_list[i] + posts_list[i + 1] + posts_list[i + 2]

        post = get_post(reliq(inp, ref=rq.ref))
        threads.append(post)

        i += 3

    return threads


def go_through(self, rq, settings, state, path, func):
    r = []
    page = 1
    for rq in self.next(rq, settings, state, path):
        write_html(path + "-" + str(page), rq, settings)
        page += 1
        r += func(rq)
    return r


def get_all_pages(self, rq, settings, state, path):
    return go_through(self, rq, settings, state, path, get_page)


def get_all_comments(self, rq, settings, state, path):
    return go_through(self, rq, settings, state, path, get_comments)


class hackernews(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"^https://news.ycombinator.com/user\?id=([^&]+)"),
                    1,
                )
            ]
            self.path_format = "m-{}"
            self.trim = True

        def subitem(self, out, name, ref, settings, state, path, func):
            out[name + "-link"] = reliq.urljoin(ref, out[name + "-link"])

            rsettings = copy.copy(settings["requests"])
            rsettings["trim"] = True

            rq = self.session.get_html(out[name + "-link"], **rsettings)
            out[name] = func(self, rq, settings, state, path + "-" + name)

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "hackernews-user", "url": url, "id": i_id}
            ref = rq.ref

            t = rq.json(Path("hackernews/user.reliq"))

            self.subitem(t, "submissions", ref, settings, state, path, get_all_pages)
            self.subitem(t, "comments", ref, settings, state, path, get_all_comments)
            self.subitem(t, "favorites", ref, settings, state, path, get_all_pages)

            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"^https://news.ycombinator.com/item\?id=(\d+)"),
                    1,
                )
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "hackernews-thread", "url": url, "id": i_id}

            fatitem = rq.filter(r"[0] table .fatitem")
            t = get_post(fatitem)
            dict_add(ret, t)

            ret["comments"] = get_all_comments(
                self, rq, settings, state, path + "-comments"
            )
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_hackernews

        self.trim = True

        self.thread = self.Thread(self.session)
        self.user = self.User(self.session)
        self.user.get_next = self.get_next
        self.thread.user = self.user
        self.thread.get_next = self.get_next

        self.domains = ["news.ycombinator.com"]
        self.domain_guess_mandatory = True

        self.forum_threads_expr = reliq.expr(
            r'span .subline; a [0] i@"&nbsp;comment" href | "%(href)v\n"'
        )
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/item\?id="],
            },
            {
                "func": "get_user",
                "exprs": [r"/user\?id="],
            },
            {
                "func": "get_forum",
                "exprs": [
                    r"/(news|newest|front|show(new)?|ask|jobs)($|\?p=)",
                    r"/(favorites|submitted)\?id=",
                ],
            },
        ]

    def get_next_page(self, rq):
        return rq.search(r'[0] a .morelink rel=next href | "%(href)v"')

    def process_forum_r(self, url, rq, settings, state):
        threads = get_page(rq)

        return {
            "format_version": "hackernews-forum",
            "url": url,
            "threads": threads,
        }
