#!/usr/bin/env python
import sys
import os
import forumscraper


def trace(x1, x2, x3):
    pass


sys.settrace(trace)

os.chdir("j")

ex = forumscraper.Extractor(
    output=forumscraper.Outputs.write_by_id, logger=sys.stdout, failed=sys.stderr
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


def test_threads_identify():
    ex.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/"
    )  # xenforo1
    ex.get_thread(
        "https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/"
    )  # xenforo2
    ex.get_thread("http://750mm.pl/index.php?topic=4892.0")  # smf1
    ex.get_thread("https://arizonagunowners.com/index.php/topic,16.0.html")  # smf2
    ex.get_thread(
        "https://www.sciencemadness.org/whisper/viewthread.php?tid=158143"
    )  # xmb
    ex.get_thread(
        "https://forum.anime-ultime.net/phpBB3/viewtopic.php?f=98&t=16040"
    )  # phpbb
    ex.get_thread(
        "https://processwire.com/talk/topic/3553-handling-categories-on-a-product-catalogue/"
    )  # invision


def test_threads_scrapers():
    ex.xenforo.v1.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/"
    )  # xenforo1
    ex.xenforo.v2.get_thread(
        "https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/"
    )  # xenforo2
    ex.smf.v1.get_thread("http://750mm.pl/index.php?topic=4892.0")  # smf1
    ex.smf.v2.get_thread(
        "https://arizonagunowners.com/index.php/topic,16.0.html"
    )  # smf2
    ex.xmb.get_thread(
        "https://www.sciencemadness.org/whisper/viewthread.php?tid=158143"
    )  # xmb
    ex.phpbb.get_thread(
        "https://forum.anime-ultime.net/phpBB3/viewtopic.php?f=98&t=16040"
    )  # phpbb
    ex.invision.get_thread(
        "https://processwire.com/talk/topic/3553-handling-categories-on-a-product-catalogue/"
    )  # invision


ex2 = forumscraper.Extractor(
    output=forumscraper.Outputs.write_by_id,
    logger=sys.stdout,
    failed=sys.stderr,
    max_workers=8,
    thread_pages_max=1,
    pages_max=2,
    pages_forums_max=1,
    pages_threads_max=1,
)


def test_forums_scrapers():
    ex2.xenforo.guess("https://kh-vids.net/forums/the-spam-zone.42/")  # xenforo1
    ex2.xenforo.guess("https://neosmart.net/forums/")  # xenforo2
    ex2.phpbb.guess("https://forum.anime-ultime.net/phpBB3/index.php")  # phpbb
    ex2.smf.guess("http://750mm.pl/index.php")  # smf1
    ex2.smf.guess("https://arizonagunowners.com/index.php")  # smf2
    ex2.xmb.guess("https://www.sciencemadness.org/whisper/")  # xmb
    ex2.invision.guess("https://processwire.com/talk/")  # ex2


def test_forums_identify():
    ex2.guess("https://kh-vids.net/forums/the-spam-zone.42/")  # xenforo1
    ex2.guess("https://neosmart.net/forums/")  # xenforo2
    ex2.guess("https://forum.anime-ultime.net/phpBB3/index.php")  # phpbb
    ex2.guess("http://750mm.pl/index.php")  # smf1
    ex2.guess("https://arizonagunowners.com/index.php")  # smf2
    ex2.guess("https://www.sciencemadness.org/whisper/")  # xmb
    ex2.guess("https://processwire.com/talk/")  # invision


# http://www.sciencemadness.org/talk/viewthread.php?tid=6064
# https://www.forumhouse.ru/threads/409354/
# https://xenforo.com/community/threads/can-not-search-chinese.2049/
# http://750mm.pl/index.php?topic=5559.0
# https://forum.anime-ultime.net/phpBB3/viewtopic.php?f=28&t=18253
# https://invisioncommunity.com/forums/topic/478369-invision-community-5-tagging-reinvented/
# https://invisioncommunity.com/forums/topic/476881-ic5-allow-use-of-fontawesome-kit/
# https://linustechtips.com/topic/1197477-policygenius-thoughts/

# ex.get_thread("https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/") #xenforo1
# ex.get_thread("https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/") #xenforo1

# state = ex.get_thread(
# "https://forum.modelarstwo.info/threads/sosnowiec-festiwal-kolej-w-miniaturze-viii-edycja-16-17-marca-2024-r.60974/"
# )  # xenforo2
# print(state["visited"])

# test_threads_identify()
# test_threads_scrapers()
# test_forums_identify()
# test_forums_scrapers
