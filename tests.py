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
    output=forumscraper.Outputs.write_by_id,
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

# test_identify()
# test_findroot()

# https://www.hornetowners.com/threads/dead-battery.523/ #would need to add badge field and view more replies
# https://www.diychatroom.com/threads/diy-tip-of-the-day.204702/
