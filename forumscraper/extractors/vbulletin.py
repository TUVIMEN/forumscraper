# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re

from ..defs import reliq
from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor
from .identify import identify_vbulletin


class vbulletin(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    r"/([0-9]+)-[^/]*/?$",
                    1,
                ),
                (
                    r"/.*([?&](t=)?|-)([0-9]+)[^/]*/?$",
                    3,
                ),
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "vbulletin-3+-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("vbulletin/thread.reliq"))
            dict_add(ret, t)

            posts = []

            for rq in self.next(rq, settings, state, path):
                t = rq.json(Path("vbulletin/posts.reliq"))
                posts += t["posts"]

            outposts = []
            for i in posts:
                thankedby = []
                for j in range(len(i["thankedby_users"])):
                    thankedby.append(
                        {
                            "user": i["thankedby_users"][j],
                            "date": (
                                i["thankedby_dates"][j]
                                if j < len(i["thankedby_dates"])
                                else ""
                            ),
                        }
                    )
                i.pop("thankedby_users")
                i.pop("thankedby_dates")
                i["thankedby"] = thankedby

                if i["date"] == "" and i["id"] == 0 and i["content"] == "":
                    if len(outposts) > 0:
                        outposts[len(outposts) - 1]["thankedby"] += thankedby
                    continue

                if len(i["attachments"]) < len(i["attachments2"]):
                    i["attachments"] = i["attachments2"]
                i.pop("attachments2")

                user = i["user"]
                custom = user["custom1"]
                if len(custom) < len(user["custom2"]):
                    custom = user["custom2"]
                if len(custom) < len(user["custom3"]):
                    custom = user["custom3"]
                if len(custom) < len(user["custom4"]):
                    custom = []
                    for j in user["custom4"]:
                        tokens = j.split(":", 1)
                        if len(tokens) < 2:
                            custom.append({"key": None, "value": j})
                        else:
                            custom.append(
                                {"key": tokens[0].strip(), "value": tokens[1].strip()}
                            )
                user.pop("custom1")
                user.pop("custom2")
                user.pop("custom3")
                user.pop("custom4")
                user["custom"] = custom

                outposts.append(i)

            ret["posts"] = outposts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_vbulletin

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.trim = True

        self.forum_forums_expr = reliq.expr(Path("vbulletin/forum-threads.reliq"))
        self.forum_threads_expr = reliq.expr(
            r'a ( #b>thread_title_ )( .topic-title ) href | "%(href)v\n" / sed "s/&amp;/\&/g"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [
                    r"/showthread\.php\?",
                ],
            },
            {
                "func": "get_forum",
                "exprs": [r"/forumdisplay\.php(\?|/)", "/forums?/[^/]+/?$"],
            },
            {
                "func": "get_thread",
                "exprs": [
                    r"(/[^/]+){2,}/\d+-[^/]+$",
                    r"(/[^/]+){2,}/[^/]+-\d+(\.html|/)$",
                ],
            },
            {"func": "get_forum", "exprs": [r"(/[^/]+){3,}/$"]},
            {
                "func": "get_board",
                "exprs": [r"/forums?(/|\.php(\?[^/]*)?)$"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(Path("vbulletin/findroot.reliq"))
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|(index|forum)\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        url = rq.search(Path("vbulletin/next-page.reliq"))

        return url

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def ifurl(self, url, rq):
        if url.find("/") == -1:
            return url
        return rq.ujoin(url)

    def process_forum_r(self, url, rq, settings, state):
        t = rq.json(Path("vbulletin/forum.reliq"))

        categories = []
        prevcat = None
        for i in t["categories"]:
            c = {}
            header = i["header"]
            if header["name"] == "" and header["link"] == "":
                header = i["header2"]
            i.pop("header")
            i.pop("header2")

            c["name"] = header["name"]
            c["link"] = header["link"]
            c["description"] = header["description"]

            forums = []
            for j in i["forums"]:
                if j["title"] == "" and j["link"] == "":
                    continue

                j["status"] = self.ifurl(j["status"], rq)

                for k in j["childboards"]:
                    k["icon"] = self.ifurl(k["icon"], rq)

                lastpost = j["lastpost"]
                forums.append(j)

            if prevcat is not None and c["link"] == prevcat["link"]:
                prevcat["forums"] += forums
            elif (
                prevcat is not None
                and c["link"] is None
                and (
                    len(prevcat["forums"]) == 0
                    or (
                        len(prevcat["forums"]) == 1
                        and prevcat["forums"][0]["link"] == prevcat["link"]
                    )
                )
            ):
                prevcat["forums"] = forums
            else:
                c["forums"] = forums
                prevcat = c
                categories.append(c)

        threads = []
        for i in t["threads"]:
            if i["link"] == "" and i["title"] == "" and i["user"] == "":
                continue

            for j, icon in enumerate(i["detailicons"]):
                i["detailicons"][j] = self.ifurl(icon, rq)

            lastpost = i["lastpost"]
            if (
                lastpost["user"] == ""
                and lastpost["user_link"] == ""
                and lastpost["date"] == ""
            ):
                lastpost = i["lastpost2"]
            if lastpost["link"] == "":
                lastpost["link"] = i["lastpost_link"]
            i.pop("lastpost")
            i.pop("lastpost2")
            i.pop("lastpost_link")
            i["lastpost"] = lastpost

            threads.append(i)

        return {
            "format_version": "vbulletin-3+-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
