# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re
import copy

from ..defs import reliq
from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor, ForumExtractorIdentify
from .identify import identify_smf1, identify_smf2


guesslist = [
    {
        "func": "get_thread",
        "exprs": [r"/.*([?/&;]topic[=,]|-t)+(\d+)"],
    },
    {
        "func": "get_forum",
        "exprs": [r"/.*([?/&;]board[=,]|-t)+(\d+)"],
    },
    {
        "func": "get_board",
        "exprs": [r"/(.*/)?index.php"],
    },
    {"func": "get_board", "exprs": None},
]


class smf1(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/.*([?/&;]topic[=,]|-t)(\d+)"),
                    2,
                )
            ]

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "smf-1-thread", "url": url, "id": int(i_id)}

            t = rq.json(Path("smf1/thread.reliq"))
            dict_add(ret, t)

            posts = []

            for rq in self.next(rq, settings, state, path):
                posts += rq.json(Path("smf1/posts.reliq"))["posts"]

            for i in posts:
                ui = []
                for j in i["userinfo"]:
                    r = re.search("(^[A-Za-z0-9_-]+): (.*)$", j)
                    if r is not None:
                        key = r[1]
                        value = r[2]
                        if key == "poster_avatar" and len(i["avatar"]) == 0:
                            i["avatar"] = reliq(value, ref=rq.ref).json(
                                '.avatar.U [0] img src | "%(src)Dv"'
                            )["avatar"]
                            continue
                        elif key == "dropmenu" and len(i["user"]) == 0:
                            i["user"] = reliq(value, ref=rq.ref).search(
                                '[0] * c@[0] i@>[1:] | "%Di" trim'
                            )
                            continue

                    ui.append(j)
                i["userinfo"] = ui

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_smf1

        self.trim = True

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'td .windowbg2 i@B>"name=\"b[0-9]*\""; b l@[1]; a href l@[1] | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'td .B>"windowbg[0-9]*" i@"<span class=\"smalltext\""; a href l@[1] | "%(href)v\n" / sed "s/[.;]msg[^\/]*#new$//;s/#new$//"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(Path("smf1/findroot.reliq"))
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((forum|foro|board)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        return rq.search(
            r"""
            b i@B>"[0-9]"; [0] a .navPages href ssub@ | "%(href)v" ||
            [0] * .current_page; [0] a ssub@; * c@[0] self@ | "%(href)v" / sed "s/?PHPSESSID=[^\/&]*&amp;/?/"
        """
        )

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = rq.json(Path("smf1/forum.reliq"))

        categories = t["categories"]
        categories_forums = []

        if len(categories) == 0:
            categories = t["categories2"]

        for i in categories:
            prev_index = None
            for index, j in enumerate(i["forums"]):
                if len(j["link"]) == 0 or j["link"].find(";sort=") != -1:
                    if prev_index is not None and len(j["childboards"]) != 0:
                        categories_forums[prev_index]["childboards"] += j["childboards"]
                    continue

                try:
                    if j["posts"] == 0:
                        j["posts"] = j["posts2"]
                    j.pop("posts2")
                except KeyError:
                    pass

                try:
                    if j["topics"] == 0:
                        j["topics"] = j["topics2"]
                    j.pop("topics2")
                except KeyError:
                    pass

                lastpost = j["lastpost"]
                if len(lastpost["user"]) == 0:
                    lastpost["user"] = lastpost.get("user2", "")
                try:
                    lastpost.pop("user2")
                except KeyError:
                    pass

                if j.get("moderators") is None:
                    j["moderators"] = []

                prev_index = len(categories_forums)
                categories_forums.append(j)

            i["forums"] = categories_forums

        threads = t["threads"]
        if len(threads) == 0:
            threads = t["threads2"]
        outthreads = []

        for i in threads:
            if len(i["link"]) == 0:
                continue
            i["type1"] = i.get("type1", "")
            i["type2"] = i.get("type2", "")
            outthreads.append(i)

        return {
            "format_version": "smf-1-forum",
            "url": url,
            "categories": categories,
            "threads": outthreads,
        }


class smf2(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/.*([?/&;]topic[=,])(\d+)"),
                    2,
                )
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "smf-2-thread", "url": url, "id": int(i_id)}

            forumposts = rq.filter(r"div #forumposts")
            title = forumposts.search(
                r'div .cat_bar; h3 .catbg | "%i\n" / sed "s/<[^>]*>//g;s/ &nbsp;/ /;s/ ([^)]*)$//;s/^[^:]*: //" decode'
            )[:-1]
            if len(title) > 0:
                viewed = forumposts.search(
                    r'div .cat_bar; h3 .catbg | "%i\n" / sed "s/<[^>]*>//g;s/ &nbsp;/ /;s/.* (\([^)]*\))$/\1/;s/.* \([0-9]*\) .*/\1/"'
                )[:-1]
            else:
                title = forumposts.search(r'h1 | "%i"') + rq.search(
                    r'B>h[0-9] .display_title; span #top_subject | "%Di"'
                )
                viewed = forumposts.search(
                    r'div .display-info;  li i@v>"comments" | "%i\n" / sed "s/<[^>]*>//g; s/ .*//"'
                )[:-1]

            ret["title"] = title
            try:
                ret["viewed"] = int(viewed)
            except ValueError:
                ret["viewed"] = viewed

            ret["path"] = rq.json(
                r"""
                .path.a {
                    div .navigate_section [0]; li; a -href=a>action= l@[1]; * c@[0] | "%Di\n" / line [:-1],
                    div .container; ol .breadcrumb [0]; li l@[1]; a l@[1]; * c@[0] | "%Di\n" / line [:-1]
                } / trim "\n"
            """
            )["path"]

            posts = []

            for rq in self.next(rq, settings, state, path):
                t = rq.json(Path("smf2/posts.reliq"))
                outt = []
                for i in t["posts"]:
                    if i["postid"] == 0 and i["date"] == "" and i["body"] == "":
                        continue
                    outt.append(i)

                posts += outt

            ret["posts"] = posts
            return ret

        def get_improper_url(self, url, rq, settings, state):
            if rq is None:
                rsettings = copy.copy(settings["requests"])
                rsettings["trim"] = self.trim
                rq = self.session.get_html(url, **rsettings)

            try:
                i_id = str(int(rq.search('input name=sd_topic value | "%(value)v"')))
            except ValueError:
                print(
                    'url leads to improper forum - "{}"'.format(url),
                    file=settings["logger"],
                )
                return [None, 0]

            return [rq, i_id]

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_smf2

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'{ * #E>board_[0-9]+, td .windowbg2 }; a E>(name|id)=E>b[0-9]+ href | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'span #B>msg_[0-9]*; a href | "%(href)v\n"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(Path("smf2/findroot.reliq"))
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        return rq.search(
            r'div .pagelinks [0]; E>(a|span|strong) i@vB>"[a-zA-Z .]" l@[1] | "%(href)v %i\n" / sed "$q; /^ /{N;D;s/ .*//;p;q}" "n"'
        )[:-1]

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = rq.json(Path("smf2/forum.reliq"))

        categories = []

        prev_category_index = None
        prev_forums_index = None

        for i in t["categories"]:
            forums = i["forums"]

            if len(i["name"]) != 0:
                categories.append(i)
                prev_category_index = len(categories) - 1
                prev_forums_index = None
                i["forums"] = []

            if len(forums) == 0 or prev_category_index is None:
                continue

            out_forums = []

            for j in forums:
                if len(j["link"]) == 0:
                    if prev_forums_index is not None and len(j["childboards"]) != 0:
                        out_forums[prev_forums_index]["childboards"] += j["childboards"]
                    continue

                redirects = 0

                lastpost = j["lastpost"]
                if len(lastpost["user_link"]) == 0 and len(lastpost["link"]) == 0:
                    lastpost = j["lastpost2"]
                j.pop("lastpost2")

                if len(lastpost["user_link"]) == 0 and len(lastpost["link"]) == 0:
                    redirects = j["posts"]
                    j["posts"] = 0
                    j["topics"] = 0
                j["redirects"] = redirects

                j["lastpost"] = lastpost

                if j["posts"] == 0:
                    j["posts"] = j["posts2"]
                if j["topics"] == 0:
                    j["topics"] = j["topics"]
                j.pop("posts2")
                j.pop("topics2")

                out_forums.append(j)
                prev_forums_index = len(out_forums) - 1

            categories[prev_category_index]["forums"] += out_forums

        threads = t["threads"]

        for i in threads:
            if len(i["link"]) == 0:
                continue

            if len(i["user_link"]) == 0:
                i["user"] = i["user2"]
                i["user_link"] = i["user_link2"]
            i.pop("user2")
            i.pop("user_link2")

            i["icons"] += i["icons2"]
            i.pop("icons2")

            if i["replies"] == 0:
                i["replies"] = i["replies2"]
                i["views"] = i["views2"]
            i.pop("replies2")
            i.pop("views2")

            lastpost = i["lastpost"]
            if len(lastpost["link"]) == 0 and len(lastpost["user_link"]) == 0:
                lastpost = i["lastpost2"]
            i.pop("lastpost2")
            i["lastpost"] = lastpost

        return {
            "format_version": "smf-2-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }


class smf(ForumExtractorIdentify):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.v1 = smf1(self.session, **kwargs)
        self.v2 = smf2(self.session, **kwargs)

        self.extractors = [self.v1, self.v2]
