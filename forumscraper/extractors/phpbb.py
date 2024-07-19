# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge_r
from .common import ItemExtractor, ForumExtractor


class phpbb(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                r"^/((.*)?viewtopic\.php(.*)[\&\?]t=|.*-t)(\d+)",
                4,
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "phpbb-2+-thread", "url": url, "id": i_id}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                .title div #page-body; B>h[1-6] [0]; a href=b>"./viewtopic.php" | "%i",
                .path.a {
                    ul #nav-breadcrumbs; a; span itemprop | "%i\n",
                    div #page-header; li .icon-home; a | "%i\n"
                }
            """
                )
            )
            dict_add(ret, t)

            posts = []
            expr = reliq.expr(
                r"""
                .posts div #page-body; div #B>"p[0-9]*"; {
                    .postid.u div #B>"p[0-9]*" l@[0] | "%(id)v" / sed "s/^p//",
                    .date p .author | "%i" / sed "s/<\/time>$//;s/.*>//; s/.*;//; s/^ *//; s/^([a-z]* )+//; /^$/d" "E",
                    .content div .content | "%i",
                    .signature div .signature #B>sig[0-9]* | "%i",
                    dl .postprofile #B>profile[0-9]*; {
                        dt l@[1]; {
                            .avatar img src | "%(src)v",
                            .user a c@[0] | "%i",
                            .userid.u a href c@[0] | "%(href)v" / sed "s/.*[&;]u=([0-9]+).*/\1/" "E",
                        },
                        .userinfo_temp.a("\a") dd l@[1] m@vf>"&nbsp;" | "%i\a" / tr '\n\t' sed "s/<strong>([^<]*)<\/strong>/\1/g; s/ +:/:/; /<ul [^>]*class=\"profile-icons\">/{s/.*<a href=\"([^\"]*)\" title=\"Site [^\"]*\".*/Site\t\1/;t;d}; /^[^<>]+:/!{s/^/Rank:/};s/: */\t/" "E" "\a"
                    }
                } |
            """
            )

            while True:
                t = json.loads(rq.search(expr))
                posts += t["posts"]

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(url, rq)
                if nexturl is None:
                    break
                rq = self.session.get_html(nexturl, settings, state)

            for i in posts:
                i["avatar"] = url_merge_r(url, i["avatar"])
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
                "exprs": [r"^/(.*/)?viewtopic.php.*[\&\?]t=\d+"],
            },
            {
                "func": "get_forum",
                "exprs": [r"^/(.*/)?viewforum.php"],
            },
            {
                "func": "get_board",
                "exprs": [r"^/(.*/)?index.php"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(
            r"""
                {
                    div #page-footer,
                    div .f_footer,
                }; [0] a href | "%(href)v\n" / line [1] sed "s/&amp;/\&/g" tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        url = rq.search(
            r'a href rel=next | "%(href)v" / sed "s/^\.\///;s/&amp;/\&/g;q"'
        )
        if len(url) == 0:
            url = rq.search(
                r'div .topic-actions; div .pagination l@[1]; span l@[1]; E>(a|strong) -href=# | "%(href)v\n" / sed "/^$/{N;s/\n//;s/&amp;/\&/g;s/^\.\///;p;q}" "n"'
            )[:-1]

        if not re.search(r"&start=[0-9]+$", url):
            return ""
        return url
