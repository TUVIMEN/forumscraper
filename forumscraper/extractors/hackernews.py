# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..enums import Outputs
from ..utils import dict_add, get_settings, url_merge_r, conv_short_size, url_merge
from .common import ItemExtractor, ForumExtractor
from .identify import identify_hackernews


def get_comments(ref, rq):
    comments = json.loads(
        rq.search(
            r"""
        .comments tr id .athing .comtr; {
            .id.u * l@[0] | "%(id)v",
            table; tr; {
                .lvl.u td .ind indent | "%(indent)v",
                td .default; {
                    span .comhead;  {
                        .user a .hnuser href; {
                            .link * l@[0] | "https://news.ycombinator.com/%(href)v",
                            .name [0] * c@[0] i@>[1:] | "%Di" trim
                        },
                        .date span .age title | "%(title)v",
                        .onstory span .onstory; [0] a; {
                            .name * self@ | "%Di" / trim,
                            .link * self@ | "%(href)v"
                        }
                    },
                    .text div .commtext | "%i"
                }
            }
        } |
    """
        )
    )["comments"]

    for i in comments:
        i["user"]["link"] = url_merge(ref, i["user"]["link"])
        i["onstory"]["link"] = url_merge(ref, i["onstory"]["link"])
    return comments


def get_post(ref, rq):
    post = json.loads(
        rq.search(
            r"""
        tr id .athing l@[:1]; {
            .id.u * self@ | "%(id)v",
            span .titleline; [0] a; {
                .link * self@ href | "%(href)v",
                .title * self@ | "%Di" trim
            }
        },
        tr -class l@[:1]; {
            .score.u span #b>score_ | "%i" sed "s/ .*//",
            .date span .age title | "%(title)v",
            .user a .hnuser href; {
                .link * self@ | "%(href)v",
                .name [0] * c@[0] i@>[1:] | "%Di" trim
            },
            a i@"&nbsp;comment"; {
                .comments_count.u a self@ | "%i" sed "s/&.*//",
                .comments_link a self@ | "%(href)v"
            }
        },
        .text [0] div .toptext | "%i"
        """
        )
    )

    post["link"] = url_merge(ref, post["link"])
    post["user"]["link"] = url_merge(ref, post["user"]["link"])
    post["comments_link"] = url_merge(ref, post["comments_link"])
    return post


def get_page(ref, rq):
    threads = []
    posts_list = rq.search(r'[1] table -#hnmain; tr l@[1] | "%A\0"').split("\0")[:-1]
    size = len(posts_list)
    i = 0
    while i < size and size - i >= 3:
        inp = posts_list[i] + posts_list[i + 1] + posts_list[i + 2]

        post = get_post(ref, reliq(inp))
        threads.append(post)

        i += 3

    return threads


def get_all_pages(self, ref, rq, settings, state):
    threads = []
    page = 0

    while True:
        threads += get_page(ref, rq)

        page += 1
        if settings["thread_pages_max"] != 0 and page >= settings["thread_pages_max"]:
            break
        url = self.get_next(ref, rq)
        if url is None:
            break

        rq, ref = self.session.get_html(url, settings, state, True)

    return threads


def get_all_comments(self, ref, rq, settings, state):
    comments = []
    page = 0

    while True:
        comments += get_comments(ref, rq)

        page += 1
        if settings["thread_pages_max"] != 0 and page >= settings["thread_pages_max"]:
            break
        url = self.get_next(ref, rq)
        if url is None:
            break

        rq, ref = self.session.get_html(url, settings, state, True)

    return comments


class hackernews(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"^https://news.ycombinator.com/user\?id=([^&]+)"),
                    1,
                )
            ]
            self.path_format = "m-{}"
            self.trim = True

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {"format_version": "hackernews-user", "url": url, "id": i_id}

            t = json.loads(
                rq.search(
                    r"""
                    table #hnmain; [1] table desc@; tr; {
                        [0] td i@f>"user:"; td ssub@; {
                            .created-timestamp * timestamp self@ | "%(timestamp)v",
                            .user [0] a; [0] * c@[0] i@>[1:] | "%Di" trim
                        },
                        .created-date [0] td i@f>"created:"; td ssub@; [0] a | "%i",
                        .karma.u [0] td i@f>"karma:"; td ssub@ | "%i",
                        .about [0] td i@f>"about:"; td ssub@ | "%i",
                        .submissions-link [0] a href=b>"submitted?" | "%(href)v",
                        .comments-link [0] a href=b>"threads?" | "%(href)v",
                        .favorites-link [0] a href=b>"favorites?" | "%(href)v",
                    }
                    """
                )
            )

            t["submissions-link"] = url_merge_r(ref, t["submissions-link"])
            t["comments-link"] = url_merge_r(ref, t["comments-link"])
            t["favorites-link"] = url_merge_r(ref, t["favorites-link"])

            rq, ref = self.session.get_html(
                t["submissions-link"], settings, state, True
            )
            t["submissions"] = get_all_pages(self, ref, rq, settings, state)

            rq, ref = self.session.get_html(t["comments-link"], settings, state, True)
            t["comments"] = get_all_comments(self, ref, rq, settings, state)

            rq, ref = self.session.get_html(t["favorites-link"], settings, state, True)
            t["favorites"] = get_all_pages(self, ref, rq, settings, state)

            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"^https://news.ycombinator.com/item\?id=(\d+)"),
                    1,
                )
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {"format_version": "hackernews-thread", "url": url, "id": i_id}

            fatitem = rq.filter(r"[0] table .fatitem")
            t = get_post(ref, fatitem)
            dict_add(ret, t)

            ret["comments"] = get_all_comments(self, ref, rq, settings, state)
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_hackernews

        self.trim = True

        self.thread = self.Thread(self.session)
        self.user = self.User(self.session)
        self.user.get_next = self.get_next
        self.thread.user = self.user
        self.thread.get_next = self.get_next

        self.domains = ["news.ycombinator.com"]
        self.domain_guess_mandatory = True

        self.forum_threads_expr = reliq.expr(
            r'span .subline; a [0] i@"&nbsp;comment" href | "%(href)v\n"'
        )
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/item\?id="],
            },
            {
                "func": "get_user",
                "exprs": [r"/user\?id="],
            },
            {
                "func": "get_forum",
                "exprs": [
                    r"/(news|newest|front|show(new)?|ask|jobs)($|\?p=)",
                    r"/(favorites|submitted)\?id=",
                ],
            },
        ]

    def get_next_page(self, rq):
        return rq.search(r'[0] a .morelink rel=next href | "%(href)v"')

    def process_forum_r(self, url, ref, rq, settings, state):
        threads = get_page(ref, rq)

        return {
            "format_version": "hackernews-forum",
            "url": url,
            "threads": threads,
        }
