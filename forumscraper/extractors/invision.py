# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re
import copy

from ..defs import Outputs, reliq
from ..utils import dict_add, get_settings, conv_short_size
from .common import ItemExtractor, ForumExtractor, write_html
from .identify import identify_invision


class invision(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(.*/)?(\d+)(-[^/]*)?/?"),
                    2,
                ),
            ]
            self.path_format = "m-{}"
            self.trim = True

        def get_url(self, url):
            url_delim = "?"
            if url.find("?") != -1:
                url_delim = "&"

            return "{}{}do=hovercard".format(url, url_delim)

        def get_first_html(self, url, rq=None, **kwargs):
            if kwargs.get("headers") is None:
                kwargs["headers"] = {}
            kwargs["headers"] = {"x-Requested-With": "XMLHttpRequest"}
            kwargs["trim"] = self.trim
            return self.session.get_html(url, **kwargs)

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "invision-4+-user", "url": url, "id": int(i_id)}
            t = rq.json(Path("invision/user.reliq"))
            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(\d+)(-[^/]*)?/page/\d+/?"),
                    1,
                ),
                (
                    re.compile(r"/(.*/)?(\d+)(-[^/]*)?/?"),
                    2,
                ),
            ]
            self.trim = True

        def get_reactions_details(self, rq, settings, state, path):
            ret = []
            nexturl = rq.search(
                r'ul .ipsReact_reactions; li .ipsReact_reactCount; [0] a href | "%(href)v" / sed "s/&amp;/\&/g; s/&reaction=.*$//;q" "E"'
            )

            rsettings = copy.copy(settings["requests"])
            if rsettings.get("headers") is None:
                rsettings["headers"] = {}
            rsettings["headers"].update({"x-Requested-With": "XMLHttpRequest"})
            rsettings["trim"] = True

            page = 0

            try:
                while True:
                    if len(nexturl) == 0:
                        break
                    nexturl = reliq.decode(rq.ujoin(nexturl))

                    rq = self.session.get_html(nexturl, **rsettings)
                    write_html(path + str(page), rq, settings)
                    page += 1

                    t = rq.json(Path("invision/reactions.reliq"))

                    if len(ret) == 0:
                        self.state_add_url("reactions", nexturl, state, settings)

                    ret += t["reactions"]

                    nexturl = rq.search(
                        r'li ( .ipsPagination_next )( .ipsPagination__next ) -.ipsPagination_inactive; [0] a href | "%(href)v" / sed "s/&amp;/&/; s/&reaction=.*$//;q"'
                    )
            except self.common_exceptions as ex:
                self.handle_error(ex, rq, settings, True)

            return ret

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "invision-4+-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("invision/thread.reliq"))
            dict_add(ret, t)

            dict_add(ret, rq.json(Path("invision/thread-recommended.reliq")))

            posts = []

            for rq in self.next(rq, settings, state, path):
                for i in rq.filter(r"article #B>elComment_[0-9]*").self():
                    post = i.json(Path("invision/post.reliq"))

                    user_link = post["user_link"]
                    if Outputs.users in settings["output"] and len(user_link) > 0:
                        try:
                            self.user.get("users", user_link, settings, state)
                        except self.common_exceptions as ex:
                            self.handle_error(ex, user_link, settings, True)

                    t = i.json(Path("invision/post-reactions.reliq"))
                    for j in t["reactions"]:
                        if j["count"] == 0:
                            j["count"] = 1
                    dict_add(post, t)

                    reactions_details = []
                    if Outputs.reactions in settings["output"]:
                        reactions_details = self.get_reactions_details(
                            i,
                            settings,
                            state,
                            path + "-reactions-" + str(post["id"]) + "-",
                        )
                    post["reactions_details"] = reactions_details

                    posts.append(post)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_invision

        self.trim = True

        self.thread = self.Thread(self.session)
        self.user = self.User(self.session)
        self.thread.user = self.user
        self.thread.get_next = self.get_next

        self.board_forums_expr = reliq.expr(
            r"""
            li class=b>"cForumRow ipsDataItem "; div .ipsDataItem_main; h4; a href | "%(href)v\n",
            div .ipsForumGrid; a .cForumGrid__hero-link href | "%(href)v\n",
            section .ipsCategoryWithFeed__item; i-data .ipsCategoryWithFeed__meta; a .ipsLinkPanel | "%(href)v\n"
            """
        )
        self.forum_forums_expr = self.board_forums_expr
        self.forum_threads_expr = reliq.expr(
            r"""
            ol data-role=tableRows; h4; a class="" href=e>"/" | "%(href)v\n" ||
            li .ipsData__item; a .ipsLinkPanel child@ | "%(href)v\n"
            """
        )
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/(.*[/?])?(thread|topic)s?/"],
            },
            {
                "func": "get_forum",
                "exprs": [r"/(.*[/?])?forums?/"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(Path("invision/findroot.reliq"))
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((forum|foro|board)s?|index\.php|community|communaute|comunidad|ipb)/?$"
        )

    def get_next_page(self, rq):
        return rq.search(
            r"""
            ul .ipsPagination; [0] li ( .ipsPagination_next )( .ipsPagination__next ) -.ipsPagination_inactive; a | "%(href)v" / sed "s/#.*//"
            """
        )

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = rq.json(Path("invision/forum.reliq"))

        categories = t["categories"]

        for i in categories:
            for j in i["forums"]:
                if len(j["icon"]) == 0:
                    j["icon"] = j["icon2"]
                j.pop("icon2")

                j["posts"] = conv_short_size(j["posts"])
                j["followers"] = conv_short_size(j["followers"])

        threads = t["threads"]
        for i in threads:
            i["replies"] = conv_short_size(i["replies"])
            i["views"] = conv_short_size(i["views"])

        return {
            "format_version": "invision-4-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
