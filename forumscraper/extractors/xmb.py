# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge
from .common import ItemExtractor, ForumExtractor
from .identify import identify_xmb


def dict_url_merge(ref, data, fields):
    for j in fields:
        if len(j) == 1:
            data[j[0]] = url_merge(ref, data[j[0]])
        else:
            data[j[0]][j[1]] = url_merge(ref, data[j[0]][j[1]])


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

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {"format_version": "xmb-thread", "url": url, "id": int(i_id)}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                    .title td .nav -style | "%i" / sed "s/.* &raquo; //" decode trim,
                    .path.a [0] td .nav -style; a | "%Di\n" / trim "\n"
                """
                )
            )
            dict_add(ret, t)

            posts = []
            expr = reliq.expr(
                r"""
                .date td -rowspan l@[1]; a i@E>".+ .+ .+" | "%i" / sed "s/^[^ ]\+ [^ ]\+ //",
                td rowspan l@[1]; {
                    .user font .mediumtxt; * c@[0] | "%Di" trim,
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
                            s/<strong>[^<]*:<\/strong> //g;
                            s/<strong>//g;
                            s/<\/strong>//g
                            '
                    }
                }
            """
            )

            while True:
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
                        t = json.loads(reliq(tr[0]).search(expr))
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
                                post[g] = url_merge(ref, fields[j])
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

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(ref, rq)
                if nexturl is None:
                    break
                rq, ref = self.session.get_html(nexturl, settings, state, True)

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

        self.findroot_expr = reliq.expr(
            r'td .nav -style; a href | "%(href)v\n" / sed "/\/$/p" "n" line [-] tr "\n"'
        )
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

    def process_board_r(self, url, ref, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
            .categories table; td [0] .tablerow l@[2]; * rparent@; tr -.header l@[1]; {
                .category td .category; * c@[0] | "%Di" trim,
                .category_link [0] a href | "%(href)v",

                .state [0] td l@[1]; img src | "%(src)v",
                [1] td l@[1]; {
                    .description [1:2] font | "%i\a" / sed "/^&nbsp;$/d" "" "\a" tr "\a",
                    a href; {
                        .link [-] * l@[0] | "%(href)v",
                        .name * c@[0] | "%Di" / trim
                    }
                },
                .topics.u [2] td l@[1]; font | "%i",
                .posts.u [3] td l@[1]; font | "%i",
                .lastpost [4] td l@[1]; tr; {
                    [0] td; {
                        .date [0] a; * rparent@ | "%i" / sed "s#<br />.*##; s/.*>//",
                        a href; {
                            .user * l@[0] | "%Di" / sed "s/.*>//;s/^by //" trim,
                            .user_link * l@[0] | "%(href)v"
                        }
                    },
                    .link [1] td; [0] a href | "%(href)v"
                }
            } | """
            )
        )

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
                group_link = url_merge(ref, i["category_link"])
                continue

            if len(i["name"]) == 0:
                continue

            i["link"] = url_merge(ref, i["link"])
            i["state"] = url_merge(ref, i["state"])

            lastpost = i["lastpost"]
            if lastpost["user_link"] == lastpost["link"]:
                lastpost["user_link"] = None
            else:
                lastpost["user_link"] = url_merge(ref, lastpost["user_link"])
            lastpost["link"] = url_merge(ref, lastpost["link"])

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

    def process_forum_r(self, url, ref, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                .threads table; font [0] .mediumtxt; a [0] href=b>"viewthread.php?" l@[1]; [0] table ancestor@; tr -class l@[1]; {
                    .state [0] td l@[1]; img src | "%(src)v",
                    .icon [1] td l@[1]; img src | "%(src)v",
                    [2] td l@[1]; {
                        .sticky.b img | "t",
                        [0] a href; {
                             .link * l@[0] | "%(href)v",
                             .title * l@[0] | "%iD" trim
                        },
                        .lastpage.u u; [-] a | "%i"
                    },
                    [3] td l@[1]; a href; {
                        .user * l@[0] | "%Di" trim,
                        .user_link * l@[0] | "%(href)v"
                    },
                    .replies.u [4] td l@[1]; font | "%i",
                    .views.u [5] td l@[1]; font | "%i",
                    .lastpost [-] td l@[1]; [0] td l@[1:]; {
                        .date [0] a; * rparent@ | "%i" / sed "s#<br />.*##; s/.*>//",
                        a href; {
                            .user_link * l@[0] | "%(href)v",
                            .user * l@[0] | "%Di" / sed "s/.*>//;s/^by //" trim
                        }
                    }
                } | """
            )
        )

        threads = []

        for i in t["threads"]:
            if len(i["link"]) == 0:
                continue
            if i["lastpost"]["user_link"].startswith("viewthread.php?goto=lastpost&"):
                i["lastpost"]["user_link"] = ""

            dict_url_merge(
                ref,
                i,
                [
                    ["state"],
                    ["icon"],
                    ["link"],
                    ["user_link"],
                    ["lastpost", "user_link"],
                ],
            )
            threads.append(i)

        forums = []

        f = json.loads(
            rq.search(
                r"""
            .forums table; td [0] .ctrtablerow l@[2]; * rparent@; font [0] .mediumtxt; a [0] href=b>"forumdisplay.php?" l@[1]; [0] table ancestor@; tr -class l@[1]; {
                .state [0] td l@[1]; img src | "%(src)v",
                [1] td l@[1]; {
                    [0] a href; {
                         .link * l@[0] | "%(href)v",
                         .name * l@[0] | "%Di" / trim
                    },
                    .description [-] font | "%i"
                },
                .threads.u [2] td l@[1]; font | "%i",
                .posts.u [3] td l@[1]; font | "%i",
                .lastpost [4] td l@[1]; [0] td l@[1:]; {
                    .date [0] a; * rparent@ | "%i" / sed "s#<br />.*##; s/.*>//",
                    a href; {
                        .user_link * l@[0] | "%(href)v",
                        .user * l@[0] | "%Di" / sed "s/.*>//;s/^by //" trim
                    }
                }
            } | """
            )
        )

        for i in f["forums"]:
            dict_url_merge(
                ref,
                i,
                [
                    ["state"],
                    ["link"],
                    ["lastpost", "user_link"],
                ],
            )

            forums.append(i)

        return {
            "format_version": "xmb-forum",
            "url": url,
            "forums": forums,
            "threads": threads,
        }
