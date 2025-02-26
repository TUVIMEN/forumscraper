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
from .identify import identify_stackexchange


class stackexchange(ForumExtractor):
    class User(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    re.compile(r"/users/(\d+)"),
                    1,
                )
            ]
            self.path_format = "m-{}"

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {"format_version": "stackexchange-user", "url": url, "id": int(i_id)}

            t = json.loads(
                rq.search(
                    r"""
                div #mainbar-full; {
                    [0] div child@; {
                        .avatar a; [0] img src | "%(src)v",
                        .user [0] div .fs-headline2 c@[0] | "%Di" trim,
                        .unregistered.b div .s-badge c@[0] | "t",
                        ul .list-reset; {
                            [0] * self@; li child@; {
                                .created [0] * self@; span title | "%(title)v",
                                .lastseen [1] * self@; div c@[0] i@bt>"Last seen" | "%i" sed "s/^Last seen//" trim
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
                            .reputation * self@ i@reputation; div child@ c@[0] | "%i" tr ",",
                            .reached * self@ i@reached; div child@ c@[0] | "%i" tr ",",
                            .answers * self@ i@answers; div child@ c@[0] | "%i" tr ",",
                            .questions * self@ i@questions; div child@ c@[0] | "%i" tr ","
                        },
                        div c@[0] i@tf>Communities; [1] * ancestor@; {
                            .communities-all [0] a i@bt>"View all" | "%(href)v",
                            .communities li; a; {
                                .profile * self@ | "%(href)v",
                                .reputation div .ml-auto c@[0] | "%i" tr ","
                            } |
                        },
                        .about [0] div .js-about-me-content | "%i",
                        div c@[0] i@tf>Badges; [1] * ancestor@; {
                            .badges-all [0] a i@bt>"View all" | "%(href)v",
                            .badges div .s-card; div .jc-space-between c@[6:] child@; {
                                .amount.u div .fs-title | "%i",
                                .name div .fs-caption | "%Di" line [0] " " tr " " / trim,
                                .achievements li; {
                                    a ( .badge )( .badge-tag ); {
                                        .tag.b * self@ .badge-tag | "t",
                                        .link * self@ | "%(href)v",
                                        .action * self@ | "%(title)v" / sed 's/^[^:]*: //',
                                        .name div c@[0] | "%Di" / trim
                                    },
                                    .amount.u div -.ml-auto child@ | "%t",
                                    .date div .ml-auto child@ c@[0] | "%i"
                                } |
                            } |
                        },
                        div c@[0] .fs-title i@tf>"Top tags"; [1] * ancestor@; {
                           .tags-all [0] a i@bt>"View all" | "%(href)v",
                           .tags [0] div .s-card; div child@; {
                                a .s-tag; {
                                    .link * self@ | "%(href)v",
                                    .name * self@ | "%Di" / trim
                                },
                                .badge [0] a .badge-tag title | "%(title)v" / sed "s/ .*//",
                                div .d-flex .ai-center; {
                                    .score div .tt-lowercase i@tf>Score; [0] * spre@ | "%i" tr ",",
                                    .posts div .tt-lowercase i@tf>Posts; [0] * spre@ | "%i" tr ",",
                                    .posts-percent.u div .tt-lowercase i@tf>"Posts %"; [0] * spre@ | "%i" tr ",",
                                },
                                .answered.u * self@ title | "%(title)v" / sed "/Gave/!d; s/.*. Gave ([0-9]+) non-wiki .*/\1/" "E",
                                .ansked.u * self@ title | "%(title)v" / sed "s/^Asked ([0-9]+) .*/\1/" "E",
                                .asked-score.u * self@ title | "%(title)v" / sed "/^Asked/!d; s/\..*//; s/^.*total score //" "E"
                            } |
                        },
                        div c@[0] .fs-title i@tf>"Top posts"; [2] * ancestor@; {
                            div i@bt>"View all"; a; {
                                .posts-answers-all * self@ i@ft>answers | "%(href)v",
                                .posts-questions-all * self@ i@ft>questions | "%(href)v"
                            },
                            .posts [0] div .s-card; div child@; {
                                .type [0] title | "%i",
                                .answered.b [0] div .s-badge__answered | "t",
                                .votes.u div .s-badge__votes | "%i",
                                [0] a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%Di" trim
                                },
                                .date span .relativetime title | "%(title)v"
                            } |
                        },
                        div c@[0] .fs-title i@tf>"Top network posts"; [1] * ancestor@; {
                           .network-posts-all [0] a i@bt>"View all" | "%(href)v",
                           .network-posts div .s-card; div child@; {
                                .votes.u div .s-badge__votes | "%i",
                                a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%Di" trim
                                },
                            } |
                        },
                        div c@[0] .fs-title i@tf>"Top Meta posts"; [1] * ancestor@; {
                            .meta-posts-asked.u div .ml8 title=b>asked | "%(title)v",
                            .meta-posts-answered.u div .ml8 title=b>gave | "%(title)v",
                            .meta-posts div .s-card; div child@; {
                                .votes.u div .s-badge__votes | "%i",
                                a .d-table; {
                                    .link * self@ | "%(href)v",
                                    .title * self@ | "%Di" trim
                                },
                            } |
                        }
                    }
                }
            """
                )
            )
            t["avatar"] = url_merge_r(ref, t["avatar"])
            t["meta-profile"] = url_merge_r(ref, t["meta-profile"])
            t["network-profile"] = url_merge_r(ref, t["network-profile"])

            t["reputation"] = conv_short_size(t["reputation"])
            t["reached"] = conv_short_size(t["reached"])
            t["answers"] = conv_short_size(t["answers"])
            t["questions"] = conv_short_size(t["questions"])

            t["communities-all"] = url_merge_r(ref, t["communities-all"])
            for i in t["communities"]:
                i["profile"] = url_merge_r(ref, i["profile"])
                i["reputation"] = conv_short_size(i["reputation"])

            t["badges-all"] = url_merge_r(ref, t["badges-all"])
            for i in t["badges"]:
                for j in i["achievements"]:
                    j["link"] = url_merge_r(ref, j["link"])
                    if j["amount"] == 0:
                        j["amount"] = 1

            t["tags-all"] = url_merge_r(ref, t["tags-all"])
            for i in t["tags"]:
                i["link"] = url_merge_r(ref, i["link"])
                i["score"] = conv_short_size(i["score"])
                i["posts"] = conv_short_size(i["posts"])

            t["posts-answers-all"] = url_merge_r(ref, t["posts-answers-all"])
            t["posts-questions-all"] = url_merge_r(ref, t["posts-questions-all"])
            for i in t["posts"]:
                i["link"] = url_merge_r(ref, i["link"])

            t["network-posts-all"] = url_merge_r(ref, t["network-posts-all"])
            for i in t["network-posts"]:
                i["link"] = url_merge_r(ref, i["link"])

            for i in t["meta-posts"]:
                i["link"] = url_merge_r(ref, i["link"])

            dict_add(ret, t)
            return ret

    class Thread(ItemExtractor):
        def __init__(self, session):
            super().__init__(session)

            self.match = [
                (
                    r"/questions/(\d+)",
                    1,
                )
            ]
            self.trim = True

        def get_post_comments(self, rq, url, ref, postid, settings, state):
            n = rq.search(r'div #b>comments-link-; a .comments-link i@b>"Show " | "t"')
            if len(n) > 0:
                nsettings = get_settings(
                    settings, headers={"x-Requested-With": "XMLHttpRequest"}
                )
                rq, ref = self.session.get_html(
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
                        .user * self@ | "%Di" trim,
                        .user_link * self@ | "%(href)v",
                        .reputation.u * self@ | "%(title)v" / tr ",."
                    },
                } |
             """
                )
            )["comments"]

            for i in comments:
                i["user_link"] = url_merge(ref, i["user_link"])
            return comments

        def get_post(self, rq, url, ref, settings, state):
            post = json.loads(
                rq.search(
                    r"""
                .id.u * self@ | "%(data-answerid)v %(data-questionid)v",
                .rating.i div .js-vote-count data-value | "%(data-value)v",
                .checkmark.b [0] div .js-accepted-answer-indicator | "t",
                .bounty.u [0] div .js-bounty-award | "%i",
                .content div class="s-prose js-post-body" | "%i",

                div .user-info i@"edited"; {
                    .edited span .relativetime | "%(title)v",
                    .editor {
                        .avatar img .bar-sm src | "%(src)v",
                         div .user-details; {
                            .name [0] * l@[1] c@[0] | "%Di" trim,
                            .link div .user-details; a href child@ | "%(href)v",
                            .reputation.u span .reputation-score | "%i" tr ",",
                            .gbadge.u span title=w>gold; span .badgecount | "%i",
                            .sbadge.u span title=w>silver; span .badgecount | "%i",
                            .bbadge.u span title=w>bronze; span .badgecount | "%i"
                        }
                    }
                },

                div .user-info i@v>"edited"; {
                    .date span .relativetime | "%(title)v",
                    .author {
                        .avatar img .bar-sm src | "%(src)v",
                         div .user-details; {
                            .name [0] * l@[1] c@[0] | "%Di" trim,
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
            post["author"]["avatar"] = url_merge(ref, post["author"]["avatar"])
            post["author"]["link"] = url_merge(ref, post["author"]["link"])
            post["editor"]["avatar"] = url_merge(ref, post["editor"]["avatar"])
            post["editor"]["link"] = url_merge(ref, post["editor"]["link"])

            post["comments"] = self.get_post_comments(
                rq, url, ref, post["id"], settings, state
            )
            return post

        def get_contents(self, rq, settings, state, url, ref, i_id):
            ret = {
                "format_version": "stackexchange-thread",
                "url": url,
                "id": int(i_id),
            }
            page = 0

            t = json.loads(
                rq.search(
                    r"""
                    .title h1 itemprop="name"; a | "%Di" / trim,
                    div .flex--item .mb8 .ws-nowrap; {
                        .views.u [0] * self@ i@"Viewed" | "%(title)v" / tr "0-9" "" "c",
                        .asked [0] * self@ i@"Asked"; [0] time itemprop="dateCreated" datetime | "%(datetime)v",
                        .modified [0] * self@ i@"Modified"; [0] a title | "%(title)v"
                    },
                    .tags.a div .ps-relative; a .post-tag | "%i\n"
                    """
                )
            )
            dict_add(ret, t)

            posts = []
            posts.append(
                self.get_post(
                    rq.filter("div #question").self()[0], url, ref, settings, state
                )
            )

            while True:
                for i in rq.filter(r"div #b>answer-").self():
                    posts.append(self.get_post(i, url, ref, settings, state))

                page += 1
                if (
                    settings["thread_pages_max"] != 0
                    and page >= settings["thread_pages_max"]
                ):
                    break
                nexturl = self.get_next(ref, rq)
                if nexturl is None:
                    break
                rq, ref = self.session.get_html(nexturl, settings, state)

            ret["posts"] = posts
            return ret

    def __init__(self, session=None, **kwargs):
        super().__init__(session, **kwargs)

        self.identify_func = identify_stackexchange

        # ucurl 'https://stackexchange.com/sites#' | reliq '[0] div .grid-view-container; a child@ | "%(href)v\n"' | sed 's/^https:\/\//"/;s/$/",/'
        self.domains = [
            "stackoverflow.com",
            "serverfault.com",
            "superuser.com",
            "meta.stackexchange.com",
            "webapps.stackexchange.com",
            "gaming.stackexchange.com",
            "webmasters.stackexchange.com",
            "cooking.stackexchange.com",
            "gamedev.stackexchange.com",
            "photo.stackexchange.com",
            "stats.stackexchange.com",
            "math.stackexchange.com",
            "diy.stackexchange.com",
            "gis.stackexchange.com",
            "tex.stackexchange.com",
            "askubuntu.com",
            "money.stackexchange.com",
            "english.stackexchange.com",
            "stackapps.com",
            "ux.stackexchange.com",
            "unix.stackexchange.com",
            "wordpress.stackexchange.com",
            "cstheory.stackexchange.com",
            "apple.stackexchange.com",
            "rpg.stackexchange.com",
            "bicycles.stackexchange.com",
            "softwareengineering.stackexchange.com",
            "electronics.stackexchange.com",
            "android.stackexchange.com",
            "boardgames.stackexchange.com",
            "physics.stackexchange.com",
            "homebrew.stackexchange.com",
            "security.stackexchange.com",
            "writing.stackexchange.com",
            "video.stackexchange.com",
            "graphicdesign.stackexchange.com",
            "dba.stackexchange.com",
            "scifi.stackexchange.com",
            "codereview.stackexchange.com",
            "codegolf.stackexchange.com",
            "quant.stackexchange.com",
            "pm.stackexchange.com",
            "skeptics.stackexchange.com",
            "fitness.stackexchange.com",
            "drupal.stackexchange.com",
            "mechanics.stackexchange.com",
            "parenting.stackexchange.com",
            "sharepoint.stackexchange.com",
            "music.stackexchange.com",
            "sqa.stackexchange.com",
            "judaism.stackexchange.com",
            "german.stackexchange.com",
            "japanese.stackexchange.com",
            "philosophy.stackexchange.com",
            "gardening.stackexchange.com",
            "travel.stackexchange.com",
            "crypto.stackexchange.com",
            "dsp.stackexchange.com",
            "french.stackexchange.com",
            "christianity.stackexchange.com",
            "bitcoin.stackexchange.com",
            "linguistics.stackexchange.com",
            "hermeneutics.stackexchange.com",
            "history.stackexchange.com",
            "bricks.stackexchange.com",
            "spanish.stackexchange.com",
            "scicomp.stackexchange.com",
            "movies.stackexchange.com",
            "chinese.stackexchange.com",
            "biology.stackexchange.com",
            "poker.stackexchange.com",
            "mathematica.stackexchange.com",
            "psychology.stackexchange.com",
            "outdoors.stackexchange.com",
            "martialarts.stackexchange.com",
            "sports.stackexchange.com",
            "academia.stackexchange.com",
            "cs.stackexchange.com",
            "workplace.stackexchange.com",
            "chemistry.stackexchange.com",
            "chess.stackexchange.com",
            "raspberrypi.stackexchange.com",
            "russian.stackexchange.com",
            "islam.stackexchange.com",
            "salesforce.stackexchange.com",
            "patents.stackexchange.com",
            "genealogy.stackexchange.com",
            "robotics.stackexchange.com",
            "expressionengine.stackexchange.com",
            "politics.stackexchange.com",
            "anime.stackexchange.com",
            "magento.stackexchange.com",
            "ell.stackexchange.com",
            "sustainability.stackexchange.com",
            "tridion.stackexchange.com",
            "reverseengineering.stackexchange.com",
            "networkengineering.stackexchange.com",
            "opendata.stackexchange.com",
            "freelancing.stackexchange.com",
            "blender.stackexchange.com",
            "mathoverflow.net",
            "space.stackexchange.com",
            "sound.stackexchange.com",
            "astronomy.stackexchange.com",
            "tor.stackexchange.com",
            "pets.stackexchange.com",
            "ham.stackexchange.com",
            "italian.stackexchange.com",
            "pt.stackoverflow.com",
            "aviation.stackexchange.com",
            "ebooks.stackexchange.com",
            "alcohol.stackexchange.com",
            "softwarerecs.stackexchange.com",
            "arduino.stackexchange.com",
            "expatriates.stackexchange.com",
            "matheducators.stackexchange.com",
            "earthscience.stackexchange.com",
            "joomla.stackexchange.com",
            "datascience.stackexchange.com",
            "puzzling.stackexchange.com",
            "craftcms.stackexchange.com",
            "buddhism.stackexchange.com",
            "hinduism.stackexchange.com",
            "communitybuilding.stackexchange.com",
            "worldbuilding.stackexchange.com",
            "ja.stackoverflow.com",
            "emacs.stackexchange.com",
            "hsm.stackexchange.com",
            "economics.stackexchange.com",
            "lifehacks.stackexchange.com",
            "engineering.stackexchange.com",
            "coffee.stackexchange.com",
            "vi.stackexchange.com",
            "musicfans.stackexchange.com",
            "woodworking.stackexchange.com",
            "civicrm.stackexchange.com",
            "medicalsciences.stackexchange.com",
            "ru.stackoverflow.com",
            "rus.stackexchange.com",
            "mythology.stackexchange.com",
            "law.stackexchange.com",
            "opensource.stackexchange.com",
            "elementaryos.stackexchange.com",
            "portuguese.stackexchange.com",
            "computergraphics.stackexchange.com",
            "hardwarerecs.stackexchange.com",
            "es.stackoverflow.com",
            "3dprinting.stackexchange.com",
            "ethereum.stackexchange.com",
            "latin.stackexchange.com",
            "languagelearning.stackexchange.com",
            "retrocomputing.stackexchange.com",
            "crafts.stackexchange.com",
            "korean.stackexchange.com",
            "monero.stackexchange.com",
            "ai.stackexchange.com",
            "esperanto.stackexchange.com",
            "sitecore.stackexchange.com",
            "iot.stackexchange.com",
            "literature.stackexchange.com",
            "vegetarianism.stackexchange.com",
            "ukrainian.stackexchange.com",
            "devops.stackexchange.com",
            "bioinformatics.stackexchange.com",
            "cseducators.stackexchange.com",
            "interpersonal.stackexchange.com",
            "iota.stackexchange.com",
            "stellar.stackexchange.com",
            "conlang.stackexchange.com",
            "quantumcomputing.stackexchange.com",
            "eosio.stackexchange.com",
            "tezos.stackexchange.com",
            "or.stackexchange.com",
            "drones.stackexchange.com",
            "mattermodeling.stackexchange.com",
            "cardano.stackexchange.com",
            "proofassistants.stackexchange.com",
            "substrate.stackexchange.com",
            "bioacoustics.stackexchange.com",
            "solana.stackexchange.com",
            "langdev.stackexchange.com",
            "genai.stackexchange.com",
        ]
        self.domain_guess_mandatory = True

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
                "func": "get_user",
                "exprs": [r"/users/(\d+)"],
            },
            {"func": "get_forum", "exprs": None},
        ]

    def get_next_page(self, rq):
        return rq.search(r'[0] div .pager-answers; [0] a rel="next" href | "%(href)v"')

    def get_forum_next_page(self, rq):
        return rq.search(r'div .pager; [0] a rel=next href | "%(href)v"')

    def process_board_r(self, url, ref, rq, settings, state):
        return self.process_forum_r(url, rq, ref, settings, state)

    def process_forum_r(self, url, ref, rq, settings, state):
        t = json.loads(
            rq.search(
                r"""
                    .threads div #b>question-summary-; {
                        div .s-post-summary--stats; div .s-post-summary--stats-item; {
                            .score.u [0] * self@ title=b>"Score of ",
                            .views.u [0] * self@ title=e>" views" | "%(title)v",
                            [0] span i@f>"answers"; {
                                .answers.u [0] span .e>-number spre@ | "%i",
                                .solved.b * .has-accepted-answer parent@ | "t"
                            },
                            .bounty.u * self@ .has-bounty | "%i"
                        },
                        div .s-post-summary--content; {
                            * .s-post-summary--content-title; [0] a; {
                                .title * self@ | "%Di" trim,
                                .link * self@ | "%(href)v"
                            },
                            .excerp * .s-post-summary--content-excerpt | "%i",
                            [0] * .s-post-summary--meta; {
                                .tags.a a .s-tag | "%i\n",
                                .author div .s-user-card; {
                                    .avatar img .s-avatar--image | "%(src)v",
                                    div .s-user-card--info; {
                                        .name [0] * c@[0] | "%Di" / trim,
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
            i["link"] = url_merge(ref, i["link"])
            i["author"]["link"] = url_merge(ref, i["author"]["link"])
            i["author"]["avatar"] = url_merge(ref, i["author"]["avatar"])

        return {
            "format_version": "stackexchange-forum",
            "url": url,
            "threads": threads,
        }
