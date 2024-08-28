# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..enums import Outputs
from ..utils import dict_add, get_settings, url_merge_r, conv_short_size, url_merge
from .common import ItemExtractor, ForumExtractor


class invision(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"/(.*/)?(\d+)(-[^/]*)?/?"),
                2,
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

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "invision-4-user", "url": url, "id": i_id}

            t = json.loads(
                rq.search(
                    r"""
                .name h2 class=b>"ipsType_reset ipsType_"; a | "%i",
                .background div .ipsCoverPhoto_container; img src | "%(src)v",
                .avatar img src .ipsUserPhoto | "%(src)v",
                .group p class="ipsType_reset ipsType_normal"; * c@[0] | "%i",

                .joined {
                    p class="ipsType_reset ipsType_medium ipsType_light" m@b>"Joined "; time datetime | "%(datetime)v",
                    div .cUserHovercard_data; li m@">Joined<"; time datetime | "%(datetime)v"
                },

                .lastseen {
                    p class="ipsType_reset ipsType_medium ipsType_light" m@b>"Last visited "; time datetime | "%(datetime)v",
                    div .cUserHovercard_data; li m@">Last visited<"; time datetime | "%(datetime)v"
                },

                .info dl; div l@[1]; {
                    .name dt | "%i",
                    .value dd | "%i"
                } | ,
                div class=b>"ipsFlex ipsFlex-ai:center "; div class="ipsFlex ipsFlex-ai:center"; {
                    .rank img title | "%(title)v",
                    .rank_date time datetime | "%(datetime)v",
                },
                .badges.a div class=b>"ipsFlex ipsFlex-ai:center "; ul; li; img alt | "%(alt)v\n"
            """
                )
            )

            t["avatar"] = url_merge_r(url, t["avatar"])
            t["background"] = url_merge_r(url, t["background"])

            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"/(.*/)?(\d+)(-[^/]*)?/?"),
                2,
            ]
            self.trim = True

        def get_poll_answers(self, rq):
            ret = []
            for i in rq.filter(r"ul; li").children():
                el = {}
                el["option"] = i.search(r'div .ipsGrid_span4 | "%i"')
                el["votes"] = i.search(
                    r'div .ipsGrid_span1; * m@E>"^(<[^>]*>[^<]*</[^>]*>)?[^<]+$" | "%i" / sed "s/^<i.*<\/i> //"'
                )
                ret.append(el)
            return ret

        def get_poll_questions(self, rq):
            ret = []
            for i in rq.filter(r"ol .ipsList_reset .cPollList; li l@[1]").children():
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

        def get_reactions_details(self, rq, settings, state):
            ret = []
            nexturl = rq.search(
                r'ul .ipsReact_reactions; li .ipsReact_reactCount; [0] a href | "%(href)v" / sed "s/&amp;/\&/g; s/&reaction=.*$//;q" "E"'
            )

            nsettings = get_settings(
                settings, headers={"x-Requested-With": "XMLHttpRequest"}
            )

            while True:
                if len(nexturl) == 0:
                    break

                rq = self.session.get_html(
                    nexturl,
                    nsettings,
                    state,
                    True,
                )

                t = json.loads(
                    rq.search(
                        r"""
                        .reactions ol; li; {
                            .avatar a .ipsUserPhoto; img src | "%(src)v",
                            a .ipsType_break href; {
                                .user_link * l@[0] | "%(href)v",
                                .user * l@[0] | "%i"
                            },
                            .reaction span .ipsType_light; img src | "%(src)v" / sed "s#.*/reactions/##;s/\..*//;s/^react_//",
                            .date time datetime | "%(datetime)v"
                        } |
                        """
                    )
                )

                if len(ret) == 0:
                    self.state_add_url("reactions", nexturl, state, settings)

                for i in t["reactions"]:
                    i["avatar"] = url_merge_r(nexturl, i["avatar"])
                    i["user_link"] = url_merge_r(nexturl, i["user_link"])

                ret += t["reactions"]

                nexturl = rq.search(
                    r'li .ipsPagination_next -.ipsPagination_inactive; [0] a href | "%(href)v" / sed "s/&amp;/&/; s/&reaction=.*$//;q"'
                )

            return ret

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "invision-4-thread", "url": url, "id": i_id}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                div #ipsLayout_mainArea; h1 class="ipsType_pageTitle ipsContained_container"; {
                    .title span class="ipsType_break ipsContained"; span -class | "%i",
                    .badges.a span title | "%(title)v\n"
                },
                .rating.b ul .ipsRating_collective; li .ipsRating_on | "true",
                div .ipsPageHeader; {
                    .user_link a .ipsType_break href | "%(href)v",
                    .user a .ipsType_break href; * c@[0] | "%i",
                    .user_avatar a .ipsUserPhoto; img src | "%(src)v",
                    .user_followers a .ipsFollow; span .ipsCommentCount | "%i",
                },
                .date div .ipsFlex-flex:11; time datetime | "%(datetime)v",
                .path.a nav class=b>"ipsBreadcrumb ipsBreadcrumb_top "; ul data-role="breadcrumbList"; li; a; span | "%t\n" / sed "s/ $//",

                .tags.a {
                    div .ipsPageHeader; ul .ipsTags; a; span c@[0] | "%i",
                    div #ipsLayout_mainArea; h1 class="ipsType_pageTitle ipsContained_container"; a .ipsTag_prefix rel=tag; span c@[0] | "%i",
                },

                .warning div .cTopicPostArea; span .ipsType_warning | "%i",
            """
                )
            )
            dict_add(ret, t)

            ret["poll"] = self.get_poll(rq)
            ret["user_link"] = url_merge_r(url, ret["user_link"])
            ret["user_avatar"] = url_merge_r(url, ret["user_avatar"])

            t = json.loads(
                rq.search(
                    r"""
                .recommended div data-role=recommendedComments; div .ipsBox data-commentID; {
                    .id.u div .ipsBox data-commentID | "%(data-commentID)v",
                     div .ipsReactOverview; {
                        .reactions.a ul; li; img alt | "%(alt)v\n",
                        .reaction_count.u p class="ipsType_reset ipsType_center" | "%i"
                    },
                    .user_avatar aside; img src | "%(src)v",
                    div .ipsColumn; {
                        * .ipsComment_meta; {
                            .user_link a .ipsType_break href | "%(href)v",
                            .user a .ipsType_break href; * c@[0] | "%i",
                            .date time datetime | "%(datetime)v"
                        },
                        .link a .ipsButton href | "%(href)v",
                        a .ipsType_break href c@[0] l@[1]; {
                            .ruser_link a l@[0] | "%(href)v",
                            .ruser a l@[0] | "%i"
                        },
                        .content div .ipsType_richText | "%i"
                    }
                }
            """
                )
            )
            rec = t["recommended"]
            rec["user_avatar"] = url_merge_r(url, rec["user_avatar"])
            rec["user_link"] = url_merge_r(url, rec["user_link"])
            rec["link"] = url_merge_r(url, rec["link"])
            rec["ruser_link"] = url_merge_r(url, rec["ruser_link"])
            dict_add(ret, t)

            expr = reliq.expr(
                r"""
                .id.u article #B>elComment_[0-9]* | "%(id)v\n" / sed "s/^elComment_//",
                aside; {
                    .user h3 class=b>"ipsType_sectionHead cAuthorPane_author "; * c@[0] [0] | "%i",
                    * .cAuthorPane_photo data-role=photo; {
                        .user_avatar a .ipsUserPhoto; img src | "%(src)v",
                        .badges.a {
                            img title alt | "%(alt)v\n",
                            span .cAuthorPane_badge title=e>" joined recently" | "%(title)v\n"
                        }
                    },
                    ul .cAuthorPane_info; {
                        .group li data-role=group; * c@[0] | "%i",
                        .group_icon li data-role=group-icon; img src | "%(src)v",
                        .rank_title li data-role=rank-title | "%i",
                        .rank_image li data-role=rank-image; * | "%i",
                        .reputation_badge li data-role=reputation-badge; span | "%i" / sed "s/^<i .*<\/i> //;s/,//g;q",
                        .posts li data-role=posts | "%i" / sed "s/ .*//;s/,//g",
                        .custom li data-role=custom-field | "%i",
                        .user_info.a ul .ipsList_reset; li; a title l@[1] | "%(title)v\n" / sort "u",
                    }
                },
                div .ipsComment_meta; {
                    .top_badges.a div class=a>"ipsComment_badges"; ul .ipsList_reset; li; strong | "%i\n" / sed "s#<i [^>]*></i> ##g",
                    .date time datetime | "%(datetime)v",
                },
                .content div .cPost_contentWrap; div data-role=commentContent | "%i",
                .signature div data-role=memberSignature; div data-ipslazyload | "%i",
            """
            )
            posts = []

            while True:
                for i in rq.filter(r"article #B>elComment_[0-9]*").children():
                    post = {}

                    post["user_link"] = url_merge_r(
                        url,
                        i.search(
                            r'aside; h3 class=b>"ipsType_sectionHead cAuthorPane_author "; a href | "%(href)v"'
                        ),
                    )

                    user_link = post["user_link"]
                    if Outputs.users in settings["output"] and len(user_link) > 0:
                        try:
                            self.user.get("users", user_link, settings, state)
                        except self.common_exceptions as ex:
                            self.handle_error(ex, user_link, settings, True)

                    t = json.loads(i.search(expr))
                    t["user_avatar"] = url_merge_r(url, t["user_avatar"])
                    t["group_icon"] = url_merge_r(url, t["group_icon"])
                    t["rank_image"] = url_merge_r(url, t["rank_image"])
                    dict_add(post, t)

                    t = json.loads(
                        i.search(
                            r"""
                        ul .ipsReact_reactions; {
                            .reactions_users li .ipsReact_overview; a href -href=a>?do= l@[1]; {
                                .link * l@[0] | "%(href)v",
                                .name * l@[0] | "%i"
                            } | ,
                            .reactions_temp.a li .ipsReact_reactCount; span a@[0] / sed "s/<span><img .* alt=\"//; s/\".*//; N; s/\n/\t/; s/<span>//; s/<\/span>//"
                        }
                    """
                        )
                    )
                    for j in t["reactions_users"]:
                        j["link"] = url_merge_r(url, j["link"])
                    t["reactions"] = []
                    for j in t["reactions_temp"]:
                        el = {}
                        reaction = j.split("\t")
                        el["name"] = reaction[0]
                        el["count"] = reaction[1]
                        t["reactions"].append(el)
                    t.pop("reactions_temp")
                    dict_add(post, t)

                    reactions_details = []
                    if Outputs.reactions in settings["output"]:
                        try:
                            reactions_details = self.get_reactions_details(
                                i, settings, state
                            )
                        except self.common_exceptions as ex:
                            self.handle_error(ex, i, settings, True)
                    post["reactions_details"] = reactions_details

                    posts.append(post)

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(url, rq)
                if nexturl is None:
                    break

                rq = self.session.get_html(nexturl, settings, state, True)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

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
                "exprs": [r"^/(.*[/?])?(thread|topic)s?/"],
            },
            {
                "func": "get_forum",
                "exprs": [r"^/(.*[/?])?forums?/"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(
            r"""
            {
                [0] ul data-role=breadcrumbList; a href | "%(href)v\n" / sed "
                    1!G
                    h
                    \#/(((forum|foro|board)s?|community)/?|index\.php)$#{p;q}
                   $p" "En" line [-],
               li #b>elNavSecondary_ i>data-navapp=i>forums; [0] a href | "%(href)v",
               li #b>lmgNavSub_; [0] a href m@i>"forums" | "%(href)v\n",
               nav; li .ipsMenu_item; [0] a m@i>forums href | "%(href)v\n",
               [0] a href=Ea>"(/|^)((forum|foro)s?|community|communaute|comunidad|ipb)(\.([a-zA-Z0-9.-]\.)*[a-zA-Z]/?|/?$)" | "%(href)v\n",
               [0] a href=Ea>"(/|^)(index|index\.php)/?$" | "%(href)v\n"
            } / line [1] tr "\n"
           """
        )
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
        t = json.loads(
            rq.search(
                r"""
                .categories [0] * .cForumList; {
                    li child@,
                    * -C@"[0] li l@[1]" self@
                }; {
                    h2 child@; {
                        .name * -title c@[0] m@>[1:] | "%i",
                        .link [-] a | "%(href)v"
                    },
                    .forums {
                        ol .ipsDataList child@; li child@,
                        div .ipsForumGrid; div child@
                    }; {
                        [0] div ( .ipsDataItem_icon )( .cForumGrid__icon ); {
                            .status [0] span class | "%(class)v" sed "s/.*cForumIcon_//; s/ .*//",
                            .icon [0] img src | "%(src)v"
                        },
                        .icon2 [0] span .cForumGrid__hero-image data-background-src | "%(data-background-src)v",
                        div ( .ipsDataItem_main )( .cForumGrid__content ); {
                            * ( .ipsDataItem_title )( .cForumGrid__title ); [0] a; {
                                .title * self@ |"%i",
                                .link * self@ | "%(href)v"
                            },
                            .description [0] * .ipsType_richText | "%T" trim,
                        },
                        .posts {
                            [0] dt .ipsDataItem_stats_number | "%i",
                            [0] ul .cForumGrid__title-stats; [0] li c@[0] | "%i" sed "s/ .*//"
                        },
                        .followers [0] ul .cForumGrid__title-stats; [0] a c@[0] | "%i" sed "s/ .*//",
                        .childboards ul ( .ipsDataItem_subList )( .cForumGrid__subforums ); a; {
                            .name * self@ | "%i",
                            .link * self@ | "%(href)v"
                        } | ,
                        .lastpost [0] * ( .ipsDataItem_lastPoster )( .cForumGrid__last ); {
                            .avatar * .ipsUserPhoto; [0] img src | "%(src)v",
                            * .ipsDataItem_lastPoster__title; [0] a; {
                                .title * self@ | "%i",
                                .link * self@ | "%(href)v"
                            },
                            li .ipsType_light; [0] a .ipsType_break; {
                                .user * c@[0] | "%i",
                                .user_link * self@ | "%(href)v"
                            },
                            .date time datetime | "%(datetime)v"
                        }
                    } |
                } | ,
                .threads [0] ol .cTopicList; li child@; {
                    .avatar div .ipsTopicSnippet__avatar; [0] img | "%(src)v",
                    [0] * .ipsDataItem_title; {
                        .icons.a i | "%(class)v\n" / sed "s/.*fa-//",
                        [0] a -rel=tag; {
                            .title * c@[0] | "%i",
                            .link * self@ | "%(href)v",
                        }
                    },
                    [0] div ( .ipsDataItem_meta )( .ipsTopicSnippet__date ); {
                        .date time datetime | "%(datetime)v",
                        [0] a .ipsType_break; {
                            .user * c@[0] | "%i",
                            .user_link * self@ | "%(href)v"
                        }
                    },
                    .lastpage.u * .ipsPagination; [-] a | "%i",
                    .tags a rel=tag; {
                        .name * c@[0] | "%i",
                        .link * self@ | "%(href)v"
                    } | ,
                    [0] * ( .ipsDataItem_stats )( .ipsTopicSnippet__stats ); {
                        .group-indicator [0] img .cGroupIndicator src | "%(src)v",
                        span .ipsDataItem_stats_number; {
                            .replies [0] * self@ | "%i",
                            .views [1] * self@ | "%i",
                        }
                    },
                    .snippet div .ipsTopicSnippet__snippet; * c@[0] | "%i",
                    .lastpost [0] * ( .ipsDataItem_lastPoster )( .ipsTopicSnippet__last ); {
                        .avatar [0] * .ipsUserPhoto; [0] img src | "%(src)v",
                        [0] a .ipsType_break; {
                            .user * c@[0] | "%i",
                            .user_link * self@ | "%(href)v"
                        },
                        .date time datetime | "%(datetime)v"
                    }
                } |
                """
            )
        )

        categories = t["categories"]

        for i in categories:
            i["link"] = url_merge(url, i["link"])

            for j in i["forums"]:
                for g in j["childboards"]:
                    g["link"] = url_merge(url, g["link"])

                j["link"] = url_merge(url, j["link"])

                if len(j["icon"]) == 0:
                    j["icon"] = j["icon2"]
                j.pop("icon2")
                j["icon"] = url_merge(url, j["icon"])

                j["posts"] = conv_short_size(j["posts"])
                j["followers"] = conv_short_size(j["followers"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(url, lastpost["link"])
                lastpost["user_link"] = url_merge(url, lastpost["user_link"])
                lastpost["avatar"] = url_merge(url, lastpost["avatar"])

        threads = t["threads"]

        for i in threads:
            i["link"] = url_merge(url, i["link"])
            i["user_link"] = url_merge(url, i["user_link"])
            i["avatar"] = url_merge(url, i["avatar"])
            i["group-indicator"] = url_merge(url, i["group-indicator"])

            i["replies"] = conv_short_size(i["replies"])
            i["views"] = conv_short_size(i["views"])

            for j in i["tags"]:
                j["link"] == url_merge(url, j["link"])

            lastpost = i["lastpost"]
            lastpost["user_link"] = url_merge(url, lastpost["user_link"])
            lastpost["avatar"] = url_merge(url, lastpost["avatar"])

        return {
            "format_version": "invision-4-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
