# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import warnings
import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge_r, url_merge
from .identify import smfIdentify
from .common import ItemExtractor, ForumExtractor, ForumExtractorIdentify


guesslist = [
    {
        "func": "get_thread",
        "exprs": [r"^/.*([?/&;]topic[=,]|-t)+(\d+)"],
    },
    {
        "func": "get_forum",
        "exprs": [r"^/.*([?/&;]board[=,]|-t)+(\d+)"],
    },
    {
        "func": "get_board",
        "exprs": [r"^/(.*/)?index.php"],
    },
    {"func": "get_board", "exprs": None},
]


class smf1(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/.*([?/&;]topic[=,]|-t)(\d+)"),
                2,
            ]

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "smf-1-thread", "url": url, "id": i_id}
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
                for i in t["posts"]:
                    i["avatar"] = url_merge_r(url, i["avatar"])
                posts += t["posts"]

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

        self.trim = True

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.forum_forums_expr = reliq.expr(
            r'td .windowbg2 m@B>"name=\"b[0-9]*\""; b l@[1]; a href l@[1] | "%(href)v\n"'
        )
        self.forum_threads_expr = reliq.expr(
            r'td .B>"windowbg[0-9]*" m@"<span class=\"smalltext\""; a href l@[1] | "%(href)v\n" / sed "s/[.;]msg[^\/]*#new$//;s/#new$//"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(
            r"""
            {
                * .E>"maintab(_active)?_back",
                div #toolbar; div .tabs; * role=menuitem; a l@[1],
                div #headerarea; a l@[1],
                div #E>(myNavbar|toolbar[0-9]|topmenu|menu|nav); li,
                body; [0] * l@[1]; table l@[0]; tr .B>windowbg[123]; td; a l@[1] C@"img" c@[1],
            }; a href | "%(href)v\n" / sed "
                \#(/((board|forum|foro)s?|community)(/(index\.(html|php))?|\.(html|php))?(\?[^/]*)?|[;&?]action=forum)$#{p;q}
                1!G; h
                $p
            " "En" line [-] sed "s/&amp;/\&/g" tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((forum|foro|board)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        return rq.search(r'b m@B>"[0-9]"; [0] a .navPages href ssub@ | "%(href)v"')

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                .categories {
                    div #bodyarea; div .tborder style l@[1],
                    div #mainarea; div -class l@[1],
                    [0] table .bordercolor C@"tr .titlebg"
                }; {
                    .name * .E>catbgf?; * c@[0] | "%i",
                    .forums [0] table l@[:2]; tr l@[1]; {
                        .childboards [0] td l@[1]; * l@[0] -C@"img"; a href; {
                            .link * l@[0] | "%(href)v",
                            .name * l@[0] | "%i",
                            .state * l@[0] | "%(title)v" sed "s/ (.*//",
                            .topics.u * l@[0] | "%(title)v" sed "s/.* (//; s/)$//; s/,.*//; s/.*: //",
                            .posts.u * l@[0] | "%(title)v" sed "s/.* (//; s/)$//; s/.*, //; s/.*: //"
                        } | ,

                        .state [0] td l@[1]; img title | "%(title)v",
                        [1] td l@[1]; {
                            [0] a href; {
                                .link * l@[0] | "%(href)v",
                                .name * l@[0] | "%i"
                            },
                            .description * l@[0] | "%t" trim sed "s/^&nbsp;//" trim,
                            .moderators div; i; a href; {
                                .user_link * l@[0] | "%(href)v",
                                .user * l@[0] | "%i"
                            } |
                        },
                        [2] td l@[1]; {
                            {
                                span,
                                small,
                                * l@[0]  c@[1:]
                            }; {
                                .posts.u * l@[0] | "%t" line [1],
                                .topics.u * l@[0] | "%t" line [2:] " "
                            },
                            .posts2.u * l@[0] c@[0] | "%i"
                        },

                        .topics2.u [3] td l@[1]; {
                            span .largetext l@[1] | "%i",
                            * l@[0] c@[0] | "%i"
                        },
                        .lastpost {
                            [3:4] td l@[1]; {
                                [0] span l@[1]; * .smalltext l@[0],
                                [0] small l@[1]
                            },
                            [1] td l@[1]; span .smalltext
                        }; {
                            [0] a href=aE>(action=profile|/profiles/); {
                                .user_link * l@[0] | "%(href)v",
                                .user * l@[0] | "%i"
                            },
                            [0] a href -href=aE>(action=profile|/profiles/); {
                                .link * l@[0] | "%(href)v",
                                .title * l@[0] | "%i"
                            },
                            .date * l@[0] | "%i" / tr "\n\r" sed "/^</!s/<.*//; s/.*<br \/>//; s/.*<\/a>//; s/<[^>]*>//g; s/\t//g; s/^on //; s/^  *//;"
                        }
                    } |
                } | ,
                .categories2 div #bodyarea_inner; div .boardindex l@[1]; {
                    .name div .cat_bar l@[1]; h3 | "%i",
                    .forums li l@[2]; {
                        .childboards div .childboards; a; {
                            .link * l@[0] | "%(href)v",
                            .name * l@[0] | "%i",
                            .state * l@[0] | "%(title)v" sed "s/ (.*//",
                            .topics.u * l@[0] | "%(title)v" sed "s/.* (//; s/)$//; s/,.*//; s/.*: //",
                            .posts.u * l@[0] | "%(title)v" sed "s/.* (//; s/)$//; s/.*, //; s/.*: //"
                        } | ,
                        .state a .board_icon; img title | "%(title)v",
                        div .info; {
                            h4; a; {
                                .link * l@[0] | "%(href)v",
                                .name * l@[0] | "%i",
                                .posts.u * l@[0] | "%(title)v",
                                .topics.u * l@[0] | "%(title)v" line [2:] " "
                            },
                            .description p l@[1] | "%i"
                        },
                        .lastpost div .lastpost; {
                            a href; {
                                .link * l@[0] | "%(href)v",
                                .title * l@[0] | "%i"
                            },
                            .date * l@[0] | "%i" sed "s/<.*//; s/.*: //;q" trim,
                            [-] a href=a>"action=profile"; {
                                .user * l@[0] | "%i",
                                .user_link * l@[0] | "%(href)v"
                            },
                            .user2 * l@[0] | "%i" tr "\n" sed "s/.*>//; s/.*&nbsp;//",
                        }
                    } |
                } | ,
                .threads [0] table .bordercolor C@"tr l@[1]; td [2] l@[1]; a href=aE>([&?;]topic=|-t)[0-9]+\.0"; [1:] tr l@[1]; {
                    .type1 [0] td l@[1]; img src | "%(src)v",
                    .type2 [1] td l@[1]; img src | "%(src)v",
                    [2] td l@[1]; {
                        .icons.a img src | "%(src)v\n",
                        [0] a href; {
                            .link * l@[0] | "%(href)v",
                            .title * l@[0] | "%i"
                        },
                        .lastpage.u {
                            span l@[1],
                            small l@[1]
                        }; [1:] a; [-] a -m@f>"All" | "%i"
                    },
                    [3] td l@[1]; a href; {
                        .user_link * l@[0] | "%(href)v",
                        .user * l@[0] | "%i"
                    },
                    .replies.u [4] td l@[1] | "%T",
                    .views.u [5] td l@[1] | "%T",
                    .lastpost [6] td l@[1]; span .smalltext l@[1]; {
                        [0] a href; {
                            .user_link * l@[0] | "%(href)v",
                            .user * l@[0] | "%i"
                        },
                        .date * l@[0] | "%i" sed "s/<br \/>.*//; s/<[^>]*>//g;q" trim
                    }
                } | ,
                .threads2 div #messageindex; li l@[2] -.pageindex_li c@[!0]; {
                    div .info; {
                        span #b>msg_; a; {
                            .link * l@[0] | "%(href)v",
                            .name * l@[0] | "%i",
                            .replies.u * l@[0] | "%(title)v",
                            .views.u * l@[0] | "%(title)v" line [2:] " "
                        },
                        [-] a l@[1]; {
                            .user_link * l@[0] | "%(href)v",
                            .user * l@[0] | "%i"
                        },
                        .lastpage.u span #b>pages; [-] a | "%i",
                        .icons.a img l@[1] | "%(src)v\n"
                    },
                    .lastpost div .lastpost; {
                        a href c@[0]; {
                            .user * l@[0] | "%i",
                            .user_link * l@[0] | "%(href)v"
                        },
                        .date * l@[0] | "%i" tr "\n\t" sed "s/.*>//; s/.*&nbsp;//"
                    }
                } |
                """
            )
        )

        categories = t["categories"]
        categories_forums = []

        if len(categories) == 0:
            categories = t["categories2"]

        for i in categories:
            prev_index = None
            for index, j in enumerate(i["forums"]):
                for g in j["childboards"]:
                    g["link"] = url_merge(url, g["link"])

                if len(j["link"]) == 0 or j["link"].find(";sort=") != -1:
                    if prev_index is not None and len(j["childboards"]) != 0:
                        categories_forums[prev_index]["childboards"] += j["childboards"]
                    continue

                j["link"] = url_merge(url, j["link"])
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
                lastpost["link"] = url_merge(url, lastpost["link"])
                lastpost["user_link"] = url_merge(url, lastpost["user_link"])
                if len(lastpost["user"]) == 0:
                    lastpost["user"] = lastpost.get("user2", "")
                try:
                    lastpost.pop("user2")
                except KeyError:
                    pass

                if j.get("moderators") is None:
                    j["moderators"] = []

                for g in j["moderators"]:
                    g["user_link"] = url_merge(url, g["user_link"])

                prev_index = len(categories_forums)
                categories_forums.append(j)

            i["forums"] = categories_forums

        threads = t["threads"]
        if len(threads) == 0:
            threads = t["threads2"]

        for i in threads:
            if len(i["link"]) == 0:
                continue

            i["link"] = url_merge(url, i["link"])
            i["user_link"] = url_merge(url, i["user_link"])
            i["lastpost"]["user_link"] = url_merge(url, i["lastpost"]["user_link"])
            i["type1"] = url_merge_r(url, i.get("type1", ""))
            i["type2"] = url_merge_r(url, i.get("type2", ""))

            icons = i["icons"]
            for j, g in enumerate(icons):
                icons[j] = url_merge(url, g)

        return {
            "format_version": "smf-1-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }


class smf2(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                re.compile(r"^/.*([?/&;]topic[=,])(\d+)"),
                2,
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, i_id):
            ret = {"format_version": "smf-2-thread", "url": url, "id": i_id}
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
                title = forumposts.search(r'h1 | "%i"') + rq.search(
                    r'B>h[0-9] .display_title; span #top_subject | "%i"'
                )
                viewed = forumposts.search(
                    r'div .display-info;  li m@v>"comments" | "%i\n" / sed "s/<[^>]*>//g; s/ .*//"'
                )[:-1]

            ret["title"] = title
            try:
                ret["viewed"] = int(viewed)
            except ValueError:
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
                    .avatar div .poster; { ul #B>msg_[0-9]*_extra_info, ul .user_info }; li .avatar; img src | "%(src)v",
                    .userinfo div .poster; { ul #B>msg_[0-9]*_extra_info, ul .user_info }; li -.avatar class; {
                        .key * l@[0] | "%(class)v",
                        .value * l@[0] | "%i"
                    } |
                } |
            """
            )

            while True:
                t = json.loads(rq.search(expr))
                for i in t["posts"]:
                    i["avatar"] = url_merge_r(url, i["avatar"])
                posts += t["posts"]

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(url, rq)
                if nexturl is None:
                    break
                rq = self.session.get_html(nexturl, settings, state, self.trim)

            ret["posts"] = posts
            return ret

        def get_improper_url(self, url, rq, settings, state):
            if rq is None:
                rq = self.session.get_html(url, settings, state, self.trim)

            try:
                i_id = int(rq.search('input name=sd_topic value | "%(value)v"'))
            except ValueError:
                warnings.warn('url leads to improper forum - "{}"'.format(url))
                return [None, 0]

            return [rq, i_id]

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
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = guesslist

        self.findroot_expr = reliq.expr(
            r"""
            {
                * #E>(menu|site_menu|main_menu|nav|navigation|navigation-root|header|kwick|button_home|toolbar-l); li,
                div #submenu,
                ul .E>(si[td]ebar-menu|main-navigation|topnav),
            }; a href | "%(href)v\n" / sed "
                /[;&?]action=/{/=forum$/!bskip}
                \#(/((board|forum|foro)s?|community)(\.([a-zA-Z0-9_-]+\.)+[a-zA-Z]+)?(/(index\.(html|php))?|\.(html|php))?(\?[^/]*)?|[;&?]action=forum)$#{p;q}
                :skip
                1!G; h
                $p
            " "En" line [-] sed "s/&amp;/\&/g" tr "\n"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|index\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        return rq.search(
            r'div .pagelinks [0]; E>(a|span|strong) m@vB>"[a-zA-Z .]" l@[1] | "%(href)v %i\n" / sed "$q; /^ /{N;D;s/ .*//;p;q}" "n"'
        )[:-1]

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                    .categories {
                        div #boardindex_table; * #b>category_,
                        div #bodyarea; div .categoryframe child@,
                        div #E>board_[0-9]+_childboards,
                        div #childboards; table .boardsframe child@
                    }; {
                        {
                            * #E>category_[0-9]+,
                            div .categoryframe self@,
                            div #E>board_[0-9]+_childboards self@,
                            table .boardsframe self@; [0] tr child@
                        }; [0] ( h3 )( td ) .catbg; {
                            .name * self@ | "%t" trim,
                            .description [0] div .desc ssub@ | "%i"
                        },
                        .forums {
                            {
                                * #E>category_[0-9]+_boards,
                                div .categoryframe self@; table .boardsframe child@
                            }; ( tr )( div ) -style child@,
                            table .boardsframe self@; [1:] tr child@,
                            div #E>board_[0-9]+_childboards self@; * #E>board_[0-9]+,
                        }; {
                            .status [0] * ( .b>icon )( .board_icon ); [0] ( a )( img )( span ) title | "%(title)v",
                            * .info child@; {
                                [0] a href; {
                                    .link * self@ | "%(href)v",
                                    .name * self@ | "%i"
                                },
                                .description [0] ( p -id -.moderators )( div .board_description ) child@ | "%i",
                            },
                            .childboards * .children; a; {
                                .link * self@ | "%(href)v",
                                .name * self@ | "%i",
                                .status * self@ | "%(title)v" sed "s/ (.*//",
                                .topics.u * self@ | "%(title)v" sed "s/.* (//; s/,.*//",
                                .posts.u * self@ | "%(title)v" sed "s/.*,//"
                            } | ,
                            .moderators * .moderators; a href; {
                                .user_link * self@ | "%(href)v",
                                .user * self@ | "%i"
                            } | ,
                            * .e>stats child@; { p child@, * self@ }; [0] * self@; {
                                .posts.u * self@ | "%i" sed 's/<.*//;s/,//g',
                                .topics.u * self@ | "%i" sed 's/.*>//;s/,//g'
                            },
                            .posts2.u [0] * .windowbg c@[0] child@ | "%i" sed 's/,//g',
                            .topics2.u [1] * .windowbg c@[0] child@ | "%i" sed 's/,//g',
                            .s * .lastpost child@; { p child@, * self@ }; [0] * self@; {
                                .lastpost * self@ -C@"[0] span .postby"; {
                                    [0] a href; {
                                        .user * self@ | "%i",
                                        .user_link * self@ | "%(href)v"
                                    },
                                    [1] a href; {
                                        .title * self@ | "%(title)v",
                                        .link * self@ | "%(href)v"
                                    },
                                    .date * self@ | "%t" tr "\n\t\r" trim sed "s/.*>//; s/([^ ]* ){3}//; s/^ *at //" "E"
                                },
                                .lastpost2 * self@ C@"[0] span .postby"; {
                                    [0] a href; {
                                        .title * self@ | "%(title)v",
                                        .link * self@ | "%(href)v"
                                    },
                                    [1] a href; {
                                        .user * self@ | "%i",
                                        .user_link * self@ | "%(href)v"
                                    },
                                    .date * self@ | "%t" trim sed "s/^at //"
                                }
                            }
                        } |
                    } | ,
                    .threads.u div #messageindex; {
                        table ( .table_grid )( .boardsframe ) child@; tbody child@; tr c@[4:] child@,
                        div #topic_container child@; div child@
                    }; {
                        .type1 * ( .icon1 )( .board_icon ) child@; img src | "%(src)v",
                        .type2 * .icon2 child@; img src | "%(src)v",
                        * ( .subject )( .info ) child@; {
                            [0] a href; {
                                .title * self@ | "%i",
                                .link * self@ | "%(href)v"
                            },
                            [1] a href; {
                                .user * self@ | "%t" trim,
                                .user_link * self@ | "%(href)v"
                            },
                            .lastpage.u [-] a ( .navPages )( .nav_page ) c@[0] m@v>"All" | "%i",
                            .icons.a {
                                * class self@,
                                div .icons; span .main_icons
                            }; * self@ | "%(class)v" / trim tr " " "\n" sed "/^subject$/d; /^windowbg/d; /^info$/d; /^info_block$/d; /^main_icons$/d; /^info_blockmain_icons$/d; /^lockmain_icons$/d",
                            .icons2.a img id child@ | "%(src)v\n" sed 's/.*\///; s/\..*//'
                        },
                        td .starter child@; a; {
                            .user2 | "%i",
                            .user_link2 * self@ | "%(href)v"
                        },
                        {
                            td .stats child@,
                            * .board_stats child@; p
                        }; {
                            .replies.u * self@ | "%i" sed "s/<.*//;s/,//g;q",
                            .views.u * self@ | "%i" tr "\n\t\r," sed "s/.*>//"
                        },
                        .replies2.u td .replies c@[0] child@ | "%i" tr ",",
                        .views2.u td .views c@[0] child@ | "%i" tr ",",
                        .s * .lastpost child@; {
                            .lastpost [0] v>p child@; * rparent@; {
                                .link [0] a href | "%(href)v",
                                [1] a href; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                },
                                .date {
                                    span .smalltext child@,
                                    * self@
                                }; [0] * self@ | "%i" tr "\n\t\r" sed "s/<br.*//; s/.*<\/a>//; s/<[^>]*>//g; s/ by //" trim
                            },
                            .lastpost2 p child@; {
                                [0] a href; {
                                    .date * self@ | "%T" trim,
                                    .link * self@ | "%(href)v"
                                },
                                [1] a href; {
                                    .user * self@ | "%i",
                                    .user_link * self@ | "%(href)v"
                                }
                            }
                        }
                    } |
                """
            )
        )

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
                for g in j["childboards"]:
                    g["link"] = url_merge(url, g["link"])

                if len(j["link"]) == 0:
                    if prev_forums_index is not None and len(j["childboards"]) != 0:
                        out_forums[prev_forums_index]["childboards"] += j["childboards"]
                    continue

                j["link"] = url_merge(url, j["link"])
                for g in j["moderators"]:
                    g["user_link"] = url_merge(url, g["user_link"])

                redirects = 0

                lastpost = j["s"]["lastpost"]
                if len(lastpost["user_link"]) == 0 and len(lastpost["link"]) == 0:
                    lastpost = j["s"]["lastpost2"]
                j.pop("s")

                if len(lastpost["user_link"]) == 0 and len(lastpost["link"]) == 0:
                    redirects = j["posts"]
                    j["posts"] = 0
                    j["topics"] = 0
                j["redirects"] = redirects

                lastpost["link"] = url_merge(url, lastpost["link"])
                lastpost["user_link"] = url_merge(url, lastpost["user_link"])
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
            i["link"] = url_merge(url, i["link"])
            i["type1"] = url_merge(url, i["type1"])
            i["type2"] = url_merge(url, i["type2"])

            if len(i["user_link"]) == 0:
                i["user"] = i["user2"]
                i["user_link"] = i["user_link2"]
            i.pop("user2")
            i.pop("user_link2")
            i["user_link"] = url_merge(url, i["user_link"])

            i["icons"] += i["icons2"]
            i.pop("icons2")

            if i["replies"] == 0:
                i["replies"] = i["replies2"]
                i["views"] = i["views2"]
            i.pop("replies2")
            i.pop("views2")

            lastpost = i["s"]["lastpost"]
            if len(lastpost["link"]) == 0 and len(lastpost["user_link"]) == 0:
                lastpost = i["s"]["lastpost2"]
            i.pop("s")
            lastpost["link"] = url_merge(url, lastpost["link"])
            lastpost["user_link"] = url_merge(url, lastpost["user_link"])
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

        self.guesslist = guesslist

    def identify_page(self, url, rq, cookies):
        return smfIdentify(self, url, rq, cookies)
