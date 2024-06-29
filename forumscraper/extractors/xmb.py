# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor


class xmb(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/(.*/)?viewthread\.php\?tid=(\d+)$"),
                2,
            ]
            self.trim = True

        def get_contents(self, settings, rq, url, t_id):
            ret = {"format_version": "xmb-thread", "url": url, "id": t_id}
            page = 0
            baseurl = self.url_base(url)

            t = json.loads(
                rq.search(
                    r"""
                .title td .nav -style | "%i" / sed "s/.* &raquo; //",
                .path.a td .nav -style; a | "%i\n"
            """
                )
            )
            dict_add(ret, t)

            posts = []
            expr = reliq.expr(
                r"""
                .date td -rowspan l@[1]; a m@E>".+ .+ .+" | "%i" / sed "s/^[^ ]\+ [^ ]\+ //",
                td rowspan l@[1]; {
                    .user font .mediumtxt; * c@[0] | "%i",
                     div .smalltxt; {
                        .postid.u a name l@[1] | "%(name)v" / sed "s/^pid//",
                        .fields.a * l@[0] | "%i\n" / sed '
                            s/^<a [^>]*><\/a>//
                            s/<br \/>/\n/
                            s/<img src="images[^>]*\/>/*/g
                            s/<br \/>.*<hr \/>/\n/
                            s/<div [^>]*>\(<img [^>]*src="\([^"]*\)"[^>]*\/>\)\?<\/div><br \/>/\2\n/
                            s/<br \/>[^:]*: //
                            s/<br \/>[^:]*: /\n/
                            /<br \/>[^:]*: /!s/<br \/>/\n\0/
                            s/<br \/>[^:]*: \(<div [^>]*><img [^>]* alt="\([^"]*\)"[^>]*\/><\/div><br \/>\([^<]*\)\)\?/\n\3/
                            s/<br \/>[^<]*<br \/>/\n/;
                            s/<br \/>//;
                            s/<strong>.*<\/strong> //;
                            '
                    }
                }
            """
            )

            while True:
                for i in rq.search(r'tr -class bgcolor / sed "N;N;s/\n/\t/g"').split(
                    "\n"
                )[:-1]:
                    tr = i.split("\t")
                    post = {}

                    try:
                        post["body"] = reliq(tr[1]).search(r'td .tablerow | "%i"')
                        post["homepage"] = reliq(tr[2]).search(
                            r'a href title=w>homepage | "%(href)v"'
                        )
                        t = json.loads(reliq(tr[0]).search(expr))
                    except (IndexError, AttributeError):
                        break

                    for j in ["date", "user", "postid"]:
                        post[j] = t[j]
                    try:
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
                            post[g] = t["fields"][j]
                    except IndexError:
                        pass

                    posts.append(post)

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(rq)
                if len(nexturl) == 0:
                    break
                nexturl = self.url_base_merge(baseurl, nexturl)
                rq = self.session.get_html(nexturl, True)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next
        self.thread.url_base = self.url_base
        self.thread.url_base_merge = self.url_base_merge

        self.forum_forums_expr = reliq.expr(
            r'font .mediumtxt; a href=b>"forumdisplay.php" l@[1] | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'font .mediumtxt; a href=b>"viewthread.php" l@[1] | "%(href)v\n"'
        )
        self.board_forums_expr = reliq.expr(
            r'a href=a>"forumdisplay.php?" | "%(href)v\n" / sed "s#/./#/#"'
        )
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"^/(.*/)?viewthread.php\?tid=\d+$"],
            },
            {
                "func": "get_forum",
                "exprs": [r"^/(.*/)?forumdisplay.php\?fid=\d+$"],
            },
            {
                "func": "get_board",
                "exprs": [r"^/(.*/)?index.php\?gid=\d+$"],
            },
            {"func": "get_board", "exprs": None},
        ]

    @staticmethod
    def url_base(url):
        return re.sub(r"[^/]*$", r"", url)

    def get_next(self, rq):
        url = rq.search(
            r'td .multi; [0] a href rel=next | "%(href)v" / sed "s/&amp;/\&/g;q"'
        )
        if not re.search(r"&page=", url):
            return ""
        return url
