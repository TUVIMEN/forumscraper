# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import (
    dict_add,
    get_settings,
    url_merge_r,
    url_merge,
    url_valid,
    conv_short_size,
)
from .common import ItemExtractor, ForumExtractor


class stackexchange(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"/users/(\d+)"),
                1,
            ]
            self.path_format = "m-{}"

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "stackexchange-user", "url": url, "id": int(i_id)}

            t = json.loads(
                rq.search(
                    r"""
                div #mainbar-full; {
                    [0] div child@; {
                        .avatar a; [0] img src | "%(src)v",
                        .user [0] div .fs-headline2 c@[0] | "%i",
                        .unregistered.b div .s-badge c@[0] | "t",
                        ul .list-reset; {
                            [0] * self@; li child@; {
                                .created [0] * self@; span title | "%(title)v",
                                .lastseen [1] * self@; div c@[0] m@bt>"Last seen" | "%i" sed "s/^Last seen//"
                            },
                            [1] * self@; {
                                .location div .wmx2 title c@[0] | "%i",
                                .social.a a href | "%(href)v\n"
                            }
                        },
                        li role=menuitem; {
                            .meta-profile a href=a>meta. | "%(href)v",
                            .network-profile a href=b>https://stackexchange.com/users/ | "%(href)v"
                        },
                    },
                    main #main-content; {
                        div #stats; div .md:fl-auto; {
                            .reputation * self@ m@reputation; div child@ c@[0] | "%i" tr ",",
                            .reached * self@ m@reached; div child@ c@[0] | "%i" tr ",",
                            .answers * self@ m@answers; div child@ c@[0] | "%i" tr ",",
                            .questions * self@ m@questions; div child@ c@[0] | "%i" tr ","
                        },
                        div c@[0] m@tf>Communities; [1] * ancestor@; {
                            .communities-all [0] a m@bt>"View all" | "%(href)v",
                            .communities li; a; {
                                .profile * self@ | "%(href)v",
                                .reputation div .ml-auto c@[0] | "%i" tr ","
                            } |
                        },
                        .about [0] div .js-about-me-content | "%i",
                        div c@[0] m@tf>Badges; [1] * ancestor@; {
                            .badges-all [0] a m@bt>"View all" | "%(href)v",
                            .badges div .s-card; div .jc-space-between c@[6:] child@; {
                                .amount.u div .fs-title | "%i",
                                .name div .fs-caption | "%i" line [1] " " tr " ",
                                .achievements li; {
                                    a ( .badge )( .badge-tag ); {
                                        .tag.b * self@ .badge-tag | "t",
                                        .link * self@ | "%(href)v",
                                        .action * self@ | "%(title)v" / sed 's/^[^:]*: //',
                                        .name div c@[0] | "%i"
                                    },
                                    .amount.u div -.ml-auto child@ | "%t",
                                    .date div .ml-auto child@ c@[0] | "%i"
                                } |
                            } |
                        },
                        div c@[0] .fs-title m@tf>"Top tags"; [1] * ancestor@; {
                           .tags-all [0] a m@bt>"View all" | "%(href)v",
                           .tags [0] div .s-card; div child@; {
                                a .s-tag; {
                                    .link * self@ | "%(href)v",
                                    .name * self@ | "%i"
                                },
                                .badge [0] a .badge-tag title | "%(title)v" / sed "s/ .*//",
                                div .d-flex .ai-center; {
                                    .score div .tt-lowercase m@tf>Score; [0] * spre@ | "%i" tr ",",
                                    .posts div .tt-lowercase m@tf>Posts; [0] * spre@ | "%i" tr ",",
                                    .posts-percent.u div .tt-lowercase m@tf>"Posts %"; [0] * spre@ | "%i" tr ",",
                                },
                                .answered.u * self@ title | "%(title)v" / sed "/Gave/!d; s/.*. Gave ([0-9]+) non-wiki .*/\1/" "E",
                                .ansked.u * self@ title | "%(title)v" / sed "s/^Asked ([0-9]+) .*/\1/" "E",
                                .asked-score.u * self@ title | "%(title)v" / sed "/^Asked/!d; s/\..*//; s/^.*total score //" "E"
                            } |
                        },
                        div c@[0] .fs-title m@tf>"Top posts"; [2] * ancestor@; {
                            div m@bt>"View all"; a; {
                                .posts-answers-all * self@ m@ft>answers | "%(href)v",
                                .posts-questions-all * self@ m@ft>questions | "%(href)v"
                            },
                            .posts [0] div .s-card; div child@; {
                                .type [0] title | "%i",
                                .answered.b [0] div .s-badge__answered | "t",
                                .votes.u div .s-badge__votes | "%i",
                                [0] a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%i"
                                },
                                .date span .relativetime title | "%(title)v"
                            } |
                        },
                        div c@[0] .fs-title m@tf>"Top network posts"; [1] * ancestor@; {
                           .network-posts-all [0] a m@bt>"View all" | "%(href)v",
                           .network-posts div .s-card; div child@; {
                                .votes.u div .s-badge__votes | "%i",
                                a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%i"
                                },
                            } |
                        },
                        div c@[0] .fs-title m@tf>"Top Meta posts"; [1] * ancestor@; {
                            .meta-posts-asked.u div .ml8 title=b>asked | "%(title)v",
                            .meta-posts-answered.u div .ml8 title=b>gave | "%(title)v",
                            .meta-posts div .s-card; div child@; {
                                .votes.u div .s-badge__votes | "%i",
                                a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%i"
                                },
                            } |
                        }
                    }
                }
            """
                )
            )
            t["avatar"] = url_merge_r(url, t["avatar"])
            t["meta-profile"] = url_merge_r(url, t["meta-profile"])
            t["network-profile"] = url_merge_r(url, t["network-profile"])

            t["reputation"] = conv_short_size(t["reputation"])
            t["reached"] = conv_short_size(t["reached"])
            t["answers"] = conv_short_size(t["answers"])
            t["questions"] = conv_short_size(t["questions"])

            t["communities-all"] = url_merge_r(url, t["communities-all"])
            for i in t["communities"]:
                i["profile"] = url_merge_r(url, i["profile"])
                i["reputation"] = conv_short_size(i["reputation"])

            t["badges-all"] = url_merge_r(url, t["badges-all"])
            for i in t["badges"]:
                for j in i["achievements"]:
                    j["link"] = url_merge_r(url, j["link"])
                    if j["amount"] == 0:
                        j["amount"] = 1

            t["tags-all"] = url_merge_r(url, t["tags-all"])
            for i in t["tags"]:
                i["link"] = url_merge_r(url, i["link"])
                i["score"] = conv_short_size(i["score"])
                i["posts"] = conv_short_size(i["posts"])

            t["posts-answers-all"] = url_merge_r(url, t["posts-answers-all"])
            t["posts-questions-all"] = url_merge_r(url, t["posts-questions-all"])
            for i in t["posts"]:
                i["link"] = url_merge_r(url, i["link"])

            t["network-posts-all"] = url_merge_r(url, t["network-posts-all"])
            for i in t["network-posts"]:
                i["link"] = url_merge_r(url, i["link"])

            for i in t["meta-posts"]:
                i["link"] = url_merge_r(url, i["link"])

            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                r"/questions/(\d+)",
                1,
            ]
            self.trim = True

        def get_post_comments(self, rq, url, postid, settings, state):
            n = rq.search(r'div #b>comments-link-; a .comments-link m@b>"Show " | "t"')
            if len(n) > 0:
                nsettings = get_settings(
                    settings, headers={"x-Requested-With": "XMLHttpRequest"}
                )
                rq = self.session.get_html(
                    "{}/posts/{}/comments".format(url_valid(url, base=True)[0], postid),
                    nsettings,
                    state,
                )

            comments = json.loads(
                rq.search(
                    r"""
                .comments li #E>comment-[0-9]+; {
                    .id.u * self@ | "%(data-comment-id)v",
                    .score.i div .comment-score; * c@[0] | "%i",
                    .content span .comment-copy | "%i",
                    .date span .comment-date; span title | "%(title)v" / sed "s/, L.*//",
                    [0] a .comment-user; {
                        .user * self@ | "%i",
                        .user_link * self@ | "%(href)v",
                        .reputation.u * self@ | "%(title)v" / tr ",."
                    },
                } |
             """
                )
            )["comments"]

            for i in comments:
                i["user_link"] = url_merge(url, i["user_link"])
            return comments

        def get_post(self, rq, url, settings, state):
            post = json.loads(
                rq.search(
                    r"""
                .id.u * self@ | "%(data-answerid)v %(data-questionid)v",
                .rating.i div .js-vote-count data-value | "%(data-value)v",
                .checkmark.b [0] div .js-accepted-answer-indicator | "t",
                .bounty.u [0] div .js-bounty-award | "%i",
                .content div class="s-prose js-post-body" | "%i",

                div .user-info m@"edited"; {
                    .edited span .relativetime | "%(title)v",
                    .editor {
                        .avatar img .bar-sm src | "%(src)v",
                         div .user-details; {
                            .name [0] * l@[1] c@[0] | "%i",
                            .link div .user-details; a href child@ | "%(href)v",
                            .reputation.u span .reputation-score | "%i" tr ",",
                            .gbadge.u span title=w>gold; span .badgecount | "%i",
                            .sbadge.u span title=w>silver; span .badgecount | "%i",
                            .bbadge.u span title=w>bronze; span .badgecount | "%i"
                        }
                    }
                },

                div .user-info m@v>"edited"; {
                    .date span .relativetime | "%(title)v",
                    .author {
                        .avatar img .bar-sm src | "%(src)v",
                         div .user-details; {
                            .name [0] * l@[1] c@[0] | "%i",
                            .link div .user-details; a href child@ | "%(href)v",
                            .reputation.u span .reputation-score | "%(title)v %i" tr ",",
                            .gbadge.u span title=w>gold; span .badgecount | "%i",
                            .sbadge.u span title=w>silver; span .badgecount | "%i",
                            .bbadge.u span title=w>bronze; span .badgecount | "%i"
                        }
                    }
                },
                """
                )
            )
            post["author"]["avatar"] = url_merge(url, post["author"]["avatar"])
            post["author"]["link"] = url_merge(url, post["author"]["link"])
            post["editor"]["avatar"] = url_merge(url, post["editor"]["avatar"])
            post["editor"]["link"] = url_merge(url, post["editor"]["link"])

            post["comments"] = self.get_post_comments(
                rq, url, post["id"], settings, state
            )
            return post

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {
                "format_version": "stackexchange-thread",
                "url": url,
                "id": int(i_id),
            }
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                    .title h1 itemprop="name"; a | "%i",
                    div .flex--item .mb8 .ws-nowrap; {
                        .views.u [0] * self@ m@"Viewed" | "%(title)v" / tr "0-9" "" "c",
                        .asked [0] * self@ m@"Asked"; [0] time itemprop="dateCreated" datetime | "%(datetime)v",
                        .modified [0] * self@ m@"Modified"; [0] a title | "%(title)v"
                    },
                    .tags.a div .ps-relative; a .post-tag | "%i\n"
                    """
                )
            )
            dict_add(ret, t)

            posts = []
            posts.append(
                self.get_post(
                    rq.filter("div #question").self()[0], url, settings, state
                )
            )

            while True:
                for i in rq.filter(r"div #b>answer-").self():
                    posts.append(self.get_post(i, url, settings, state))

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

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.user = self.User(self.session)

        self.forum_threads_expr = reliq.expr(
            r'a .s-link href=a>/questions/ | "%(href)v\n"'
        )

        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [r"/questions/(\d+)"],
            },
            {
                "func": "get_users",
                "exprs": [r"/users/(\d+)"],
            },
            {"func": "get_forum", "exprs": None},
        ]

    def get_next_page(self, rq):
        return rq.search(r'[0] div .pager-answers; [0] a rel="next" href | "%(href)v"')

    def get_forum_next_page(self, rq):
        return rq.search(r'div .pager; [0] a rel=next href | "%(href)v"')

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                    .threads div #b>question-summary-; {
                        div .s-post-summary--stats; div .s-post-summary--stats-item; {
                            .score.u [0] * self@ title=b>"Score of ",
                            .views.u [0] * self@ title=e>" views" | "%(title)v",
                            [0] span m@f>"answers"; {
                                .answers.u [0] span .e>-number spre@ | "%i",
                                .solved.b * .has-accepted-answer parent@ | "t"
                            },
                            .bounty.u * self@ .has-bounty | "%i"
                        },
                        div .s-post-summary--content; {
                            * .s-post-summary--content-title; [0] a; {
                                .title * self@ | "%i",
                                .link * self@ | "%(href)v"
                            },
                            .excerp * .s-post-summary--content-excerpt | "%i",
                            [0] * .s-post-summary--meta; {
                                .tags.a a .s-tag | "%i\n",
                                .author div .s-user-card; {
                                    .avatar img .s-avatar--image | "%(src)v",
                                    div .s-user-card--info; {
                                        .name [0] * c@[0] | "%i",
                                        .link a | "%(href)v"
                                    },
                                    .reputation.u li .s-user-card--rep; [0] span | "%(title)v %i" / tr ","
                                },
                                .date span .relativetime | "%(title)v"
                            }
                        }
                    } |
                """
            )
        )

        threads = t["threads"]

        for i in threads:
            i["link"] = url_merge(url, i["link"])
            i["author"]["link"] = url_merge(url, i["author"]["link"])
            i["author"]["avatar"] = url_merge(url, i["author"]["link"])

        return {
            "format_version": "stackexchange-forum",
            "url": url,
            "threads": threads,
        }
