# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re

from ..defs import reliq
from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor
from .identify import identify_xmb


class xmb(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(.*/)?viewthread\.php\?tid=(\d+)$"),
                    2,
                )
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "xmb-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("xmb/thread.reliq"))
            dict_add(ret, t)

            posts = []

            for rq in self.next(rq, settings, state, path):
                for i in rq.search(
                    r'tr -class bgcolor | "%A\a" / tr "\n\r\t" "   " tr "\a" "\n" sed "N;N;s/\n/\t/g"'
                ).split("\n")[:-1]:
                    tr = i.split("\t")
                    post = {}

                    try:
                        post["body"] = reliq(tr[1]).search(r'td .tablerow | "%i"')
                        post["homepage"] = reliq(tr[2]).search(
                            r'a href title=w>homepage | "%(href)v"'
                        )
                        t = reliq(tr[0]).json(Path("xmb/post.reliq"))
                    except (IndexError, AttributeError):
                        continue

                    for j in ["date", "user", "postid"]:
                        post[j] = t[j]

                    fields = t["fields"]

                    for j, g in enumerate(
                        [
                            "rank",
                            "stars",
                            "avatar",
                            "posts",
                            "registered",
                            "location",
                            "mood",
                        ]
                    ):
                        try:
                            if g == "stars":
                                post[g] = len(fields[j])
                            elif g == "avatar":
                                post[g] = (
                                    rq.ujoin(fields[j]) if len(fields[j]) > 0 else ""
                                )
                            elif g == "posts":
                                try:
                                    post[g] = int(fields[j])
                                except ValueError:
                                    post[g] = fields[j]
                            else:
                                post[g] = fields[j]
                        except IndexError:
                            pass

                    posts.append(post)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_xmb

        self.trim = True

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'font .mediumtxt; a l@[1] href=Ea>"(forumdisplay\.php\?|^[0-9]+/)" | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'font .mediumtxt; a href=b>"viewthread.php" l@[1] | "%(href)v\n"'
        )
        self.board_forums_expr = reliq.expr(
            r'a href=Ea>"(forumdisplay\.php\?|^[0-9]+/)" | "%(href)v\n" / sed "s#/./#/#"'
        )
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/(.*/)?viewthread.php\?tid=\d+$"],
            },
            {
                "func": "get_forum",
                "exprs": [r"/(.*/)?forumdisplay.php\?fid=\d+$", "/forums?/.+"],
            },
            {
                "func": "get_board",
                "exprs": [r"/(.*/)?index.php\?gid=\d+$"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(Path("xmb/findroot.reliq"))
        self.findroot_board = False
        self.findroot_board_expr = None

    def get_next_page(self, rq):
        url = rq.search(
            r'''td .multi; {
                [0] a href rel=next | "%(href)v\n",
                strong; [0] u ssub@; a href | "%(href)v\n"
            } / sed "s/&amp;/\&/g;q" tr "\n"'''
        )
        if not re.search(r"&page=", url):
            return ""
        return url

    def process_board_r(self, url, rq, settings, state):
        t = rq.json(Path("xmb/board.reliq"))

        groups = []
        group_name = None
        group_link = None
        group_forums = []
        isfirst = True
        for i in t["categories"]:
            if len(i["category"]):
                if not isfirst:
                    if group_link is None or not group_link.endswith(
                        "misc.php?action=online"
                    ):
                        groups.append(
                            {
                                "name": group_name,
                                "link": group_link,
                                "forums": group_forums,
                            }
                        )
                    group_forums = []
                group_name = i["category"]
                group_link = i["category_link"]
                continue

            if len(i["name"]) == 0:
                continue

            lastpost = i["lastpost"]
            if lastpost["user_link"] == lastpost["link"]:
                lastpost["user_link"] = None

            i.pop("category")
            i.pop("category_link")

            group_forums.append(i)

            isfirst = False

        if len(group_forums) != 0 and (
            group_link is None or not group_link.endswith("misc.php?action=online")
        ):
            groups.append(
                {"name": group_name, "link": group_link, "forums": group_forums}
            )

        return {"format_version": "xmb-board", "url": url, "groups": groups}

    def process_forum_r(self, url, rq, settings, state):
        threads = list(
            filter(
                lambda x: len(x["link"]) > 0,
                rq.json(Path("xmb/forum-threads.reliq"))["threads"],
            )
        )
        forums = rq.json(Path("xmb/forum-forums.reliq"))["forums"]

        return {
            "format_version": "xmb-forum",
            "url": url,
            "forums": forums,
            "threads": threads,
        }
