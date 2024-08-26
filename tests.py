#!/usr/bin/env python
import sys
import os
import forumscraper


def trace(x1, x2, x3):
    pass


sys.settrace(trace)

os.chdir("j")

ex = forumscraper.Extractor(
    output=forumscraper.Outputs.write_by_id
    | forumscraper.Outputs.users
    | forumscraper.Outputs.threads,
    logger=sys.stdout,
    failed=sys.stderr,
)

# print(ex.get_board("https://kh-vids.net/forums/discussion.25/",output=forumscraper.Outputs.forums,accumulate=True))
# print(ex.get_board("https://kh-vids.net/categories/community.1/",output=forumscraper.Outputs.forums,accumulate=True,pages_max_depth=1))
# print(ex.get_forum("https://kh-vids.net/forums/new-releases.90/",output=forumscraper.Outputs.hash,thread_pages_max=1,accumulate=True,pages_max_depth=1))

# print(ex.get_forum("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=28",output=forumscraper.Outputs.threads))
# print(ex.get_forum("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=40&sid=4b714bb53c68e22a84c06d4a953a762b",output=forumscraper.Outputs.forums))
# print(ex.get_forum("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=40&sid=4b714bb53c68e22a84c06d4a953a762b",output=forumscraper.Outputs.forums,pages_max_depth=1))
# print(ex.get_forum("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=78",output=forumscraper.Outputs.dict,thread_pages_max=1))
# print(ex.get_forum("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=78",output=forumscraper.Outputs.dict,thread_pages_max=1,pages_threads_max=2))

# ex.xenforo.guess("https://neosmart.net/forums/", max_workers=8)
# ex.xenforo.v2.guess("https://neosmart.net/forums/")
# ex.phpbb.guess("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=40&sid=dc874a97c2d0463b497374eea460fad8")
# ex.smf.guess("http://750mm.pl/index.php?board=11.0;sort=replies;desc")
# ex.smf.v1.guess("http://750mm.pl/index.php?board=11.0;sort=replies;desc")
# ex.guess("http://750mm.pl/index.php?board=11.0;sort=replies;desc")

tested_threads = [
    (
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/",
        "xenforo",
        "v1",
    ),
    (
        "https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/",
        "xenforo",
        "v2",
    ),
    ("http://750mm.pl/index.php?topic=4892.0", "smf", "v1"),
    ("https://arizonagunowners.com/index.php/topic,16.0.html", "smf", "v2"),
    ("https://www.sciencemadness.org/whisper/viewthread.php?tid=158143", "xmb"),
    ("https://forum.anime-ultime.net/phpBB3/viewtopic.php?f=98&t=16040", "phpbb"),
    (
        "https://processwire.com/talk/topic/3553-handling-categories-on-a-product-catalogue/",
        "invision",
    ),
]

tested_forums = [
    ("https://kh-vids.net/forums/the-spam-zone.42/", "xenforo", "v1"),
    ("https://neosmart.net/forums/forums/easybcd-support.7/", "xenforo", "v2"),
    ("https://forum.anime-ultime.net/phpBB3/viewforum.php?f=48", "phpbb"),
    ("http://750mm.pl/index.php?board=26.0", "smf", "v1"),
    ("https://arizonagunowners.com/index.php/board,1.0.html", "smf", "v2"),
    ("https://www.sciencemadness.org/whisper/forumdisplay.php?fid=15", "xmb"),
    ("https://processwire.com/talk/forum/13-tutorials/", "invision"),
]

tested_boards = [
    ("https://kh-vids.net/forums/", "xenforo", "v1"),
    ("https://neosmart.net/forums/", "xenforo", "v2"),
    ("https://forum.anime-ultime.net/phpBB3/index.php", "phpbb"),
    ("http://750mm.pl/index.php", "smf", "v1"),
    ("https://arizonagunowners.com/index.php", "smf", "v2"),
    ("https://www.sciencemadness.org/whisper/", "xmb"),
    ("https://processwire.com/talk/", "invision"),
]


def get_getter(ex, fields):
    getter = getattr(ex, fields[1])
    if len(fields) > 2:
        getter = getattr(getter, fields[2])
    return getter


def test_urls(ex, print_func, func_name, identify, *args):
    for i in args:
        for j in i:
            getter = ex
            if not identify:
                getter = get_getter(ex, i)
            func = getattr(getter, func_name)
            r = func(j[0])
            if print_func is not None:
                print_func(r)


ex2 = forumscraper.Extractor(
    output=forumscraper.Outputs.write_by_id
    | forumscraper.Outputs.users
    | forumscraper.Outputs.threads,
    logger=sys.stdout,
    failed=sys.stderr,
    max_workers=8,
    thread_pages_max=1,
    pages_max=2,
    pages_forums_max=1,
    pages_threads_max=1,
)


def test_threads_identify():
    test_urls(ex, None, "get_thread", True, tested_threads)


def test_threads_scrapers():
    test_urls(ex, None, "get_thread", False, tested_threads)


def test_forums_scrapers():
    test_urls(ex2, None, "guess", False, tested_forums)


def test_forums_identify():
    test_urls(ex2, None, "guess", True, tested_forums)


def test_boards_scrapers():
    test_urls(ex2, None, "guess", False, tested_boards)


def test_boards_identify():
    test_urls(ex2, None, "guess", True, tested_boards)


def print_state_scraper(state):
    if state is None:
        return
    if isinstance(state, str):
        print(state)
    else:
        print(state["scraper"])


ex3 = forumscraper.Extractor(logger=sys.stderr, failed=sys.stderr)


def test_identify():
    test_urls(
        ex3,
        print_state_scraper,
        "identify",
        True,
        tested_boards,
        tested_forums,
        tested_threads,
    )


def test_findroot():
    test_urls(
        ex3,
        print_state_scraper,
        "findroot",
        True,
        tested_boards,
        tested_forums,
        tested_threads,
    )


def test_ignoring_hashed_before_identify():
    ex.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/",
        output=forumscraper.Outputs.write_by_hash,
    )  # xenforo1
    ex.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/",
        output=forumscraper.Outputs.write_by_hash,
    )  # xenforo1


xmb_forums_list = [
    "https://locostbuilders.co.uk/forum/2/",
    "https://div-arena.co.uk/forum2/forumdisplay.php?fid=3",
    "https://forum.postcrossing.com/forumdisplay.php?fid=180",
    "https://forum.solbu.net/forumdisplay.php?fid=74",
    "https://forums.bajanomad.com/forumdisplay.php?fid=38",
    "https://forums.xmbforum2.com/forumdisplay.php?fid=29",
    "https://www.sciencemadness.org/whisper/forumdisplay.php?fid=10",
    "http://www.club-k.co.nz/Forums/forumdisplay.php?fid=111",
    "https://forum.wendishresearch.org/forumdisplay.php?fid=413",
    "https://www.slotracinglemans.com/newforum/forumdisplay.php?fid=21",
    "https://forum.kapital3.org/forumdisplay.php?fid=25",
    # "https://www.alfapower.nu/forumdisplay.php?fid=6",
]

xmb_boards_list = [
    "https://locostbuilders.co.uk/forum/",
    "https://div-arena.co.uk/forum2/",
    "https://forum.postcrossing.com/",
    "https://forum.solbu.net/",
    "https://forums.bajanomad.com/",
    "https://forums.xmbforum2.com/",
    "https://www.sciencemadness.org/whisper/",
    "https://akeet.com",
    "http://www.club-k.co.nz/Forums/",
    "https://computernostalgiaheaven.co.uk/",
    "https://forum.kapital3.org/",
    "https://forum.wendishresearch.org/",
    "https://www.slotracinglemans.com/newforum/",
    # "https://www.alfapower.nu/forum.php",
]

smf1_boards_list = [
    "http://750mm.pl/index.php",
    "http://www.saberforum.com/index.php",
    # "https://3inchforum.nl/index.php",
    "https://bitcointalk.org/index.php",
    "https://councilofexmuslims.com/index.php?action=forum",
    "https://forum.ipfon.pl/index.php",
    "https://forum.jac.or.id/index.php",
    "https://forum.uqm.stack.nl/index.php",
    "https://forums.zeldaspeedruns.com/index.php",
    "https://forumszkolne.pl/index.php",
    "https://wiird.gamehacking.org/forum/index.php",
]

smf1_forums_list = [
    "http://750mm.pl/index.php?board=11.0",
    "http://www.saberforum.com/index.php?board=18.0",
    # https://3inchforum.nl/index.php?board=88.0
    "https://bitcointalk.org/index.php?board=5.0",
    "https://councilofexmuslims.com/index.php?board=8.0",
    "https://forum.ipfon.pl/index.php?board=1.0",
    "https://forum.jac.or.id/index.php?board=9.0",
    "https://forum.uqm.stack.nl/index.php?board=2.0",
    "https://forums.zeldaspeedruns.com/index.php?board=2.0",
    "https://forumszkolne.pl/szkola-ogolnie-b13.0/",
    "https://wiird.gamehacking.org/forum/index.php?board=4.0",
]

smf2_boards_list = [
    "https://forums.soldat.pl/index.php?action=forum",
    "https://www.chemicalforums.com/index.php",
    "https://www.nukeworker.com/forum/index.php",
    "https://forum.nasm.us/",
    "https://forum.coppermine-gallery.net/",
    "https://www.norotors.com/index.php",
    "https://forums.camerabits.com/",
    "https://czfirearms.us",
    "https://www.theflatearthsociety.org/forum/index.php",
    "https://www.tropicalfishforums.co.uk/index.php?action=forum",
    "https://forum.kuntsevo.com/",
    "https://naijacrux.com/index.php",
    "https://arizonagunowners.com/",
    # "http://bagnasadobre.org.pl/",
    "http://forum.33cats.ru/",
    "https://www.simplemachines.org/community/index.php",
    "https://forums.cadillaclasalle.club/",
    "https://tardisbuilders.com/",
    "https://forums.cyotek.com/",
    "https://tigerpedia.tigertms.com/",
    "https://forums.2000ad.com/",
    "https://aleforum.pl/",
]

smf2_forums_list = [
    "https://forums.soldat.pl/index.php?board=4.0",
    "https://www.chemicalforums.com/index.php?board=3.0",
    "https://www.nukeworker.com/forum/index.php/board,138.0.html",
    "https://forum.nasm.us/index.php?board=2.0",
    "https://forum.coppermine-gallery.net/index.php/board,90.0.html",
    "https://www.norotors.com/index.php?board=8.0",
    "https://forums.camerabits.com/index.php?board=4.0",
    "https://czfirearms.us/index.php?board=28.0",
    "https://www.theflatearthsociety.org/forum/index.php?board=18.0",
    "https://www.tropicalfishforums.co.uk/index.php/board,62.0.html",
    "https://forum.kuntsevo.com/index.php?board=1.0",
    "https://naijacrux.com/index.php?board=5.0",
    "https://arizonagunowners.com/index.php/board,2.0.html",
    # "http://bagnasadobre.org.pl/index.php?board=13.0",
    "http://forum.33cats.ru/index.php?board=3.0",
    "https://www.simplemachines.org/community/index.php?board=254.0",
    "https://forums.cadillaclasalle.club/index.php?board=10.0",
    "https://tardisbuilders.com/index.php?board=20.0",
    "https://forums.cyotek.com/cyotek-palette-editor/",
    "https://tigerpedia.tigertms.com/index.php?board=4.0",
    "https://forums.2000ad.com/index.php?board=3.0",
    "https://aleforum.pl/index.php?board=4.0",
]

phpbb_forums_list = [
    "http://askcodeman.com/viewforum.php?f=19",
    "https://forum.anime-ultime.net/phpBB3/viewforum.php?f=48",
    "https://forum.asustor.com/viewforum.php?f=33",
    "https://forum.avmania.zive.cz/forum-1713/Dalsi-zarizeni-a-komponenty.html",
    "https://forum.mobilmania.zive.cz/forum-10/Dalsi-znacky-mobilnich-telefonu.html",
    "https://forum.motec.com.au/viewforum.php?f=11",
    "https://fungi.pl/forum/viewforum.php?f=34",
    "https://garaz.autorevue.cz/forum-818/O-Garazi-a-AutoRevue-cz.html",
    "https://stilldcf.com/forums/viewforum.php?f=3",
    "https://www.ao-universe.com/forum/viewforum.php?f=25",
    "https://www.eldemore.com/viewforum.php?f=25",
    "https://www.eurobabeforum.com/viewforum.php?f=48",
    "https://www.phpbb.pl/viewforum.php?f=156",
    "https://forum.asustor.com/viewforum.php?f=42",
]

phpbb_boards_list = [
    "http://askcodeman.com/index.php",
    "http://forum.anime-ultime.net/phpBB3/index.php",
    "https://forum.asustor.com/index.php",
    "https://forum.avmania.zive.cz/index.php",
    "https://forum.mobilmania.zive.cz/index.php",
    "https://forum.motec.com.au/index.php",
    "https://fungi.pl/forum/index.php",
    "https://garaz.autorevue.cz/index.php",
    "https://stilldcf.com/forums/index.php",
    "https://www.ao-universe.com/forum/index.php",
    "https://www.eldemore.com/index.php",
    "https://www.eurobabeforum.com/index.php",
    "http://www.phpbb.pl/index.php",
]

xenforo1_boards_list = [
    "https://bmwfaq.org/",
    "https://boards.theforce.net/",
    "https://bukkit.org/forums/",
    "https://fanficslandia.com/",
    "https://forum.xnxx.com/",
    "https://forums.digitalpoint.com/",
    "https://forums.stevehoffman.tv/",
    "https://kh-vids.net/forums/",
    "https://www.bigsoccer.com/forums/",
    "https://www.hipforums.com/forum/",
    "https://www.jalopyjournal.com/forum/",
    "https://www.nucastle.co.uk/",
    "https://www.the-mainboard.com/index.php",
    "https://www.tigerfan.com/",
    "https://www.forumhouse.ru/forums",
    "https://xxx-files.org/",
    "https://audiosex.pro/",
    "https://damskiiclub.ru/",
]

xenforo1_forums_list = [
    "https://bmwfaq.org/forums/moteros-bmw-faq-club.74/",
    "https://boards.theforce.net/forums/rules-announcements.10719/",
    "https://bukkit.org/forums/plugin-development.5/",
    "https://fanficslandia.com/foro/actividades-y-concursos.19/",
    "https://forum.xnxx.com/forums/sex-stories.6/",
    "https://forums.digitalpoint.com/forums/google.5/",
    "https://forums.stevehoffman.tv/forums/music-corner.2/",
    "https://kh-vids.net/forums/introductions-departures.23/",
    "https://www.bigsoccer.com/forums/concacaf.23/",
    "https://www.hipforums.com/forum/forum/38-politics/",
    "https://www.jalopyjournal.com/forum/forums/classifieds.45/",
    "https://www.nucastle.co.uk/forums/music.7/",
    "https://www.the-mainboard.com/index.php?forums/the-mainboard.4/",
    "https://www.tigerfan.com/forums/lsu-recruiting.6/",
    "https://www.forumhouse.ru/forums/25/",
    "https://xxx-files.org/forums/pissing-and-squirting.33/",
    "https://audiosex.pro/forums/dj.68/",
    "https://damskiiclub.ru/forums/mir-zhenschiny.154/",
]

xenforo2_boards_list = [
    "https://www.mothering.com/forums/",
    "https://xenforo.com/community/",
    "https://www.veganforum.org/",
    # "https://www.ignboards.com/",
    "https://www.bigcricket.com/community/",
    "https://www.bigfooty.com/forum/",
    "https://www.blackhatworld.com/forums/",
    "https://www.kia-forums.com/forums/",
    "https://www.lexusrxowners.com/forums/",
    "https://www.mazda6club.com/forums/",
    "https://www.reptileforums.co.uk/forums/",
    "https://www.se7ensins.com/forums/",
    "https://rune-server.org/forums/",
    "https://www.woodworkingtalk.com/forums/",
    "https://www.shotgunworld.com/forums/",
    "https://www.watchuseek.com/forums/",
    "https://www.wranglerforum.com/forums/",
    "https://www.diychatroom.com/forums/",
    "https://www.dogforums.com/forums/",
    "https://longhaircareforums.com/forums/",
    "https://kenhsinhvien.vn",
    "https://forums.mangadex.org/",
]

xenforo2_forums_list = [
    "https://www.mothering.com/forums/fertility.68/",
    "https://xenforo.com/community/forums/xenforo-suggestions.18/",
    "https://www.veganforum.org/forums/vegan-by-location.105/",
    # "https://www.ignboards.com/forums/movies.8275/",
    "https://www.bigcricket.com/community/forums/club-chat.15/",
    "https://www.bigfooty.com/forum/forums/drafts-trading-free-agency.61/",
    "https://www.blackhatworld.com/forums/forum-suggestions-feedback.26/",
    "https://www.kia-forums.com/forums/amanti-opirus-forum-post-in-sub-section-only.221/",
    "https://www.lexusrxowners.com/forums/new-member-introductions.7/",
    "https://www.mazda6club.com/forums/mazda6-atenza.160/",
    "https://www.reptileforums.co.uk/forums/spiders-and-inverts.26/",
    "https://www.se7ensins.com/forums/forums/programming-scripting.62/",
    "https://rune-server.org/forums/forum-support-center.227/",
    "https://www.woodworkingtalk.com/forums/general-woodworking-discussions.2/",
    "https://www.shotgunworld.com/forums/the-fringe.52/",
    "https://www.watchuseek.com/forums/watch-fairs-and-events.919/",
    "https://www.wranglerforum.com/forums/general-jeep-discussion.19/",
    "https://www.diychatroom.com/forums/cook-it-yourself.195/",
    "https://www.dogforums.com/forums/general-dog-forum.2/",
    "https://longhaircareforums.com/forums/hair-care-tips-product-review-discussion.6/",
    "https://kenhsinhvien.vn/f/phong-truyen.213/",
    "https://forums.mangadex.org/forums/scanlator-discussions.63/",
    "https://rune-server.org/forums/defects.751/",
    "https://kenhsinhvien.vn/f/truyen-dai.301/",
]

invision_forums_list = [
    "https://invisioncommunity.com/forums/forum/497-technical-problems/",
    "https://linustechtips.com/forum/13-tech-news/",
    "https://aslain.com/index.php?/forum/1-multilingual-section/",
    "https://aslain.com/index.php?/forum/11-issues-bug-reporting/",
    "https://forums.cgarchitect.com/forum/9-general-discussions/",
    "https://forum.davidicke.com/index.php?/forum/32-general-chat/",
    "https://forum.fishingplanet.com/index.php?/forum/52-general-discussion-of-fishing-planet/",
    "https://forum.frogcommunity.com/index.php?/forum/7-general-chat/",
    "https://forum.htc.com/forum/23-vive-community-forums/",
    "https://forum.htc.com/forum/28-general-vive-discussion/",
    "https://forum.invisionize.pl/forum/3-informacje-i-og%C5%82oszenia/",
    "https://www.ipsfocus.com/forums/forum/9-news/",
    "https://community.ironcad.com/index.php?/forum/12-general-discussion/",
    "https://community.jaggedalliance.com/forums/forum/7-general-discussion/",
    "https://processwire.com/talk/forum/4-modulesplugins/",
    "https://www.seeq.org/forum/25-seeq-developer-club/",
    "https://www.thehuntinglife.com/forums/forum/72-living-off-the-land-amp-game-cooking/",
    "https://invisioncommunity.com/forums/forum/528-invision-community-insider/",
]

invision_boards_list = [
    "https://invisioncommunity.com/forums/",
    "https://linustechtips.com/",
    "https://aslain.com/",
    "https://forums.cgarchitect.com/",
    "https://forum.davidicke.com/",
    "https://forum.fishingplanet.com/",
    "https://forum.frogcommunity.com/",
    "https://forum.htc.com/",
    "https://forum.invisionize.pl/",
    "https://www.ipsfocus.com/forums/",
    "https://community.ironcad.com/",
    "https://community.jaggedalliance.com/",
    "https://processwire.com/talk/",
    "https://www.seeq.org/",
    "https://www.thehuntinglife.com/forums/",
]

ex4 = forumscraper.Extractor(
    output=forumscraper.Outputs.write_by_id
    | forumscraper.Outputs.forums
    | forumscraper.Outputs.tags
    | forumscraper.Outputs.boards,
    thread_pages_max=1,
    pages_max=1,
    pages_forums_max=1,
    pages_threads_max=1,
    logger=sys.stderr,
    failed=sys.stderr,
)


def test_xmb_page_forums():
    for i in xmb_forums_list:
        ex4.xmb.get_forum(i)


def test_xmb_page_boards():
    for i in xmb_boards_list:
        ex4.xmb.get_board(i)


def test_smf1_page_forums():
    for i in smf1_forums_list:
        ex4.smf.v1.get_forum(i)


def test_smf1_page_boards():
    for i in smf1_boards_list:
        ex4.smf.v1.get_board(i)


def test_smf2_page_forums():
    for i in smf2_forums_list:
        ex4.smf.v2.get_forum(i)


def test_smf2_page_boards():
    for i in smf2_boards_list:
        ex4.smf.v2.get_board(i)


def test_phpbb_page_forums():
    for i in phpbb_forums_list:
        ex4.phpbb.get_forum(i)


def test_phpbb_page_boards():
    for i in phpbb_boards_list:
        ex4.phpbb.get_board(i)


def test_xenforo1_page_forums():
    for i in xenforo1_forums_list:
        ex4.xenforo.v1.get_forum(i)


def test_xenforo1_page_boards():
    for i in xenforo1_boards_list:
        ex4.xenforo.v1.get_board(i)


def test_xenforo2_page_forums():
    for i in xenforo2_forums_list:
        ex4.xenforo.v2.get_forum(i)


def test_xenforo2_page_boards():
    for i in xenforo2_boards_list:
        ex4.xenforo.v2.get_board(i)


def test_invision_page_forums():
    for i in invision_forums_list:
        ex4.invision.get_forum(i)


def test_invision_page_boards():
    for i in invision_boards_list:
        ex4.invision.get_board(i)


# state = ex.get_thread(
# "https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/"
# )  # xenforo2
# print(state["visited"])

# test_threads_identify()
# test_threads_scrapers()
# test_forums_identify()
# test_forums_scrapers()
# test_boards_identify()
# test_boards_scrapers()
# test_ignoring_hashed_before_identify()

# test_xmb_page_forums()
# test_xmb_page_boards()
# test_smf1_page_forums()
# test_smf1_page_boards()
# test_smf2_page_forums()
# test_smf2_page_boards()
# test_phpbb_page_forums()
# test_phpbb_page_boards()
# test_xenforo1_page_forums()
# test_xenforo1_page_boards()
# test_xenforo2_page_forums()
# test_xenforo2_page_boards()
# test_invision_page_forums()
# test_invision_page_boards()

# test_identify()
# test_findroot()

# https://www.hornetowners.com/threads/dead-battery.523/ #would need to add badge field and view more replies
# https://www.diychatroom.com/threads/diy-tip-of-the-day.204702/

# python -m forumscraper -d j --noreactions 'https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/'
# python -m forumscraper -d j --nousers --noreactions 'https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/'
# python -m forumscraper -d j --nothreads --nousers --noreactions 'https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/'
# python -m forumscraper --only-urls-forums  'https://kh-vids.net/forums/discussion.25/'
# python -m forumscraper --only-urls-threads -o kk 'https://kh-vids.net/forums/help-with-life.101/'
# python -m forumscraper -d j --boards --forums --nothreads   'https://kh-vids.net/forums/help-with-life.101/'
