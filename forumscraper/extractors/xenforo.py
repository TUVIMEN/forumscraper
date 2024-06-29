# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import warnings
import re
import json
from reliq import reliq

from ..exceptions import RequestError
from ..utils import dict_add, url_valid
from .identify import xenforoIdentify
from .common import ItemExtractor, ForumExtractor, ForumExtractorIdentify


def url_base(url):
    r = url_valid(url, None, True)
    if r is None:
        return ""
    return r[0]


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

            self.url_base = url_base

            self.match = [
                re.compile(r"^/(.*[./])?(\d+)(/.*)?$"),
                2,
            ]

        def get_search_user(self, settings, rq, baseurl, first_delim, xfToken):
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
                    settings,
                    "{}{}{}tooltip=true&_xfWithData=1&_xfToken={}&_xfResponseType=json".format(
                        baseurl, user_url, first_delim, xfToken
                    ),
                )

        @staticmethod
        def get_xfToken(rq):
            xfToken = rq.search(r'html data-csrf | "%(data-csrf)v"')
            if len(xfToken) == 0:
                xfToken = rq.search(r'[0] input name="_xfToken" value | "%(value)v"')
            if len(xfToken) == 0:
                xfToken = session.headers.get("csrf")

            return xfToken

        def get_reactions(self, rq, baseurl, first_delim, xfToken):
            ret = []
            reactions_url = rq.search(r'a .reactionsBar-link href | "%(href)v"')

            if len(reactions_url) > 0:
                reactions_url = "{}{}{}_xfRequestUri=&_xfWithData=1&_xfToken={}&_xfResponseType=json".format(
                    baseurl, reactions_url, first_delim, xfToken
                )

                obj = reliq(
                    self.session.get_json(reactions_url)["html"]["content"].translate(
                        str.maketrans("", "", "\n\t")
                    )
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

            return ret

        def get_contents(self, settings, rq, url, t_id):
            baseurl = self.url_base(url)
            page = 0
            url_first_delimiter = "?"
            if url.find("?") != -1:
                url_first_delimiter = "&"
            ret = {"format_version": "xenforo-2-thread", "url": url, "id": t_id}

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
                    .title h2 .block-header | "%i\n" / sed "s/\t//g; s/<[^>]*>//g; s/^ *//; s/ *$//; /^$/d;",
                    .answers li; {
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
                .user_id.u {
                    h4 class=b>message-name; * data-user-id | "%(data-user-id)v",
                    div .MessageCard__avatar; a data-user-id | "%(data-user-id)v"
                },

                .user {
                    h4 class=b>message-name; * c@[0] | "%i",
                    * .MessageCard__user-info__name; * c@[0] | "%i"
                },

                .id.u E>(span|div) #B>post-[0-9]* | "%(id)v" / sed "s/^post-//;q",

                .date {
                    * class=b>message-attribution-main; time datetime | "%(datetime)v",
                    * .MessageCard__date-created; [0] time datetime .u-dt | "%(datetime)v"
                },

                .text {
                    article class=b>message-body; div .bbWrapper | "%i",
                    div .MessageCard__content-inner; div .bbWrapper | "%i"
                },

                .attachments.a {
                    ul .attachmentList | "%i\n",
                    div #signature-content-wrapper; div .bbWrapper | "%i\n"
                }
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

                    reactions = []

                    if len(xfToken) > 0:
                        try:
                            if not settings["nousers"]:
                                self.get_search_user(
                                    settings, tag, baseurl, url_first_delimiter, xfToken
                                )

                            if not settings["noreactions"]:
                                reactions = self.get_reactions(
                                    tag, baseurl, url_first_delimiter, xfToken
                                )
                        except self.common_exceptions as ex:
                            self.handle_error(
                                ex,
                                "{}{}{}".format(baseurl, url_first_delimiter, xfToken),
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
                nexturl = self.get_next(rq)
                if len(nexturl) == 0:
                    break
                nexturl = self.url_base_merge(baseurl, nexturl)
                rq = self.session.get_html(nexturl, True)

            ret["posts"] = posts
            return ret

    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.url_base = url_base

            self.match = [
                re.compile(r"^/(.*[./])?(\d+)/[\&?]tooltip=true\&"),
                2,
            ]
            self.path_format = "m-{}"

        def get_first_html(self, url, rq=None):
            return reliq(self.session.get_json(url)["html"]["content"])

        def get_contents(self, settings, rq, url, u_id):
            baseurl = self.url_base(url)
            ret = {"format_version": "xenforo-2-user", "url": url, "id": u_id}

            t = json.loads(
                rq.search(
                    r"""
                .background div class=B>"memberProfileBanner memberTooltip-header.*" style=a>"url(" | "%(style)v" / sed "s#.*url(##;s#^//#https://#;s/?.*//;p;q" "n",
                .location a href=b>/misc/location-info | "%i",
                .avatar img src | "%(src)v" / sed "s#^//#https://#;s/?.*//; q",
                .joined dl .pairs .pairs--inline m@">Joined<"; time datetime | "%(datetime)v",
                .lastseen dl .pairs .pairs--inline m@">Last seen<"; time datetime | "%(datetime)v",
                .title span .userTitle | "%i",
                .name h4 .memberTooltip-name; a; * c@[0] | "%i",
                .forum em; a href | "%(href)v",
                .messages dl m@"<dt>Messages</dt>"; dd; * c@[0] | "%i\n" / sed "/[0-9]/{s/[,\t ]//g;p;q}" "n" tr "\n",
                .reactionscore dl m@B>"<dt.*>Reaction.*</dt>"; dd; * c@[0] | "%i\n" / sed "/[0-9]/{s/[,\t ]//g;p;q}" "n" tr "\n",
                .points dl m@B>"<dt .*title=\".*\">Points</dt>"; dd; * c@[0] | "%i\n" / sed "/[0-9]/{s/[,\t ]//g;p;q}" tr "\n"
            """
                )
            )
            if len(t["background"]) > 0:
                t["background"] = "{}{}".format(baseurl, t["background"])
            if len(t["avatar"]) > 0:
                t["avatar"] = "{}{}".format(baseurl, t["avatar"])
            dict_add(ret, t)

            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.url_base = url_base

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next
        self.thread.url_base_merge = self.url_base_merge
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

    def get_next(self, rq):
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

            self.url_base = url_base

            self.match = [
                re.compile(r"^/(.*[./])?t?(\d+)(/(\?.*)?|\.html)?$"),
                2,
            ]

        def get_contents(self, settings, rq, url, t_id):
            ret = {"format_version": "xenforo-1-thread", "url": url, "id": t_id}
            page = 0
            baseurl = self.url_base(url)

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

                    user_id = "0"
                    avatar = messageUB.search(
                        r'* class=b>avatar; [0] img src | "/%(src)v"'
                    )
                    if len(avatar) == 0:
                        user_id = messageUB.search(
                            r'span class="img m" style | "%(style)v" / sed "s#^.*/avatars/m/[0-9]*/##; s#\..*##"'
                        )
                        avatar = messageUB.search(
                            r"""span class="img m" style | "%(style)v" / sed "s/?[0-9]*')//; s/background-image: url('/\//; s/')$//" """
                        )
                    else:
                        r = re.search(r"/(\d+)\.[a-zA-Z]*(\?.*)?$", url)
                        if r:
                            user_id = r[1]

                    if len(avatar) > 0:
                        avatar = "{}{}".format(baseurl, url)

                    post["avatar"] = avatar
                    try:
                        post["user_id"] = int(user_id)
                    except ValueError:
                        post["user_id"] = 0

                    t = json.loads(messageUB.search(expr))
                    dict_add(post, t)

                    t = json.loads(
                        i.search(
                            r"""
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
                nexturl = self.get_next(rq)
                if len(nexturl) == 0:
                    break
                nexturl = self.url_base_merge(baseurl, nexturl)
                rq = self.session.get_html(nexturl, True)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.url_base = url_base

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next
        self.thread.url_base_merge = self.url_base_merge

        self.board_forums_expr = reliq.expr(
            r'h3 .nodeTitle; a -href=a>"#" href | "%(href)v\n"'
        )
        self.forum_forums_expr = self.board_forums_expr
        self.forum_threads_expr = reliq.expr(
            r'li id; div .titleText; h3 .title; a -.prefixLink href | "%(href)v\n"'
        )
        self.guesslist = guesslist

    def get_next(self, rq):
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

        self.v1 = xenforo1(self.session)
        self.v2 = xenforo2(self.session)

        self.guesslist = guesslist

    def identify(self, rq):
        return xenforoIdentify(self, rq)
