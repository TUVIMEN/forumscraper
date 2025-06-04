# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

import re
from pathlib import Path

from ..defs import reliq
from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor
from .identify import identify_phpbb


class phpbb(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    r"/((.*)?viewtopic\.php(.*)[\&\?]t=|.*-t)(\d+)",
                    4,
                )
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "phpbb-2+-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("phpbb/thread.reliq"))
            dict_add(ret, t)

            posts = []

            for rq in self.next(rq, settings, state, path):
                posts += rq.json(Path("phpbb/posts.reliq"))["posts"]

            for i in posts:
                i["userinfo"] = []
                for j in i["userinfo_temp"]:
                    t = j.split("\t")
                    t_len = len(t)
                    if t_len > 2 or (t_len == 0 and len(t[0]) == 0):
                        continue
                    if t_len < 2:
                        t.append("")
                    i["userinfo"].append({"key": t[0], "value": t[1]})
                i.pop("userinfo_temp")

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_phpbb

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'li; a .forumtitle href | "%(href)v\n" / sed "s/^\.\///;s/&amp;/\&/g"'
        )
        self.forum_threads_expr = reliq.expr(
            r'li; a .topictitle href | "%(href)v\n" / sed "s/^\.\///;s/&amp;/\&/g"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/(.*/)?viewtopic.php.*[\&\?]t=\d+"],
            },
            {
                "func": "get_forum",
                "exprs": [r"/(.*/)?viewforum.php"],
            },
            {
                "func": "get_board",
                "exprs": [r"/(.*/)?index.php"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(Path("phpbb/findroot.reliq"))
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        url = rq.search(r'[0] a href rel=next | "%(href)v" / sed "s/&amp;/\&/g;q"')
        if len(url) == 0:
            url = rq.search(
                r'div .topic-actions; div .pagination l@[1]; span l@[1]; E>(a|strong) -href=# | "%(href)v\n" / sed "/^$/{N;s/\n//;s/&amp;/\&/g;p;q}" "n"'
            )[:-1]

        if not re.search(r"&start=[0-9]+$", url):
            return ""
        return url

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = rq.json(Path("phpbb/forum.reliq"))

        categories = t["categories"]

        for i in t["categories"]:
            for j in i["forums"]:
                if j["posts"] == 0:
                    j["posts"] = j["posts2"]
                if j["topics"] == 0:
                    j["topics"] = j["topics"]
                j.pop("posts2")
                j.pop("topics2")

        threads = t["threads"]

        return {
            "format_version": "phpbb-2+-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
