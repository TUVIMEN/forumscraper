# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import re
import json
from reliq import reliq

from ..utils import dict_add, url_merge_r, url_merge
from .common import ItemExtractor, ForumExtractor
from .identify import identify_vbulletin
from ..exceptions import AlreadyVisitedError


class vbulletin(ForumExtractor):
    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    r"/([0-9]+)-[^/]*/?$",
                    1,
                ),
                (
                    r"/.*([?&](t=)?|-)([0-9]+)[^/]*/?$",
                    3,
                ),
            ]
            self.trim = True

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {"format_version": "vbulletin-3+-thread", "url": url, "id": int(i_id)}
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                    .title {
                        [0] * .threadtitle; * c@[0] i@>[!0] | "%Di" ||
                        [0] * .main-title c@[0] | "%Di" ||
                        td .navbar; strong child@; * [0] c@[0] i@>[!0] | "%Di" / sed "s/<[^>]+>//g" "E" ||
                        * .thread-breadcrumb; * [0] c@[0] i@>[!0] | "%Di" ||
                        * #toolbar; [0] h1 c@[0] | "%Di"
                    } / trim,
                    .path.a {
                        span c@[1:5] .navbar; a [0] i@>[!0] child@ | "%Di\n" ||
                        {
                            div itemtype="http://schema.org/BreadcrumbList" ||
                            [0] * ( #breadcrumbs )( .breadcrumbs ) ||
                            * .navbit
                        }; a c@[:5]; * [0] c@[0] i@>[!0] | "%Di\n"
                    } / trim "\n"
            """
                )
            )
            dict_add(ret, t)

            posts = []
            expr = reliq.expr(
                r"""
                .posts {
                    [0] ul .conversation-list,
                    * #posts; {
                        ul child@ ||
                        * self@
                    }
                }; * -#lastpost -.ad_block child@; {
                    .date {
                        time itemprop=dateCreated | "%(datetime)v" ||
                        span .date | "%DT" ||
                        span .timepost | "%i" ||
                        a name=E>post[0-9]+; * parent@ | "%DT" / sed "s/<[^>]+>//g" "E" trim
                    },

                    .id.u {
                        [0] a name=E>post[0-9]+ | "%(name)v" ||
                        [0] a #E>post[0-9]+ | "%(id)v"
                    } / sed "s/^post//",

                    .title {
                        h2 ( .title )( .b-post__title )( .posttitle ) | "%Di" ||
                        img .inlineimg; div .smallfont c@[:3] parent@ | "%Di" ||
                        div .tittle | "%Di"
                    } / trim,

                    .content div ( #b>post_message_ )( .js-post__content-text ) | "%i",

                    .signature {
                        div .post-signature | "%i" ||
                        div .signaturecontainer | "%i" ||
                        [0] div i@bB>"[^<]*________" | "%Di"
                    },

                    .edited {
                        div .b-post__edit ||
                        div .smallfont; [0] em child@ ||
                        blockquote .lastedited
                    }; {
                        [0] a; {
                            .userid.u * self@ | "%(data-vbnamecard)v",
                            .user_link * self@ | "%(href)v"
                        },
                        .user {
                            [0] a | "%i" ||
                            * self@ | "%t" / tr "\n\t\r" sed "s/[(;)].*//g; s/  *$//; s/.* //"
                        },
                        .date {
                            * self@ | "%t" / tr "\n\t\r" sed "s/.*[(;]//g",
                            span .time | " %i"
                        } / sed "s/)$//" trim
                    },

                    .attachments li .b-post-attachments__item; a [0]; {
                        .link * self@ | "%(href)v",
                        .name span .h-wordwrap | "%i" / sed "s/&lrm;$//" decode trim,
                        span c@[0] i@e>")"; {
                            .size * self@ | "%i" / sed "s/^(//;s/,.*//",
                            .views.u * self@ | "%i" / sed "s/.*,//"
                        }
                    } | ,
                    .attachments2 {
                        div .attachments; li c@[1:] ||
                        a href=Eb>"(attachment|download)\.php\?"; td parent@
                    }; {
                        a [0]; {
                            .link * self@ | "%(href)v",
                            .name * self@ | "%i" / sed "s/&lrm;$//" decode trim
                        },
                        .size * self@ | "%t" / sed "/(/{ s/.*(//; s/,.*//; p }" "n" trim,
                        .views.u * self@ | "%t" / sed "/(/{ s/.*(//; s/.*,//; p }" "n"
                    } | ,


                    .reactions div .reactions__topic-reaction; {
                        .type [0] span .reactions__emoji | "%Di",
                        .count.u [0] span .reactions__topic-reaction--count | "%i"
                    } | ,

                    .thankedby_users.a {
                        div .likes_postbit; li; a [0]; * c@[0] | "%i\n" ||
                        * #b>post_thanks_box_; [-] a; * parent@; * c@[0] | "%i\n"
                    },
                    .thankedby_dates.a(",") * #b>post_thanks_box_; [-] a; * parent@ | "%Dt" / tr "\n\t\r() " tr "[[:print:]]" "" "c" sed "s/<!--[^>]*>//g; s#<[^>]*>##g",

                    .user {
                        [0] * #b>postmenu_; [-] * -has@"[0] * #b>td_post_" ancestor@ ||
                        [0] div ( .userinfo )( .userinfo_noavatar )( .postauthor )
                    }; {
                        {
                            [0] * .username ||
                            [0] a .bigusername ||
                            div .author ||
                            [0] a .siteicon_profile ||
                            * #b>postmenu_ c@[0]
                        }; {
                            .link [0] a | "%(href)v",
                            .name [0] * c@[0] | "%Di" / trim
                        },
                        .avatar {
                            [0] * .E>"(postuseravatar(link)?|(b-)?avatar(-block)?|userpic|user-avatar-h)"; img | "%(src)v" ||
                            [0] img src=Ea>"((/|^)(forum|custom)?avatars?/|image\.php\?)" | "%(src)v"
                        },

                        .title {
                            * ( .usertitle )( .usertittle ) ||
                            * c@[0] i@>[1:]; [0] * c@[:5] .smallfont ancestor@ ||
                            [0] * c@[0] .smallfont
                        }; [0] * c@[0] i@>[1:] | "%Di" / trim,

                        .rank.u {
                            [0] * ( .rank )( .b-userinfo__rank ) | "%c" ||
                            [-] * #b>repdisplay_ | "%c" ||
                            * b-meter__bar i@>[1:] | "l" / wc "c"
                        },
                        .rank-name [0] a .rank-link | "%Di",

                        .custom1 * ( .userinfo_extra )( .userfield ); dl; dt; {
                            .key * self@ | "%Di" trim,
                            .value [0] dd ssub@; [0] * c@[0] i@>[1:] | "%Di" trim
                        } | ,
                        .custom2 li .b-userinfo__additional-info; {
                            .key label child@ | "%Di" trim,
                            .value span child@; [0] * c@[0] i@>[1:]  | "%Di" trim
                        } | ,
                        .custom3 div .fields-list; div .line; {
                            .key span child@ | "%Di" trim,
                            .value strong child@ | "%Di" trim
                        } | ,
                        .custom4.a {
                            div c@[0] i@Bf>" *"; [0] div ( .smallfont )( .userinfo ) parent@ | "%Di" trim ||
                            div a@[0] c@[:2] i@":"; [0] div c@[:14] parent@ | "%Di" trim
                        } / tr "\r\t" sed "
                            :r
                            s/ //g
                            s/<!--[^>]*>//g
                            s/<div>//g
                            s/<\/div>/\n/g
                            s/<b>//g
                            s/<\/b>//g
                            s/< *br *(\/ *)?>/\n/g

                            /^ *$/d
                            /: *$/{
                                N
                                s/\n/ /g
                                br
                            }
                        " "E" sed "/^ *$/d; s/^ *//; s/ *$//"
                    }
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
                nexturl = self.get_next(ref, rq)
                if nexturl is None:
                    break

                try:
                    rq, ref = self.session.get_html(
                        nexturl, settings, state, trim=self.trim
                    )
                except AlreadyVisitedError:
                    break

            outposts = []
            for i in posts:
                thankedby = []
                for j in range(len(i["thankedby_users"])):
                    thankedby.append(
                        {
                            "user": i["thankedby_users"][j],
                            "date": (
                                i["thankedby_dates"][j]
                                if j < len(i["thankedby_dates"])
                                else ""
                            ),
                        }
                    )
                i.pop("thankedby_users")
                i.pop("thankedby_dates")
                i["thankedby"] = thankedby

                if i["date"] == "" and i["id"] == 0 and i["content"] == "":
                    if len(outposts) > 0:
                        outposts[len(outposts) - 1]["thankedby"] += thankedby
                    continue

                i["edited"]["user_link"] = url_merge_r(ref, i["edited"]["user_link"])

                attachments = i["attachments"]
                if len(attachments) < len(i["attachments2"]):
                    attachments = i["attachments2"]
                i.pop("attachments2")
                for j in attachments:
                    j["link"] = url_merge_r(ref, j["link"])
                i["attachments"] = attachments

                user = i["user"]
                user["link"] = url_merge_r(ref, user["link"])
                user["avatar"] = url_merge_r(ref, user["avatar"])

                custom = user["custom1"]
                if len(custom) < len(user["custom2"]):
                    custom = user["custom2"]
                if len(custom) < len(user["custom3"]):
                    custom = user["custom3"]
                if len(custom) < len(user["custom4"]):
                    custom = []
                    for j in user["custom4"]:
                        tokens = j.split(":", 1)
                        if len(tokens) < 2:
                            custom.append({"key": None, "value": j})
                        else:
                            custom.append(
                                {"key": tokens[0].strip(), "value": tokens[1].strip()}
                            )
                user.pop("custom1")
                user.pop("custom2")
                user.pop("custom3")
                user.pop("custom4")
                user["custom"] = custom

                outposts.append(i)

            ret["posts"] = outposts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_vbulletin

        self.thread = self.Thread(self.session)
        self.thread.get_next = self.get_next

        self.trim = True

        self.forum_forums_expr = reliq.expr(
            r'''{
                * .forumtitle; a l@[:2] c@[0] | "%(href)v\n",
                * #E>f[0-9]+; a [0] c@[:4] | "%(href)v\n",
                a .forum-title c@[0] | "%(href)v\n",
                a href=E>"/f[0-9]+/" c@[0] | "%(href)v\n",
                h2 .forumTitle; a [0] l@[:3] c@[:3] | "%(href)v\n"
            } / sed "s/&amp;/\&/g" sort "u"'''
        )
        self.forum_threads_expr = reliq.expr(
            r'a ( #b>thread_title_ )( .topic-title ) href | "%(href)v\n" / sed "s/&amp;/\&/g"'
        )
        self.board_forums_expr = self.forum_forums_expr
        self.guesslist = [
            {
                "func": "get_thread",
                "exprs": [
                    r"/showthread\.php\?",
                ],
            },
            {
                "func": "get_forum",
                "exprs": [r"/forumdisplay\.php(\?|/)", "/forums?/[^/]+/?$"],
            },
            {
                "func": "get_thread",
                "exprs": [
                    r"(/[^/]+){2,}/\d+-[^/]+$",
                    r"(/[^/]+){2,}/[^/]+-\d+(\.html|/)$",
                ],
            },
            {"func": "get_forum", "exprs": [r"(/[^/]+){3,}/$"]},
            {
                "func": "get_board",
                "exprs": [r"/forums?(/|\.php(\?[^/]*)?)$"],
            },
            {"func": "get_board", "exprs": None},
        ]

        self.findroot_expr = reliq.expr(
            r"""
                {
                    [0] * ( #breadcrumbs )( .breadcrumbs )( #breadcrumb )( .breadcrumbs-table ); a href=>[1:] | "%(href)v\n" / sed "
                        \#(/|^)(((forum|foro|board)s?|community)/?|forum\.php)(\?[^/]*)?$#{p;q}
                        1!G
                        h
                       $p" "En" line [-],
                    [0] span .navbar; a href | "%(href)v\n"
                } / line [0] tr "\n" sed "s/&amp;/\&/g"
            """
        )
        self.findroot_board = True
        self.findroot_board_expr = re.compile(
            r"^(/[^\.-])?/((board|forum|foro)s?|(index|forum)\.(php|html)|community|communaute|comunidad)(/|\?[^/]*)?$",
        )

    def get_next_page(self, rq):
        url = rq.search(
            r'''{
                * ( .pagenav )( .threadpagenav )( .pagination )( #mb_pagenav ); {
                    [0] a rel=next | "%(href)v",
                    [0] a .js-pagenav-next-button href=b>http | "%(href)v",
                },
                span .pages; [0] span .currentpage; [0] a ssub@ | "%(href)v"
            } / line [0] sed "/^javascript:/d; s/&amp;/\&/g"'''
        )

        return url

    def process_board_r(self, url, ref, rq, settings, state):
        return self.process_forum_r(url, ref, rq, settings, state)

    def process_forum_r(self, url, ref, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                .categories {
                    * #b>collapseobj_forumbit_ ||
                    * ( #E>forum[0-9]+ )( .subforum-list ) ||
                    * #E>f[0-9]+; * parent@ ||
                    li .forumRow
                }; {
                    .header * self@ #b>collapseobj_forumbit_; {
                        [0] * spre@; * -#b>collapseobj_forumbit_ self@ ||
                        * parent@; [0] * spre@; * -#b>collapseobj_forumbit_ self@
                    }; {
                        .name {
                            [0] a -has@"[0] img"; [0] * c@[0] i@>[1:] | "%Di" ||
                            [0] a; * parent@ | "%Dt"
                        } / trim,
                        .link [0] a -has@"[0] img" | "%(href)v",
                        .description [0] * .smallfont c@[0] i@>[1:] | "%Di",
                    },
                    .header2 * self@ #E>forum[0-9]+; {
                        * .category-header self@ ||
                        [1] * ancestor@; * #E>cat[0-9]+ self@
                    }; {
                        .name {
                            a .category c@[0] | "%Di" ||
                            * .catTitle; [0] a; * c@[0] i@>[1:] | "%Di" ||
                            [0] * .forumhead; span .forumtitle; [0] a; * c@[0] i@>[1:] | "%Di"
                        } / trim,
                        .link {
                            a .category c@[0] | "%(href)v" ||
                            * .catTitle; [0] a | "%(href)v" ||
                            [0] * .forumhead; * .forumtitle; [0] a | "%(href)v"
                        },
                        .description [0] * .forumhead; * .subforumdescription; [0] * c@[0] i@>[1:] | "%Di"
                    },

                    .forums {
                        * self@ #b>collapseobj_forumbit_; * -thead child@ ||
                        * self@
                    }; {
                        .status {
                            [0] img ( #b>forum_statusicon_ )( .forumicon ) | "%(src)v" ||
                            [0] span .icon | "%(title)v"
                        },
                        {
                            * .forum-title ||
                            [0] v>span .forumtitle ||
                            [0] a c@[:1]
                        }; {
                            .title [0] * c@[0] i@>[1:] | "%Di" trim,
                            .link [0] a | "%(href)v"
                        },
                        .description {
                            [0] * ( .forum-desc )( .forumdescription )( .description ) | "%i" ||
                            div .smallfont; {
                                [0] * c@[0] i@b>[1:] self@ | "%i" ||
                                [0] * child@; v>strong * self@; * parent@ | "%i"
                            }
                        },
                        .viewing.u {
                            span .viewing | "%i" ||
                            [0] span c@[0] i@tb>"(" i@te>")" | "%i"
                        },

                        .childboards {
                            * .subforum-info ||
                            [0] * .subforums; * child@ ||
                            strong c@[0]; div .smallfont parent@
                        }; a; {
                            .link * self@ | "%(href)v",
                            .name [0] * c@[0] i@>[1:] | "%Di" / trim,
                            .icon [0] * spre@; {
                                img self@ | "%(src)v" ||
                                span self@ | "%(title)v"
                            },
                            [0] * ssub@; span c@[0] i@tb>"(" i@te>")"; {
                                .topics.u * self@ | "%i",
                                .posts.u * self@ | "%i" / sed "/\//!d; s#.*/##"
                            }
                        } | ,

                        .topics.u {
                            [0] * ( .topics-count )( .threadcount ) c@[0] | "%i" ||
                            * ( .forumstats )( .forumstats_2 ); [0] * c@[0] child@ | "%i" ||
                            [0] * c@[0] i@tEf>"(([0-9]+,)+)?[0-9]+" | "%i" ||
                            [0] * c@[0] i@tEf>"(([0-9]+,)+)?[0-9]+ */ *(([0-9]+,)+)?[0-9]+" | "%i"
                        } / tr ",.",
                        .posts.u {
                            [0] * ( .posts-count )( .postcount ) c@[0] | "%i" ||
                            * ( .forumstats )( .forumstats_2 ); [1] * c@[0] child@ | "%i" ||
                            [1] * c@[0] i@tEf>"(([0-9]+,)+)?[0-9]+" | "%i" ||
                            [0] * c@[0] i@tEf>"(([0-9]+,)+)?[0-9]+ */ *(([0-9]+,)+)?[0-9]+" | "%i" / sed "s/.*\///"
                        } / tr ",.",

                        .lastpost {
                            [0] * ( .i>lastpost )( .i>forumlastpost ) ||
                            strong c@[0] i@>[1:]; a parent@; div [0] l@[-5:0] .smallfont ancestor@; [-] * self@
                        }; {
                            {
                                [0] * ( .lastpost-title )( .lastposttitle )( .title ) ||
                                [0] strong c@[0]; * parent@
                            }; {
                                .title [0] * c@[0] i@>[1:] | "%Di" / trim,
                                .link [0] a | "%(href)v",
                            },
                            .icon {
                                * .lastposttitle; [0] img | "%(src)v" ||
                                [0] img .inlineimg | "%(src)v"
                            },
                            .date {
                                [0] * ( .lastpost-date )( .lastpostdate )( .time ) | "%DT" trim,
                                [-] div; * self@ c@[:5] | "%DT" trim
                            },
                            .user {
                                * ( .lastpost-by )( .lastpostby ); [0] a ||
                                * .title ||
                                [-1] div; * c@[:1] self@
                            }; [0] * c@[0] i@>[1:] | "%Di" trim,
                            .user_link {
                                * ( .lastpost-by )( .lastpostby ) ||
                                [-1] div; * c@[1] self@
                            }; [0] a; * self@ | "%(href)v",
                            .avatar a .avatar; [0] img | "%(src)v"
                        }
                    } |
                } | ,

                .threads {
                    li #b>thread_ ||
                    * .topic-item ||
                    * #b>threadbits_forum_; * child@ ||
                    * #threadslist; * child@
                }; {
                    .avatar a .avatar; [0] img | "%(src)v",
                    .icons.a {
                        [0] * .threadtitle; img child@ | "%(src)v\n" ||
                        img .js-post-icon | "%(src)v\n" ||
                        {
                            img #b>thread_statusicon_ | "%(src)v\n",
                            div c@[1]; img -id | "%(src)v\n",
                            * #b>td_threadtitle_; img | "%(src)v\n"
                        }
                    },
                    .prefix {
                        [0] * ( .topic-prefix )( .js-topic-prefix )( .prefix )( #b>thread_prefix_ ) | "%DT" trim ||
                        span c@[0] i@et>":" | "%Di"
                    },
                    {
                        [0] * ( .topic-title )( #b>thread_title_ ) ||
                        [0] * #b>thread_title_
                    }; [0] a; {
                        .link * self@ | "%(href)v",
                        .title * c@[0] i@>[1:] | "%Di" / trim
                    },
                    {
                        div .topic-info ||
                        div .threadmeta ||
                        * #b>td_threadtitle_; [-] div .smallfont
                    }; {
                        .user {
                            div .smallfont c@[:4] self@ | "%DT" trim ||
                            span style=b>cursor:; [0] * c@[0] i@>[1:] | "%Di" trim ||
                            [0] a; [0] * c@[0] i@>[1:] | "%Di" trim ||
                        },
                        .user_link {
                            [0] span onclick | "%(onclick)v" / sed "s/,.*//;s/.*'([^']+)'/\1/" "E" ||
                            [0] a | "%(href)v"
                        },
                        .date {
                            [0] span ( .date )( .time ) | "%Di" trim ||
                            span style=b>cursor:; [0] * ssub@; span self@; [0] * c@[0] i@>[1:] | "%Di" trim ||
                            div .author; [0] span c@[0] child@ i@E>" [0-9]{4}" | "%Di" trim ||
                            [0] a; * parent@ | "%Dt" / sed "s/.*,//; s/^ *//; s/ *$//" trim
                        } / sed "s/^on //"
                    },
                    .detailicons.a {
                        * .threaddetailicons; img | "%(src)v\n" ||
                        * .cell-icons; span | "%(title)v\n"
                    },
                    .posts.u {
                        {
                            div .posts-count ||
                            * .threadstats; {
                                [0] li -.hidden; [0] * c@[0] i@>[1:] ||
                                * self@
                            }
                        }; * self@ | "%i" ||
                        * c@[4:] title=aE>"[0-9]+.*,.*[0-9]+" | "%(title)v" / sed "s/, .*//"
                    } / tr ",.",
                    .views.u {
                        div .views-count | "%i" ||
                        * .threadstats; {
                            [1] li -.hidden; [0] * c@[0] i@>[1:] | "%i" ||
                            * self@ | "%i" / sed "s/.*>//"
                        }  ||
                        * c@[4:] title=aE>"[0-9]+.*,.*[0-9]+" | "%(title)v" / sed "s/.*, //"
                    } / tr ",.",
                    .reactions.u div .votes-count | "%i" tr ",.",
                    .rating.u {
                        [0] * .E>rating[0-9] | "%(class)v" ||
                        [0] img src=eE>"/rating_?[0-9]+.gif" | "%(src)v" / sed "s#.*/##"
                    },
                    .lastpage.u {
                        * #b>pagination_threadbit_; [-] a | "%i" ||
                        [0] * i@tb>"(" i@te>")" c@[1:]; [-] a; * self@ | "%(href)v" / sed "s#/$##; s#.*/##; s/.*;page=//" ||
                        * #b>td_threadtitle_; [-] a i@Eft>"[0-9]+" | "%i"
                    },

                    .lastpost [0] * ( .cell-lastpost )( .threadlastpost ); {
                        .avatar [0] a .avatar; [0] img src | "%(src)v",
                        {
                            * .lastpost-by; [0] a ||
                            [0] a .username
                        }; {
                            .user_link * self@ | "%(href)v",
                            .user * c@[0] i@>[1:] | "%Di"
                        },
                        .date {
                            span .post-date | "%Di" ||
                            * .time; * parent@ | "%Dt" trim ||
                            [0] * c@[0] i@E>"[0-9]{4}" | "%Di" / sed "s/ //g" trim
                        },
                        .link [0] a ( .go-to-last-post )( .lastpostdate ) | "%(href)v"
                    },
                    .lastpost_link [0] a .lastpostdate | "%(href)v",
                    .lastpost2 * c@[3:] title=aE>"[0-9]+.*,.*[0-9]+"; div .smallfont child@; {
                        .avatar nothing | "",
                        .user_link [0] a c@[0] | "%(href)v",
                        .user {
                            [0] a c@[0] | "%Di" trim ||
                            * self@ | "%Di" / tr "\n" sed "s/.*<br ?\/?>//" "E" trim
                        },
                        .date * self@ | "%i" / tr "\n" sed "
                            s/<br ?\/?>.*//
                            s/<[^>]*>//g
                        " "E" trim,
                        .link img; [-] a parent@ | "%(href)v"
                    }
                } |
                """
            )
        )

        categories = []
        prevcat = None
        for i in t["categories"]:
            c = {}
            header = i["header"]
            if header["name"] == "" and header["link"] == "":
                header = i["header2"]
            i.pop("header")
            i.pop("header2")

            header["link"] = url_merge(ref, header["link"])
            c["name"] = header["name"]
            c["link"] = header["link"]
            c["description"] = header["description"]

            forums = []
            for j in i["forums"]:
                if j["title"] == "" and j["link"] == "":
                    continue

                if j["status"].find("/"):
                    j["status"] = url_merge(ref, j["status"])

                j["link"] = url_merge(ref, j["link"])

                for k in j["childboards"]:
                    k["link"] = url_merge(ref, k["link"])
                    if k["icon"].find("/"):
                        k["icon"] = url_merge(ref, k["icon"])

                lastpost = j["lastpost"]
                lastpost["link"] = url_merge(ref, lastpost["link"])
                lastpost["icon"] = url_merge(ref, lastpost["icon"])
                lastpost["user_link"] = url_merge(ref, lastpost["user_link"])
                lastpost["avatar"] = url_merge(ref, lastpost["avatar"])

                forums.append(j)

            if prevcat is not None and c["link"] == prevcat["link"]:
                prevcat["forums"] += forums
            elif (
                prevcat is not None
                and c["link"] is None
                and (
                    len(prevcat["forums"]) == 0
                    or (
                        len(prevcat["forums"]) == 1
                        and prevcat["forums"][0]["link"] == prevcat["link"]
                    )
                )
            ):
                prevcat["forums"] = forums
            else:
                c["forums"] = forums
                prevcat = c
                categories.append(c)

        threads = []
        for i in t["threads"]:
            if i["link"] == "" and i["title"] == "" and i["user"] == "":
                continue

            i["avatar"] = url_merge(ref, i["avatar"])
            for j, icon in enumerate(i["icons"]):
                i["icons"][j] = url_merge(ref, i["icons"][j])

            i["link"] = url_merge(ref, i["link"])
            i["user_link"] = url_merge(ref, i["user_link"])
            for j, icon in enumerate(i["detailicons"]):
                if icon.find("/") != -1:
                    i["detailicons"][j] = url_merge(ref, icon)

            lastpost = i["lastpost"]
            if (
                lastpost["user"] == ""
                and lastpost["user_link"] == ""
                and lastpost["date"] == ""
            ):
                lastpost = i["lastpost2"]
            if lastpost["link"] == "":
                lastpost["link"] = i["lastpost_link"]
            i.pop("lastpost")
            i.pop("lastpost2")
            i.pop("lastpost_link")

            lastpost["link"] = url_merge(ref, lastpost["link"])
            lastpost["user_link"] = url_merge(ref, lastpost["user_link"])
            lastpost["avatar"] = url_merge(ref, lastpost["avatar"])

            i["lastpost"] = lastpost

            threads.append(i)

        return {
            "format_version": "vbulletin-3+-forum",
            "url": url,
            "categories": categories,
            "threads": threads,
        }
