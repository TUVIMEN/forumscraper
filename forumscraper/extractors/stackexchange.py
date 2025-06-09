# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

from pathlib import Path
import re
import copy

from ..defs import reliq
from ..utils import (
    dict_add,
    get_settings,
    url_valid,
    conv_short_size,
)
from .common import ItemExtractor, ForumExtractor, write_html
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

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {"format_version": "stackexchange-user", "url": url, "id": int(i_id)}

            t = rq.json(Path("stackexchange/user.reliq"))

            t["reputation"] = conv_short_size(t["reputation"])
            t["reached"] = conv_short_size(t["reached"])
            t["answers"] = conv_short_size(t["answers"])
            t["questions"] = conv_short_size(t["questions"])

            for i in t["communities"]:
                i["reputation"] = conv_short_size(i["reputation"])

            for i in t["badges"]:
                for j in i["achievements"]:
                    if j["amount"] == 0:
                        j["amount"] = 1

            for i in t["tags"]:
                i["score"] = conv_short_size(i["score"])
                i["posts"] = conv_short_size(i["posts"])

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

        def get_post_comments(self, rq, url, postid, settings, state, path):
            n = rq.search(r'div #b>comments-link-; a .comments-link i@b>"Show " | "t"')
            if len(n) > 0:
                rsettings = copy.copy(settings["requests"])
                if rsettings.get("headers") is None:
                    rsettings["headers"] = {}
                rsettings["headers"].update({"x-Requested-With": "XMLHttpRequest"})

                rq = self.session.get_html(
                    "{}/posts/{}/comments".format(url_valid(url, base=True)[0], postid),
                    **rsettings,
                )
                write_html(path + "-comments-" + str(postid), rq, settings)

            comments = rq.json(Path("stackexchange/post-comments.reliq"))["comments"]

            return comments

        def get_post(self, rq, url, settings, state, path):
            post = rq.json(Path("stackexchange/post.reliq"))

            post["comments"] = self.get_post_comments(
                rq, url, post["id"], settings, state, path
            )
            return post

        def get_contents(self, rq, settings, state, url, i_id, path):
            ret = {
                "format_version": "stackexchange-thread",
                "url": url,
                "id": int(i_id),
            }

            t = rq.json(Path("stackexchange/thread.reliq"))
            dict_add(ret, t)

            posts = []
            posts.append(
                self.get_post(
                    rq.filter("div #question").self()[0],
                    url,
                    settings,
                    state,
                    path,
                )
            )

            for rq in self.next(rq, settings, state, path):
                for i in rq.filter(r"div #b>answer-").self():
                    posts.append(self.get_post(i, url, settings, state, path))

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

    def process_board_r(self, url, rq, settings, state):
        return self.process_forum_r(url, rq, settings, state)

    def process_forum_r(self, url, rq, settings, state):
        threads = rq.json(Path("stackexchange/forum.reliq"))["threads"]

        return {
            "format_version": "stackexchange-forum",
            "url": url,
            "threads": threads,
        }
