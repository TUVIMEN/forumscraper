# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge, url_merge_r
from .identify import xenforoIdentify
from .common import ItemExtractor, ForumExtractor, ForumExtractorIdentify


guesslist = [
    {
        "func": "get_thread",
        "exprs": [r"^/(.*[/?])?(thread|topic)s?/"],
    },
    {"func": "get_board", "exprs": [r"^/(.*[/?])?forums?/$"]},
    {
        "func": "get_forum",
        "exprs": [r"^/(.*[/?])?forums?/"],
    },
    {
        "func": "get_tag",
        "exprs": [r"^/(.*[/?])?tags?/"],
    },
    {"func": "get_board", "exprs": None},
]


class xenforo2(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/(.*[./])?(\d+)(/.*)?$"),
                2,
            ]

        def get_search_user(self, rq, state, refurl, first_delim, xfToken, settings):
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
                        url_merge(refurl, user_url), first_delim, xfToken
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

        def get_reactions(self, rq, refurl, first_delim, xfToken, settings, state):
            ret = []
            reactions_url = rq.search(
                r'{ a .reactionsBar-link href | "%(href)v\n", div #b>reactions-bar-; a .list-reacts href | "%(href)v\n" } / line [1] tr "\n"'
            )

            if len(reactions_url) > 0:
                reactions_url = "{}{}_xfRequestUri=&_xfWithData=1&_xfToken={}&_xfResponseType=json".format(
                    url_merge(refurl, reactions_url), first_delim, xfToken
                )

                obj = reliq(
                    self.session.get_json(reactions_url, settings, state)["html"][
                        "content"
                    ].translate(str.maketrans("", "", "\n\t"))
                )

                t = json.loads(
                    obj.search(
                        r"""
                    .reactions div .contentRow; {
                        .user_id.u * .username data-user-id | "%(data-user-id)v",
                        .user * .username data-user-id; * c@[0] | "%i",
                        .date time .u-dt datetime | "%(datetime)v",
                        .reaction span .reaction; img title | "%(title)v"
                    } |
                """
                    )
                )
                ret = t["reactions"]

                self.state_add_url("reactions", reactions_url, state, settings)

            return ret

        def get_contents(self, rq, settings, state, url, i_id):
            page = 0
            url_first_delimiter = "?"
            if url.find("?") != -1:
                url_first_delimiter = "&"
            ret = {"format_version": "xenforo-2-thread", "url": url, "id": i_id}

            t = json.loads(
                rq.search(
                    r"""
                .title h1 {
                    h1 .p-title-value | "%i",
                    h1 qid="page-header" | "%i",
                    h1 .MessageCard__thread-title | "%i"
                } / sed ":x; s/<[^>]*>//g; $!{N;s/\n/ /;bx}",

                div .p-description; {
                    .user_id.u * data-user-id | "%(data-user-id)v",
                    .user * data-user-id; * c@[0] | "%i",
                    .date time datetime | "%(datetime)v",
                },
                .path.a ul .p-breadcrumbs -.p-breadcrumbs--bottom; span | "%i\n",
                .tags.a("|") a class=b>tagItem | "%i\n" / sed ":x; s/\t//g; /^$/d; $!{N;s/\n/|/;bx}; s/|$//; s/|\+/|/g" tr "\n",
                .poll form data-xf-init="poll-block ajax-submit"; {
                    .title h2 .block-header | "%i" / sed "s/\t//g; s/<[^>]*>//g; s/^ *//; s/ *$//; /^$/d;",
                    .answers [:-1] li; {
                        .option h3 .pollResult-response | "%i",
                        .votes.u span .pollResult-votes | "%i" / sed "s/\t//g; s/<[^>]*>//g; s/^ *//; s/ *$//; /^$/d; s/^.* //"
                    } |
                }
            """
                )
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
                    .user [0] * c@[0] | "%i",
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

                .id.u E>(span|div) #B>post-[0-9]* | "%(id)v" / sed "s/^post-//;q",

                .date {
                    * class=b>message-attribution-main; time datetime | "%(datetime)v",
                    * .MessageCard__date-created; [0] time datetime .u-dt | "%(datetime)v"
                },

                .text {
                    article class=b>message-body,
                    div .MessageCard__content-inner
                }; div .bbWrapper | "%i",

                .attachments.a ul .attachmentList; a,

                .signature div #signature-content-wrapper; div .bbWrapper | "%i"
            """
            )

            rq = reliq(rq.get_data().translate(str.maketrans("", "", "\n\t\r\a")))

            while True:
                post_tags = rq.search(
                    r"""
                    div #thread-main-section; div .MessageCard l@[1] | "%i\n",
                    article id,
                    div #B>post-[0-9]*,
                    div .block-container; div .MessageCard | "%i\n"
                """
                ).split("\n")[:-1]

                for i in post_tags:
                    tag = reliq(i)

                    post = json.loads(tag.search(expr))

                    post["user_link"] = url_merge_r(url, post["user_link"])
                    if post["user_avatar"][:1] == "/":
                        post["user_avatar"] = re.sub(
                            r"\?[0-9]+$", r"", post["user_avatar"]
                        )
                    post["user_avatar"] = url_merge_r(url, post["user_avatar"])

                    uext = post["user_extras"]
                    uext["pairs"] = uext["pairs1"] + uext["pairs2"] + uext["pairs3"]
                    uext.pop("pairs1")
                    uext.pop("pairs2")
                    uext.pop("pairs3")

                    reactions = []

                    if len(xfToken) > 0:
                        try:
                            if not settings["nousers"]:
                                self.get_search_user(
                                    tag,
                                    state,
                                    url,
                                    url_first_delimiter,
                                    xfToken,
                                    settings,
                                )

                            if not settings["noreactions"]:
                                reactions = self.get_reactions(
                                    tag,
                                    url,
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

    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/(.*[./])?(\d+)/[\&?]tooltip=true\&"),
                2,
            ]
            self.path_format = "m-{}"

        def get_first_html(self, url, settings, state, rq=None):
            return reliq(self.session.get_json(url, settings, state)["html"]["content"])

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "xenforo-2-user", "url": url, "id": i_id}

            t = json.loads(
                rq.search(
                    r"""
                .background div class=B>"memberProfileBanner memberTooltip-header.*" style=a>"url(" | "%(style)v" / sed "s#.*url(##;s#^//#https://#;s/?.*//;p;q" "n",
                .location a href=b>/misc/location-info | "%i",
                .avatar img src | "%(src)v" / sed "s/?.*//; q",
                .title span .userTitle | "%i",
                .banners.a * .userBanner; strong | "%i\n",
                .name h4 .memberTooltip-name; a; * c@[0] | "%i",
                .forum em; a href | "%(href)v",
                .extras dl .pairs c@[!0]; {
                    .key dt | "%i",
                    .value dd; {
                        time datetime | "%(datetime)v\a",
                        a m@v>"<" | "%i\a",
                        * l@[0] | "%i"
                    } / tr '\n' sed "s/^\a*//;s/\a.*//"
                } |
            """
                )
            )
            t["background"] = url_merge_r(url, t["background"])
            t["avatar"] = url_merge_r(url, t["avatar"])
            dict_add(ret, t)

            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

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
            } / line [1] tr "\n"
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


class xenforo1(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/(.*[./])?t?(\d+)(/(\?.*)?|\.html)?$"),
                2,
            ]

        def get_avatar_and_userid(self, refurl, messageUB):
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
            avatar = url_merge_r(refurl, avatar)

            if user_id == "0":
                user_id = messageUB.search(
                    r'[0] * .userText; a .username href | "%(href)v" / sed "s#/$##;s/.*\.//"'
                )
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = 0

            return avatar, user_id

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "xenforo-1-thread", "url": url, "id": i_id}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                .title { div class=b>titleBar; h1 | "%i", div #header; h1 | "%i" / sed ":x; s/<[^>]*>//g; $!{N;s/\n/ /;bx}" },
                p #pageDescription; {
                    .user_id.u a .username href | "%(href)v" / sed "s/^.*[\/.]\([0-9]\+\)/\1/; s/[^0-9]$//",
                    .user a .username | "%i",
                    .date * .DateTime | "%i"
                },
                .path.a span .crumbs; span itemprop=B>"[a-z]*"; * c@[0] | "%i\n",
                .tags.a("|") ul .tagList; a .tag | "%i|" / sed "s/<[^>]*>[^<]*<\/[^>]*>//g; s/|$//"
            """
                )
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
                    .name dt; * c@[0] | "%i",
                    .value dd; * c@[0] | "%i"
                } |
            """
            )
            posts = []

            while True:
                for i in rq.filter(
                    r"ol #messageList; li #E>post-[0-9]* data-author l@[1]"
                ).children():
                    post = {}
                    messageUB = i.filter(r"div class=b>messageUserBlock")

                    avatar, user_id = self.get_avatar_and_userid(url, messageUB)
                    post["avatar"] = avatar
                    post["user_id"] = user_id

                    t = json.loads(messageUB.search(expr))
                    dict_add(post, t)

                    t = json.loads(
                        i.search(
                            r"""
                        .date div .messageMeta; span .item; * .DateTime; {
                            * l@[0] title | "%(title)v",
                            * l@[0] -title | "%i"
                        },
                        .user li data-author l@[0] | "%(data-author)v",
                        .id.u li data-author l@[0] #B>post-[0-9]* | "%(id)v" / sed "s/^post-//",
                        .text div .messageContent; article | "%i"
                    """
                        )
                    )
                    dict_add(post, t)

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
                    [0] a C@'span itemprop="title" m@i>"forums"' | '%(href)v\n',
                    [0] a | "%(href)v\n"
                }
            } / line [1] tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = None

    def get_next_page(self, rq):
        url = rq.search(
            r'nav; [0] a class href=Be>"/page-[0-9]*" m@B>"^[^0-9]*&gt;" | "%(href)v"'
        )
        if not re.search(r"/page-[0-9]+$", url):
            return ""
        return url

    def get_tag(self, url, rq=None, **kwargs):
        return self.get_forum(url, rq, **kwargs)


class xenforo(ForumExtractorIdentify):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.v1 = xenforo1(self.session, **kwargs)
        self.v2 = xenforo2(self.session, **kwargs)

        self.guesslist = guesslist

    def identify_page(self, url, rq, cookies):
        return xenforoIdentify(self, url, rq, cookies)
