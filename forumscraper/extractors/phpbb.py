# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge_r, url_merge
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
                    div .nav-tabs; li .tab .forums; a .nav-link,
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

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                * #page-body; {
                    .categories div .forabg; {
                        [0] ul -.forums .topiclist; dt; { a, * self@ }; [0] * self@; {
                            .name * self@ | "%t",
                            .link * self@ | "%(href)v"
                        },
                        .forums ul .forums .topiclist; li child@; dl child@; {
                            .state {
                                * title self@ | "%(title)v\a",
                                * style=b>background-image: self@ | "%(style)v" sed "s/.*url(//;s/);.*//; s/.*\///; s/\..*//",
                                * class self@ | "%(class)v" tr ' ' '\n' sed '/^icon$/d; /^row-item$/d; /^elegant-row$/d'
                            } / sed "s/\a.*//" trim,
                            dt child@; {
                                [0] a href; {
                                    .name * self@ | "%i",
                                    .link * self@ | "%(href)v"
                                },
                                .icon span .forum-image; img src | "%(src)v",
                                .description * self@ | "%i" tr "\n\t\r" sed "/<br *\/>/!d; s/.*-->//; s/[^<]*(<br *\/?>(.*)|<)/\2/g; s/<strong>.*//; s/<br *\/?>/\n/g; s/<span[^>]*>([^<]*)<\/span>/\1/g; s/<div.*//" "E" trim,
                                .childboards a .subforum; {
                                    .state * self@ | "%(title)v",
                                    .name * self@ | "%t" trim,
                                    .link * self@ | "%(href)v"
                                } | ,
                                .moderators strong c@[0] m@b>Mod m@e>: l@[1:2]; a -.subforum ssub@; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                } | ,
                                div .forum-statistics; {
                                    .topics2.u [0] span .value | "%i",
                                    .posts2.u [1] span .value | "%i",
                                }
                            },
                            .topics.u dd .b>topics child@ | "%t" tr " ,",
                            .posts.u dd .b>posts child@ | "%t" tr " ,",
                            .redirects.u dd .redirect | "%T",
                            .lastpost dd .b>lastpost child@; span child@; {
                                a ( .b>username )( -class ) c@[0]; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                },
                                [0] a ( .lastsubject )( c@[1:] ); {
                                    .title * self@ | "%(title)v",
                                    .link * self@ | "%(href)v"
                                },
                                .date {
                                    time datetime | "%(datetime)v\a",
                                    * self@ | "%i" tr "\n\t\r" sed "/<br/!d; s/.*<br *\/?>//; s/^on //; s/&nbsp;//g" "E"
                                } / sed "s/\a.*//" trim
                            }
                        } |
                    } | ,
                    .threads div .forumbg; {
                        .name ul .topiclist -.topics; [0] dt | "%T" trim,
                        .threads ul .topiclist .topics; li child@; dl child@; {
                            .state {
                                * title self@ | "%(title)v\a",
                                * style=b>background-image: self@ | "%(style)v" sed "s/.*url(//;s/);.*//; s/.*\///; s/\..*//",
                                * class self@ | "%(class)v" tr ' ' '\n' sed '/^icon$/d; /^row-item$/d; /^elegant-row$/d'
                            } / sed "s/\a.*//" trim,
                            dt child@; {
                                [0] a href; {
                                    .title * self@ | "%i",
                                    .link * self@ | "%(href)v"
                                },
                                .lastpage.u * .pagination; [-] a c@[0] m@B>"[0-9]" | "%i",
                                [-] a href c@[0]; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                },
                                .date {
                                    time datetime | "%(datetime)v\a",
                                    {
                                        * self@ | "%i",
                                        div .topic-poster | "%t"
                                    } / tr "\n\t\r" sed "s/.*>//; s/^on //; s/&nbsp;//g; s/.*&raquo;//" "E"
                                } / sed "s/\a.*//" trim
                            },
                            .posts.u dd .posts | "%i",
                            .views.u dd .views | "%i",
                            .lastpost dd .b>lastpost child@; span child@; {
                                a ( .b>username )( -class ) c@[0]; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                },
                                .link [0] a ( .lastsubject )( c@[1:] ) | "%(href)v",
                                .date {
                                    time datetime | "%(datetime)v\a",
                                    * self@ | "%i" tr "\n\t\r" sed "/<br/!d; s/.*<br *\/?>//; s/^on //; s/&nbsp;//g" "E"
                                } / sed "s/\a.*//" trim
                            }
                        } |
                    } |
                }
                """
            )
        )

        categories = t["categories"]

        for i in t["categories"]:
            i["link"] = url_merge(url, i["link"])

            for j in i["forums"]:
                for g in j["childboards"]:
                    g["link"] = url_merge(url, g["link"])

                j["link"] = url_merge(url, j["link"])
                for g in j["moderators"]:
                    g["user_link"] = url_merge(url, g["user_link"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(url, lastpost["link"])
                lastpost["user_link"] = url_merge(url, lastpost["user_link"])

                if j["posts"] == 0:
                    j["posts"] = j["posts2"]
                if j["topics"] == 0:
                    j["topics"] = j["topics"]
                j.pop("posts2")
                j.pop("topics2")

                j["icon"] = url_merge(url, j["icon"])

        threads = t["threads"]

        for i in threads:
            for j in i["threads"]:
                j["link"] = url_merge(url, j["link"])
                j["user_link"] = url_merge(url, j["user_link"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(url, lastpost["link"])
                lastpost["user_link"] = url_merge(url, lastpost["user_link"])

        return {
            "format_version": "phpbb-2+-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
