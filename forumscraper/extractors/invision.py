# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re

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

        def get_first_html(self, url, settings, state, rq=None, return_cookies=False):
            settings = get_settings(
                settings, headers={"x-Requested-With": "XMLHttpRequest"}
            )
            return self.session.get_html(
                url, settings, state, self.trim, return_cookies
            )

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "invision-4-user", "url": url, "id": int(i_id)}
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

        def get_poll_answers(self, rq):
            ret = []
            for i in rq.filter(r"ul; li").self():
                el = {}
                el["option"] = i.search(r'div .ipsGrid_span4 | "%i"')
                el["votes"] = i.search(
                    r'div .ipsGrid_span1; * i@E>"^(<[^>]*>[^<]*</[^>]*>)?[^<]+$" | "%i" / sed "s/^<i.*<\/i> //"'
                )
                ret.append(el)
            return ret

        def get_poll_questions(self, rq):
            ret = []
            for i in rq.filter(r"ol .ipsList_reset .cPollList; li l@[1]").self():
                el = {}
                el["question"] = i.search(r'h3; span | "%i"')
                el["answers"] = self.get_poll_answers(i)
                ret.append(el)

            return ret

        def get_poll(self, rq):
            ret = {}
            controller = rq.filter(r"section data-controller=core.front.core.poll")

            title = ""
            questions = []

            if controller:
                title = controller.search(
                    r'h2 l@[1]; span l@[1] | "%i" / sed "s/<.*//;s/&nbsp;//g;s/ *$//"'
                )
                questions = self.get_poll_questions(controller)

            ret["title"] = title
            ret["questions"] = questions
            return ret

        def get_reactions_details(self, rq, settings, state, path):
            ret = []
            nexturl = rq.search(
                r'ul .ipsReact_reactions; li .ipsReact_reactCount; [0] a href | "%(href)v" / sed "s/&amp;/\&/g; s/&reaction=.*$//;q" "E"'
            )

            nsettings = get_settings(
                settings, headers={"x-Requested-With": "XMLHttpRequest"}
            )

            page = 0

            while True:
                if len(nexturl) == 0:
                    break

                rq = self.session.get_html(
                    nexturl,
                    nsettings,
                    state,
                    True,
                )
                write_html(path + str(page), rq, settings)
                page += 1

                t = rq.json(Path("invision/reactions.reliq"))

                if len(ret) == 0:
                    self.state_add_url("reactions", nexturl, state, settings)

                ret += t["reactions"]

                nexturl = rq.search(
                    r'li .ipsPagination_next -.ipsPagination_inactive; [0] a href | "%(href)v" / sed "s/&amp;/&/; s/&reaction=.*$//;q"'
                )

            return ret

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "invision-4-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("invision/thread.reliq"))
            dict_add(ret, t)

            ret["poll"] = self.get_poll(rq)
            dict_add(ret, rq.json(Path("invision/thread-recommended.reliq")))

            posts = []

            for rq in self.next(rq, settings, state, path):
                for i in rq.filter(r"article #B>elComment_[0-9]*").self():
                    post = {}

                    user_link = post["user_link"] = i.json(
                        r'.t.U aside; h3 class=b>"ipsType_sectionHead cAuthorPane_author "; a href | "%(href)v"'
                    )["t"]

                    user_link = post["user_link"]
                    if Outputs.users in settings["output"] and len(user_link) > 0:
                        try:
                            self.user.get("users", user_link, settings, state)
                        except self.common_exceptions as ex:
                            self.handle_error(ex, user_link, settings, True)

                    dict_add(post, i.json(Path("invision/post.reliq")))

                    t = i.json(Path("invision/post-reactions.reliq"))
                    t["reactions"] = []
                    for j in t["reactions_temp"]:
                        el = {}
                        reaction = j.split("\t")
                        el["name"] = reaction[0]
                        el["count"] = 1
                        try:
                            el["count"] = int(reaction[1])
                        except Exception:
                            pass
                        t["reactions"].append(el)
                    t.pop("reactions_temp")
                    dict_add(post, t)

                    reactions_details = []
                    if Outputs.reactions in settings["output"]:
                        try:
                            reactions_details = self.get_reactions_details(
                                i,
                                settings,
                                state,
                                path + "-reactions-" + str(post["id"]) + "-",
                            )
                        except self.common_exceptions as ex:
                            self.handle_error(ex, i, settings, True)
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
            r'li class=b>"cForumRow ipsDataItem "; div .ipsDataItem_main; h4; a href | "%(href)v\n", div .ipsForumGrid; a .cForumGrid__hero-link href | "%(href)v\n"'
        )
        self.forum_forums_expr = self.board_forums_expr
        self.forum_threads_expr = reliq.expr(
            r'ol data-role=tableRows; h4; a class="" href=e>"/" | "%(href)v\n"'
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

    def get_forum_next_page(self, rq):
        return rq.search(
            'ul .ipsPagination; li .ipsPagination_next -.ipsPagination_inactive; [0] a | "%(href)v"'
        )

    def get_next_page(self, rq):
        return rq.search(
            r'ul .ipsPagination [0]; li .ipsPagination_next -.ipsPagination_inactive; a | "%(href)v" / sed "s#/page/([0-9]+)/.*#/?page=\1#" "E"'
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
