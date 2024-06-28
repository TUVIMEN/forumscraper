# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import warnings
import re
import json
from reliq import reliq

from ..utils import dict_add
from .common import ItemExtractor, ForumExtractor


def _guess(self, url, **kwargs):
    if re.fullmatch(
        r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+/.*([?/&;]topic[=,]|-t)+(\d+).*", url
    ):
        return self.get_thread(url, **kwargs)
    elif re.fullmatch(
        r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+/.*([?/&;]board[=,]|-t)+(\d+).*", url
    ):
        return self.get_forum(url, **kwargs)
    elif re.fullmatch(r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+/(.*/)?index.php.*", url):
        return self.get_forum(url, **kwargs)
    elif re.fullmatch(r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+(/.*)?", url):
        return self.get_forum(url, **kwargs)
    else:
        return None


class smf1Extractor(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(
                    r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+/.*([?/&;]topic[=,]|-t)(\d+).*"
                ),
                3,
            ]

        def get_contents(self, settings, rq, url, t_id):
            ret = {"format_version": "smf-1-thread", "url": url, "id": t_id}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                .title td #top_subject | "%i" / sed "s/[^:]*: //;s/([^(]*)//;s/&nbsp;//g;s/ *$//",
                .viewed.u td #top_subject | "%i" /  sed "s/.*\(//g;s/.* ([0-9]+) .*/\1/" "E",
                .path.a("\n") div a@[0]; E>(div|span) .nav l@[1]; a .nav | "%i\n" / line [:-1]
            """
                )
            )
            dict_add(ret, t)

            posts = []
            expr = reliq.expr(
                r"""
                .posts form #quickModForm; table l@[1]; tr l@[1] m@B>"id=\"subject_[0-9]*\""; tr l@[0] m@v>".googlesyndication.com/"; {
                    .postid.u div #B>subject_[0-9]* | "%(id)v" / sed "s/.*_//",
                    .date td valign=middle; div .smalltext | "%i" / sed "s/.* ://;s/^<\/b> //;s/ &#187;//g;s/<br *\/>.*//;s/<[^>]*>//g;s/ *$//",
                    .body div .post | "%i",
                    .signature div .signature | "%i",
                    .user td valign=top rowspan=2; b l@[1]; a href | "%i",
                    .userid.u td valign=top rowspan=2; b l@[1]; a href | "%(href)v" / sed "s/.*;//;s/.*-//;s/\.html$//;s/^u//;s/^=//",
                    .avatar td valign=top rowspan=2; img .avatar src | "%(src)v",
                    .edited td #B>modified_[0-9]*; * c@[0] | "%i",
                    .score span #B>gpbp_score_[0-9]* | "%i",
                    .attachments.a("\t") a href #B>link_[0-9]* | "%(href)v\t",
                    .userinfo.a("\n") td valign=top rowspan=2; div .smalltext | "%i\n" / sed "s/\(<br \/>\)\+/\n/g;s/\t//g" sed "/^$/d;/<img.* class=\"avatar\"/d"
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
                nexturl = self.get_next(rq)
                if len(nexturl) == 0:
                    break
                rq = self.session.get_html(nexturl)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'td .windowbg2 m@B>"name=\"b[0-9]*\""; b l@[1]; a href l@[1] | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'td .B>"windowbg[0-9]*" m@"<span class=\"smalltext\""; a href l@[1] | "%(href)v\n" / sed "s/[.;]msg[^\/]*#new$//;s/#new$//"'
        )

    def get_next(self, rq):
        return rq.search(
            r"""
            * m@B>'.*:.*class="navPages"' [-] | "%i\n" / sed 's#.*<b>[0-9]+</b>##;s#[^<]*<a [^>]*href="([^"]+)".*#\1#;/;all$/d;/^\]/d;/^#/d' "E"
        """
        )[:-1]

    def guess(self, url, **kwargs):
        return _guess(self, url, **kwargs)


class smf2Extractor(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(
                    r"https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]+/.*([?/&;]topic[=,])(\d+).*"
                ),
                3,
            ]
            self.trim = True

        def get_contents(self, settings, rq, url, t_id):
            ret = {"format_version": "smf-2-thread", "url": url, "id": t_id}
            page = 0

            forumposts = rq.filter(r"div #forumposts")
            title = forumposts.search(
                r'div .cat_bar; h3 .catbg | "%i\n" / sed "s/<[^>]*>//g;s/ &nbsp;/ /;s/ ([^)]*)$//;s/^[^:]*: //"'
            )[:-1]
            if len(title) > 0:
                viewed = forumposts.search(
                    r'div .cat_bar; h3 .catbg | "%i\n" / sed "s/<[^>]*>//g;s/ &nbsp;/ /;s/.* (\([^)]*\))$/\1/;s/.* \([0-9]*\) .*/\1/"'
                )[:-1]
            else:
                title = forumposts.search(
                    'h1 | "%i\n", B>h[0-9] .display_title; span #top_subject | "%i"'
                )
                viewed = forumposts.search(
                    'div .display-info;  li m@v>"comments" | "%i\n" / sed "s/<[^>]*>//g; s/ .*//"'
                )[:-1]

            ret["title"] = title
            ret["viewed"] = viewed

            ret["path"] = json.loads(
                rq.search(
                    r"""
                .path.a {
                    div .navigate_section [0]; li; a -href=a>action= l@[1]; * c@[0] | "%i\n" / line [:-1],
                    div .container; ol .breadcrumb [0]; li l@[1]; a l@[1]; * c@[0] | "%i\n" / line [:-1]
                }
            """
                )
            )["path"]

            posts = []
            expr = reliq.expr(
                r"""
                .posts form #quickModForm; div l@[1]; {
                    .postid.u div #B>msg_[0-9]* | "%(id)v" / sed "s/^msg_//",
                    .date div .postarea; div .keyinfo; E>(div|a) .smalltext | "%i" / sed "s/.*>//;s/^ //;s/&#187;//;s/ $//",
                    .body div .post; div #B>msg_[0-9]* l@[1] | "%i",
                    .signature div .signature | "%i",
                    .edited * #B>modified_[0-9]* | "%i",
                    .attachments.a div .attached; div .attachments_top; a href | "%(href)v\n",
                    .user div .poster; h4; a l@[1] | "%i",
                    .userid.u div .poster; h4; a href l@[1] | "%(href)v" / sed "s/^.*;u=//",
                    .avatar div .poster; { ul #B>msg_[0-9]*_extra_info, ul .user_info }; li .avatar; img src | "%(src)v\n",
                    .userinfo div .poster; { ul #B>msg_[0-9]*_extra_info, ul .user_info }; li -.avatar class; {
                        .key * l@[0] | "%(class)v",
                        .value * l@[0] | "%i"
                    } |
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
                nexturl = self.get_next(rq)
                if len(nexturl) == 0:
                    break
                rq = self.session.get_html(nexturl, self.trim)

            ret["posts"] = posts
            return ret

        def get_improper_url(self, url, rq):
            if rq is None:
                rq = self.session.get_html(url, self.trim)

            try:
                t_id = int(rq.search('input name=sd_topic value | "%(value)v"'))
            except ValueError:
                warnings.warn('url leads to improper forum - "{}"'.format(url))
                return [None, 0]

            return [rq, t_id]

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'{ * #E>board_[0-9]+, td .windowbg2 }; a E>(name|id)=E>b[0-9]+ href | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'span #B>msg_[0-9]*; a href | "%(href)v\n"'
        )

    def get_next(self, rq):
        return rq.search(
            r'div .pagelinks [0]; E>(a|span|strong) m@vB>"[a-zA-Z .]" l@[1] | "%(href)v %i\n" / sed "$q; /^ /{N;D;s/ .*//;p;q}" "n"'
        )[:-1]

    def guess(self, url, **kwargs):
        return _guess(self, url, **kwargs)


class smfExtractor(ForumExtractor):
    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.trim = True

        self.v1 = smf1Extractor(self.session)
        self.v2 = smf2Extractor(self.session)

    @staticmethod
    def is_version_1(rq):
        if rq.search(r'* l@[1] m@E>"Powered by SMF 1\.[^<]*<" | "t"'):
            return True
        return False

    def version_judge(self, func1, func2, url, rq=None, **kwargs):
        settings = self.get_settings(**kwargs)
        rq = self.get_first_html(url, rq)

        if self.is_version_1(rq):
            return func1(url, rq, **settings)
        else:
            return func2(url, rq, **settings)

    def get_thread(self, url, rq=None, depth=0, **kwargs):
        return self.version_judge(
            self.v1.get_thread, self.v2.get_thread, url, rq, **kwargs
        )

    def get_forum(self, url, rq=None, depth=0, **kwargs):
        return self.version_judge(
            self.v1.get_forum, self.v2.get_forum, url, rq, **kwargs
        )

    def guess(self, url, **kwargs):
        return _guess(self, url, **kwargs)
