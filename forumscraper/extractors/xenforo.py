# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json

from ..defs import Outputs, reliq
from ..utils import dict_add, url_merge, url_merge_r, conv_short_size
from .common import ItemExtractor, ForumExtractor, ForumExtractorIdentify
from .identify import identify_xenforo1, identify_xenforo2


guesslist = [
    {
        "func": "get_thread",
        "exprs": [r"/(.*[/?])?(thread|topic|tema)s?/", r"/t/."],
    },
    {"func": "get_board", "exprs": [r"^/(.*[/?])?forums?/$"]},
    {
        "func": "get_forum",
        "exprs": [r"/(.*[/?])?forums?/", r"/f/."],
    },
    {
        "func": "get_tag",
        "exprs": [r"/(.*[/?])?tags?/"],
    },
    {"func": "get_board", "exprs": None},
]


class xenforo2(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(.*[./])?(\d+)(/.*)?$"),
                    2,
                )
            ]

        def get_search_user(self, rq, state, ref, first_delim, xfToken, settings):
            user_url = rq.search(
                r"""
                {
                    h4 class=b>message-name,
                    div .MessageCard__avatar
                }; [0] a data-user-id href | "%(href)v"
            """
            )
            if len(user_url) > 0:
                self.user.get(
                    "users",
                    "{}{}tooltip=true&_xfWithData=1&_xfToken={}&_xfResponseType=json".format(
                        url_merge(ref, user_url), first_delim, xfToken
                    ),
                    settings,
                    state,
                )

        def get_xfToken(self, rq):
            xfToken = rq.search(r'html data-csrf | "%(data-csrf)v"')
            if len(xfToken) == 0:
                xfToken = rq.search(r'[0] input name="_xfToken" value | "%(value)v"')
            if len(xfToken) == 0:
                xfToken = self.session.headers.get("csrf")

            return xfToken

        def get_reactions(self, rq, ref, first_delim, xfToken, settings, state):
            ret = []
            reactions_url = rq.search(
                r'{ a .reactionsBar-link href | "%(href)v\n", div #b>reactions-bar-; a .list-reacts href | "%(href)v\n" } / line [0] tr "\n"'
            )

            if len(reactions_url) > 0:
                reactions_url = "{}{}_xfRequestUri=&_xfWithData=1&_xfToken={}&_xfResponseType=json".format(
                    url_merge(ref, reactions_url), first_delim, xfToken
                )

                obj = reliq(
                    self.session.get_json(reactions_url, settings, state)["html"][
                        "content"
                    ].translate(str.maketrans("", "", "\n\t"))
                )

                t = obj.json(
                    r"""
                    .reactions div .contentRow; {
                        .user_id.u * .username data-user-id | "%(data-user-id)v",
                        .user * .username data-user-id; * c@[0] | "%Di" / trim,
                        .date time .u-dt datetime | "%(datetime)v",
                        .reaction span .reaction; img title | "%(title)v"
                    } |
                """
                )
                ret = t["reactions"]

                self.state_add_url("reactions", reactions_url, state, settings)

            return ret

        def get_contents(self, rq, settings, state, url, ref, i_id, path):
            url_first_delimiter = "?"
            if url.find("?") != -1:
                url_first_delimiter = "&"
            ret = {"format_version": "xenforo-2-thread", "url": url, "id": int(i_id)}

            t = rq.json(
                r"""
                .title h1; {
                    h1 .p-title-value | "%Di",
                    h1 qid="page-header" | "%Di",
                    h1 .MessageCard__thread-title | "%Di"
                } / sed ":x; s/<[^>]*>//g; $!{N;s/\n/ /;bx}" trim,

                div .p-description; {
                    .user_id.u * data-user-id | "%(data-user-id)v",
                    .user * data-user-id; * c@[0] | "%Di" / trim,
                    .date [0] time datetime | "%(datetime)v",
                },
                .path.a [0] ul .p-breadcrumbs -.p-breadcrumbs--bottom; span | "%Di\n" / trim "\n",
                .tags.a("|") a class=b>tagItem | "%i\n" / sed ":x; s/\t//g; /^$/d; $!{N;s/\n/|/;bx}; s/|$//; s/|\+/|/g" tr "\n",
                .poll form data-xf-init="poll-block ajax-submit"; {
                    .title h2 .block-header | "%Di" / sed "s/\t//g; s/<[^>]*>//g; s/^ *//; s/ *$//; /^$/d;" trim,
                    .answers [:-1] li; {
                        .option h3 .pollResult-response | "%i",
                        .votes.u span .pollResult-votes | "%i" / sed "s/\t//g; s/<[^>]*>//g; s/^ *//; s/ *$//; /^$/d; s/^.* //"
                    } |
                }
            """
            )
            dict_add(ret, t)

            xfToken = self.get_xfToken(rq)

            posts = []
            expr = reliq.expr(
                r"""
                {
                    h4 class=b>message-name,
                    * .MessageCard__user-info__name
                }; {
                    .user [0] * c@[0] | "%Di" trim,
                    .user_link [0] a class href | "%(href)v",
                    .user_id.u [0] * data-user-id | "%(data-user-id)v"
                },

                .user_avatar {
                    div .message-avatar,
                    div .MessageCard__avatar
                }; img src | "%(src)v",

                .user_title h5 .userTitle | "%i",

                .user_banners.a div .userBanner; strong | "%i\n",

                .user_extras {
                    .pairs1 div .message-userExtras; dl l@[1]; {
                        .key dt; {
                            * title | "%(title)v\a",
                            * l@[0] | "%i"
                        } / sed "s/^\a*//;s/\a.*//",
                        .value dd | "%i",
                    } | ,

                    .pairs2 div .message-userExtras; div .pairs; span title; {
                        .key * l@[0] | "%(title)v",
                        .value * l@[0] | "%i",
                    } | ,

                    .pairs3 div .MessageCard__user-details; span class -.MessageCard__dot-separator; {
                        .key * l@[0] | "%(class)v" / sed 's/^MessageCard__//',
                        .value * l@[0] | "%i"
                    } | ,

                    div .message-userExtras; {
                        .stars.a ul .reputation-star-container; li .eB>"[a-z]star" | "%(class)v\n" / sed "s/.* //",

                        .bar.a ul .reputation-bar-container; li .reputation-bar | "%(class)v\n" / sed "s/.* //"
                    }
                },

                .id.u [0] * #E>(js-)?post-[0-9]+ | "%(id)v" / sed "s/^js-//; s/^post-//;q",

                .date {
                    * class=b>message-attribution-main; time datetime | "%(datetime)v\t",
                    * .MessageCard__date-created; [0] time datetime .u-dt | "%(datetime)v"
                } / sed "s/\t.*//",

                .text {
                    article class=b>message-body,
                    div .MessageCard__content-inner
                }; div .bbWrapper | "%i",

                .attachments.a ul .attachmentList; a,

                .signature div #signature-content-wrapper; div .bbWrapper | "%i"
            """
            )

            rq = reliq(rq.get_data().translate(str.maketrans("", "", "\n\t\r\a")))

            for rq, ref in self.next(ref, rq, settings, state, path, trim=True):
                post_tags = rq.search(
                    r"""
                        [0] div c@[2:] .california-article-post,
                        div #E>(js-)?post-[0-9]+ ||
                        div #thread-main-section; div .MessageCard l@[1] | "%i\n" ||
                        article id ||
                        div .block-container; div .MessageCard | "%i\n"
                """
                ).split("\n")[:-1]

                for i in post_tags:
                    tag = reliq(i)

                    post = tag.json(expr)

                    post["user_link"] = url_merge_r(ref, post["user_link"])
                    if post["user_avatar"][:1] == "/":
                        post["user_avatar"] = re.sub(
                            r"\?[0-9]+$", r"", post["user_avatar"]
                        )
                    post["user_avatar"] = url_merge_r(ref, post["user_avatar"])

                    uext = post["user_extras"]
                    uext["pairs"] = uext["pairs1"] + uext["pairs2"] + uext["pairs3"]
                    uext.pop("pairs1")
                    uext.pop("pairs2")
                    uext.pop("pairs3")

                    reactions = []

                    if len(xfToken) > 0:
                        try:
                            if Outputs.users in settings["output"]:
                                self.get_search_user(
                                    tag,
                                    state,
                                    ref,
                                    url_first_delimiter,
                                    xfToken,
                                    settings,
                                )
                        except self.common_exceptions as ex:
                            self.handle_error(
                                ex,
                                "{}{}{}".format(url, url_first_delimiter, xfToken),
                                settings,
                                True,
                            )

                        try:
                            if Outputs.reactions in settings["output"]:
                                reactions = self.get_reactions(
                                    tag,
                                    ref,
                                    url_first_delimiter,
                                    xfToken,
                                    settings,
                                    state,
                                )
                        except self.common_exceptions as ex:
                            self.handle_error(
                                ex,
                                "{}{}{}".format(url, url_first_delimiter, xfToken),
                                settings,
                                True,
                            )

                    post["reactions"] = reactions

                    posts.append(post)

            ret["posts"] = posts
            return ret

    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(.*[./])?(\d+)/[\&?]tooltip=true\&"),
                    2,
                )
            ]
            self.path_format = "m-{}"

        def get_first_html(self, url, settings, state, rq=None, ref=None):
            rq = reliq(
                self.session.get_json(url, settings, state)["html"]["content"], ref=url
            )
            ref = rq.ref
            return (rq, ref)

        def get_contents(self, rq, settings, state, url, ref, i_id, path):
            ret = {"format_version": "xenforo-2-user", "url": url, "id": int(i_id)}

            t = rq.json(
                r"""
                .background div class=B>"memberProfileBanner memberTooltip-header.*" style=a>"url(" | "%(style)v" / sed "s#.*url(##;s#^//#https://#;s/?.*//;p;q" "n",
                .location a href=b>/misc/location-info | "%i",
                .avatar img src | "%(src)v" / sed "s/?.*//; q",
                .title span .userTitle | "%Di" / trim,
                .banners.a * .userBanner; strong | "%i\n",
                .name h4 .memberTooltip-name; a; * c@[0] | "%Di" / trim,
                .forum em; a href | "%(href)v",
                .extras dl .pairs c@[!0]; {
                    .key dt | "%i",
                    .value dd; {
                        time datetime | "%(datetime)v\a",
                        a i@v>"<" | "%i\a",
                        * l@[0] | "%i"
                    } / tr '\n' sed "s/^\a*//;s/\a.*//"
                } |
            """
            )
            t["background"] = url_merge_r(ref, t["background"])
            t["avatar"] = url_merge_r(ref, t["avatar"])
            dict_add(ret, t)

            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_xenforo2

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next
        self.user = self.User(self.session)
        self.thread.user = self.user

        self.board_forums_expr = reliq.expr(
            r'* .node-title; a href -href=b>/link-forums/ | "%(href)v\n"'
        )
        self.forum_forums_expr = self.board_forums_expr
        self.forum_threads_expr = reliq.expr(
            r'* .structItem-title; a -.labelLink href | "%(href)v\n"'
        )
        self.tag_threads_expr = reliq.expr(
            r'div class=b>contentRow; a -.labelLink href -data-user-id | "%(href)v\n"'
        )
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(
            r"""
            {
                * .p-nav; [0] a href | "%(href)v\n",
                * #header-forum-listing href | "%(href)v\n"
            } / line [0] tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((forum|foro|board)s?|index\.php|community|communaute|comunidad)/?$",
        )

    def get_next_page(self, rq):
        url = rq.search(
            r'div .block-outer; [0] a .pageNav-jump .pageNav-jump--next href | "%(href)v"'
        )
        if not re.search(r"/page-[0-9]*(\?.*)?/?(#.*)?$", url):
            return ""
        return url

    def process_board_r(self, url, ref, rq, settings, state):
        return self.process_forum_r(url, ref, rq, settings, state)

    def process_tag_r(self, url, ref, rq, settings, state):
        return self.process_forum_r(url, ref, rq, settings, state)

    def process_forum_r(self, url, ref, rq, settings, state):
        t = rq.json(
            r"""
            .categories div .block -b>data-widget- -.thNodes__nodeList -data-type=thread; {
                [0] * ( .block-header )( .section-header ); [0] * c@[0]; {
                    .name * self@ | "%Di" / trim,
                    .link * self@ | "%(href)v"
                },
                .forums [0] div ( .block-body )( .node-list ); div .node l@[1:2]; {
                    .icon [0] span .node-icon; {
                        i | "%(class)v" sed "s/.* //",
                        span .icon | "%(class)v" tr " " "\n" sed "/^icon$/d;/^forum$/d;s/node--//" trim,
                    },
                    * .node-main; {
                        * .node-title; [0] a; {
                            .name * self@ | "%Di" / trim,
                            .link * self@ | "%(href)v"
                        },
                        .description div .node-description | "%i",
                        .childboards [0] ol ( .node-subNodeFlatList )( .subNodeMenu ); a .subNodeLink; {
                            .icon {
                                * self@ | "%(class)v\a" sed "s/.*--//; /^subNodeLink/d",
                                i | "%(class)v" sed "s/ subNodeLink-icon//; s/.* //"
                            } / sed "s/\a.*//",
                            .name * self@ | "%Dt" trim,
                            .link * self@ | "%(href)v"
                        } |
                    },
                    div ( .node-meta )( .node-stats ); {
                        dd; {
                            .topics [0] * self@ | "%i",
                            .posts [1] * self@ | "%i"
                        },
                        span title; {
                            .posts2.u [0] * self@ | "%(title)v" tr ",. ",
                            .views.u [1] * self@ | "%(title)v" tr ",. "
                        }
                    },
                    .placeholder [0] * .node-extra-placeholder | "%i",
                    .lastpost div .node-extra; {
                        .avatar div .node-extra-icon; [0] img | "%(src)v",
                        * .node-extra-title; [0] a; {
                            .title * self@ | "%(title)Dv" trim,
                            .link * self@ | "%(href)v",
                            .label [0] span .label | "%i"
                        },
                        .date time .node-extra-date datetime | "%(datetime)v",
                        * .node-extra-user; [0] a; {
                            .user [0] * c@[0] | "%Di" trim,
                            .user_link * self@ | "%(href)v"
                        }
                    },
                    .date2 [0] * .last-time; time datetime | "%(datetime)v"
                } |
            } | ,
            .threads div .structItem--thread; {
                .votes.u span .contentVote-score | "%i",
                .avatar div .structItem-iconContainer; [0] img src | "%(src)v",
                div .structItem-cell--main; {
                    .icons.a {
                        ul .structItem-statuses; span; {
                            img title | "%(title)v\n",
                            * self@ | "%t\n" sed "/^$/d",
                        },
                        svg title | "%(title)v\n"
                    },
                    .label span .label | "%t",
                    * .structItem-title; [-] a -.labelLink; {
                        .title * self@ | "%Di" trim,
                        .link * self@ | "%(href)v"
                    },
                    [0] a .username; {
                        .user * c@[0] | "%Di" trim,
                        .user_link * self@ | "%(href)v"
                    },
                    .date [0] time datetime | "%(datetime)v",
                    .lastpage.u * .structItem-pageJump; [-] a | "%i"
                },
                div .structItem-cell--meta; {
                    dt i@B>"^[0-9]",
                    dd
                }; {
                    .replies [0] * c@[0] | "%i",
                    .views [1] * c@[0] | "%i"
                },
                .replies2.u [0] div .reply-count title | "%(title)v" tr ",. ",
                .views2.u [0] div .view-count title | "%(title)v" tr ",. ",
                .lastpost div ( .structItem-cell--latest )( .last-post-cell ); {
                    .date [0] time datetime | "%(datetime)v",
                    [0] a .username; {
                        .user * c@[0] | "%Di" trim,
                        .user_link * self@ | "%(href)v"
                    },
                },
                .lp-avatar div .structItem-cell--iconEnd; [0] img src | "%(src)v"
            } |
            """
        )

        categories = []

        for i in t["categories"]:
            if len(i["name"]) == 0 and len(i["forums"]) == 0:
                continue

            i["link"] = url_merge(ref, i["link"])

            for j in i["forums"]:
                for g in j["childboards"]:
                    g["link"] = url_merge(ref, g["link"])

                j["link"] = url_merge(ref, j["link"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(ref, lastpost["link"])
                lastpost["user_link"] = url_merge(ref, lastpost["user_link"])
                lastpost["avatar"] = url_merge(ref, lastpost["avatar"])
                if len(lastpost["date"]) == 0:
                    lastpost["date"] = j["date2"]
                j.pop("date2")

                if len(j["posts"]) == 0:
                    j["topics"] = 0
                    j["posts"] = j["posts2"]
                else:
                    j["topics"] = conv_short_size(j["topics"])
                    j["posts"] = conv_short_size(j["posts"])
                j.pop("posts2")

            categories.append(i)

        threads = t["threads"]

        for i in threads:
            i["link"] = url_merge(ref, i["link"])
            i["avatar"] = url_merge(ref, i["avatar"])
            i["user_link"] = url_merge(ref, i["user_link"])

            if len(i["replies"]) == 0:
                i["replies"] = i["replies2"]
                i["views"] = i["views2"]
            else:
                i["replies"] = conv_short_size(i["replies"])
                i["views"] = conv_short_size(i["views"])
            i.pop("replies2")
            i.pop("views2")

            lastpost = i["lastpost"]
            lastpost["user_link"] = url_merge(ref, lastpost["user_link"])
            lastpost["avatar"] = url_merge(ref, i["lp-avatar"])
            i.pop("lp-avatar")

        return {
            "format_version": "xenforo-2-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }


class xenforo1(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/(.*[./])?t?(\d+)(/(\?.*)?|\.html)?$"),
                    2,
                )
            ]

        def get_avatar_and_userid(self, ref, messageUB):
            user_id = "0"
            avatar = messageUB.search(r'* class=b>avatar; [0] img src | "%(src)v"')
            if len(avatar) == 0:
                user_id = messageUB.search(
                    r'span class="img m" style | "%(style)v" / sed "s#^.*/avatars/m/[0-9]*/##; s#\..*##"'
                )
                avatar = messageUB.search(
                    r"""span class="img m" style | "%(style)v" / sed "s/?[0-9]*')//; s/background-image: url('/\//; s/')$//" """
                )
            else:
                r = re.search(r"/(\d+)\.[a-zA-Z]*(\?.*)?$", avatar)
                if r:
                    user_id = r[1]

            avatar = re.sub(r"\?[0-9]+$", r"", avatar)
            avatar = url_merge_r(ref, avatar)

            if user_id == "0":
                user_id = messageUB.search(
                    r'[0] * .userText; a .username href | "%(href)v" / sed "s#/$##;s/.*\.//"'
                )
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = 0

            return avatar, user_id

        def get_contents(self, rq, settings, state, url, ref, i_id, path):
            ret = {"format_version": "xenforo-1-thread", "url": url, "id": int(i_id)}

            t = rq.json(
                r"""
                .title { div class=b>titleBar; [0] h1 | "%Di" trim, div #header; [0] h1 | "%Di" trim / sed ":x; s/<[^>]*>//g; $!{N;s/\n/ /;bx}" },
                p #pageDescription; {
                    .user_id.u a .username href | "%(href)v" / sed "s/^.*[\/.]\([0-9]\+\)/\1/; s/[^0-9]$//",
                    .user [0] a .username | "%Di" trim,
                    .date [0] * .DateTime | "%i"
                },
                .path.a span .crumbs; span itemprop=B>"[a-z]*"; * c@[0] | "%Di\n" / sed "/^$/d" trim "\n",
                .tags.a("|") ul .tagList; a .tag | "%i|" / sed "s/<[^>]*>[^<]*<\/[^>]*>//g; s/|$//"
            """
            )
            dict_add(ret, t)

            rq = reliq(rq.get_data().translate(str.maketrans("", "", "\n\t\r\a")))
            expr = reliq.expr(
                r"""
                h3 .userText; {
                    .user_title em class=b>userTitle | "%i",
                    .user_banner em class=b>userBanner; * c@[0] | "%i" / sed "/^[ \t]*$/d",
                },
                .user_extra dl; {
                    .name dt; * c@[0] | "%Di" / trim,
                    .value dd; * c@[0] | "%i"
                } |
            """
            )
            posts = []

            for rq, ref in self.next(ref, rq, settings, state, path, trim=True):
                for i in rq.filter(
                    r"ol ( #messageList )( .messageList ); li #E>post-[0-9]* data-author l@[1]"
                ).self():
                    post = {}
                    messageUB = i.filter(r"div class=b>messageUserBlock")

                    avatar, user_id = self.get_avatar_and_userid(ref, messageUB)
                    post["avatar"] = avatar
                    post["user_id"] = user_id

                    t = messageUB.json(expr)
                    dict_add(post, t)

                    t = i.json(
                        r"""
                        .date div .messageMeta; span .item; [0] * .DateTime; {
                            * l@[0] title | "%(title)v",
                            * l@[0] -title | "%i"
                        },
                        .user li data-author l@[0] | "%(data-author)Dv" / trim,
                        .id.u li data-author l@[0] #B>post-[0-9]* | "%(id)v" / sed "s/^post-//",
                        .text div .messageContent; article | "%i"
                    """
                    )
                    dict_add(post, t)

                    posts.append(post)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_xenforo1

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.board_forums_expr = reliq.expr(
            r'h3 .nodeTitle; a -href=a>"#" href | "%(href)v\n"'
        )
        self.forum_forums_expr = self.board_forums_expr
        self.forum_threads_expr = reliq.expr(
            r'li id; div .titleText; h3 .title; a -.prefixLink href | "%(href)v\n"'
        )
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(
            r"""
            {
                div #navigation; {
                    * .navTab .forums,
                    * .navTab .home
                }; [0] a href | "%(href)v\n",
                fieldset .breadcrumb; a .crumb href; {
                    span itemprop="title" i@i>"forums"; [0] a ancestor@ | '%(href)v\n',
                    [0] a | "%(href)v\n"
                }
            } / line [0] tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = None

    def get_next_page(self, rq):
        url = rq.search(
            r'nav; [0] a class href=Be>"/page-[0-9]*" i@B>"^[^0-9]*&gt;" | "%(href)v"'
        )
        if not re.search(r"/page-[0-9]+$", url):
            return ""
        return url

    def get_tag(self, url, rq=None, state=None, depth=0, **kwargs):
        return self.get_forum(url, rq, state, depth, **kwargs)

    def process_board_r(self, url, ref, rq, settings, state):
        return self.process_forum_r(url, ref, rq, settings, state)

    def process_forum_r(self, url, ref, rq, settings, state):
        t = rq.json(
            r"""
            .categories { ol #forums; li child@ || ol .nodeList }; {
                [0] div .nodeInfo child@; div .categoryText; {
                    * .nodeTitle; a; {
                        .name * self@ | "%Di" / trim,
                        .link * self@ | "%(href)v"
                    },
                    .description * .nodeDescription | "%i",
                },
                .forums {
                    ol .nodeList l@[:2]; li child@ ||
                    * self@
                }; div .nodeInfo [0] child@; {
                    .state span .nodeIcon title child@ | "%(title)v",
                    .icon span .nodeIcons; [0] img | "%(src)v",
                    div .nodeText child@; {
                        * .nodeTitle; [0] a; {
                            .name * self@ | "%Di" / trim,
                            .link * self@ | "%(href)v"
                        },
                        .description * #b>nodeDescription child@ | "%i",
                        div .nodeStats; dd; {
                            .topics.u [0] * self@ | "%i" tr ",. ",
                            .posts.u [1] * self@ | "%i" tr ",. "
                        },
                    },
                    .feed div .nodeControls; a .feedIcon | "%(href)v",
                    .childboards li .node .level-n; a; {
                        .name * self@ | "%Di" / trim,
                        .link * self@ | "%(href)v"
                    } | ,
                    .lastpost div .nodeLastPost; {
                        * .lastThreadTitle; [0] a; {
                            .title * self@ | "%Di" / trim,
                            .link * self@ | "%(href)v"
                        },
                        * .lastThreadMeta; {
                            * .lastThreadUser; [0] a; {
                                .user * self@ | "%Di" trim,
                                .user_link * self@ | "%(href)v"
                            },
                            .date * .DateTime | "%(title)v\a%(data-time)v" sed "s/^\a//g; s/\a.*//;"
                        }
                    }
                } |
            } | ,
            .threads ol .discussionListItems; li id=b>thread-; {
                .avatar div .posterAvatar; [0] img | "%(src)v",
                div .main child@; div .titleText child@; {
                    .icons.a div .iconKey child@; span class child@ | "%(class)v\n" / tr " " "\n",
                    * .title child@; {
                        .label [0] a .prefixLink; * c@[0] | "%i",
                        [0] a -.prefixLink; {
                            .title * self@ | "%Di" / trim,
                            .link * self@ | "%(href)v"
                        }
                    },
                    [0] a .username; {
                        .user * self@; [0] * c@[0] | "%Di" trim,
                        .user_link * self@ | "%(href)v"
                    },
                    .date * .DateTime | "%(title)v\a%(data-time)v\a%i" sed "s/^\a//g; s/\a.*//;",
                    .lastpage.u * .itemPageNav; [-] a href | "%i"
                },
                div .stats child@; {
                    .replies.u [0] dd | "%i" tr "., ",
                    .views.u [1] dd | "%i" tr "., "
                },
                .lastpost div .lastPost child@; {
                    [0] a .username; {
                        .user * self@; * c@[0] | "%Di" / trim,
                        .user_link * self@ | "%(href)v"
                    },
                    .date * .DateTime | "%(title)v\a%(data-time)v\a%i" sed "s/^\a//g; s/\a.*//;"
                }
            } |
            """
        )

        categories = t["categories"]

        for i in categories:
            i["link"] = url_merge(ref, i["link"])

            for j in i["forums"]:
                for g in j["childboards"]:
                    g["link"] = url_merge(ref, g["link"])

                j["link"] = url_merge(ref, j["link"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(ref, lastpost["link"])
                lastpost["user_link"] = url_merge(ref, lastpost["user_link"])

                j["icon"] = url_merge(ref, j["icon"])

        threads = t["threads"]

        for i in threads:
            i["link"] = url_merge(ref, i["link"])
            i["user_link"] = url_merge(ref, i["user_link"])

            lastpost = i["lastpost"]
            lastpost["user_link"] = url_merge(ref, lastpost["user_link"])

        return {
            "format_version": "xenforo-1-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }


class xenforo(ForumExtractorIdentify):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.v1 = xenforo1(self.session, **kwargs)
        self.v2 = xenforo2(self.session, **kwargs)

        self.extractors = [self.v1, self.v2]
