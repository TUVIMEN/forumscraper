#!/usr/bin/env python

import difflib
from cdifflib import CSequenceMatcher

difflib.SequenceMatcher = CSequenceMatcher

import sys
import os
import itertools
import hashlib
import json
import vcr
import forumscraper


def strtosha256(string):
    if isinstance(string, str):
        string = string.encode()

    return hashlib.sha256(string).hexdigest()


def fdiff(l1, l2):
    for i in itertools.batched(zip(l1, l2), 20000):
        n1 = []
        n2 = []
        for i1, i2 in i:
            n1.append(i1)
            n2.append(i2)

        yield from difflib.unified_diff(n1, n2)


tested_urls = {
    "get_forum": {
        "xmb": [
            "https://locostbuilders.co.uk/forum/2/",
            "https://div-arena.co.uk/forum2/forumdisplay.php?fid=3",
            "https://forum.postcrossing.com/forumdisplay.php?fid=180",
            # "https://forum.solbu.net/forumdisplay.php?fid=74",
            "https://forums.bajanomad.com/forumdisplay.php?fid=38",
            "https://forums.xmbforum2.com/forumdisplay.php?fid=29",
            "https://www.sciencemadness.org/whisper/forumdisplay.php?fid=10",
            "http://www.club-k.co.nz/Forums/forumdisplay.php?fid=111",
            "https://forum.wendishresearch.org/forumdisplay.php?fid=413",
            "https://www.slotracinglemans.com/newforum/forumdisplay.php?fid=21",
            "https://forum.kapital3.org/forumdisplay.php?fid=25",
            # "https://www.alfapower.nu/forumdisplay.php?fid=6", https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
        ],
        "xenforo.v1": [
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
        ],
        "xenforo.v2": [
            "https://www.mothering.com/forums/fertility.68/",
            "https://xenforo.com/community/forums/xenforo-suggestions.18/",
            "https://www.veganforum.org/forums/vegan-by-location.105/",
            "https://www.ignboards.com/forums/movies.8275/",
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
            "https://longhaircareforums.com/forums/hair-care-tips-product-reviews.6/",
            "https://kenhsinhvien.vn/f/phong-truyen.213/",
            "https://forums.mangadex.org/forums/scanlator-discussions.63/",
            "https://rune-server.org/forums/defects.751/",
            "https://kenhsinhvien.vn/f/truyen-dai.301/",
        ],
        "smf.v1": [
            "http://750mm.pl/index.php?board=11.0",
            "http://www.saberforum.com/index.php?board=18.0",
            "https://3inchforum.nl/index.php?board=88.0",
            "https://bitcointalk.org/index.php?board=5.0",
            "https://councilofexmuslims.com/index.php?board=8.0",
            # "https://forum.ipfon.pl/index.php?board=1.0",
            # "https://forum.jac.or.id/index.php?board=9.0",
            "https://forum.uqm.stack.nl/index.php?board=2.0",
            "https://forums.zeldaspeedruns.com/index.php?board=2.0",
            "https://forumszkolne.pl/szkola-ogolnie-b13.0/",
            "https://wiird.gamehacking.org/forum/index.php?board=4.0",
        ],
        "smf.v2": [
            "https://forums.soldat.pl/index.php?board=4.0",
            "https://www.chemicalforums.com/index.php?board=3.0",
            "https://www.nukeworker.com/forum/index.php/board,138.0.html",
            "https://forum.nasm.us/index.php?board=2.0",
            "https://coppermine-gallery.com/forum/index.php/board,90.0.html",
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
        ],
        "phpbb": [
            "http://askcodeman.com/viewforum.php?f=19",
            "https://forum.anime-ultime.net/phpBB3/viewforum.php?f=48",
            "https://forum.asustor.com/viewforum.php?f=33",
            "https://forum.avmania.zive.cz/forum-1713/dalsi-zarizeni-a-komponenty.html",
            "https://forum.mobilmania.zive.cz/forum-10/dalsi-znacky-mobilnich-telefonu.html",
            "https://forum.motec.com.au/viewforum.php?f=11",
            "https://fungi.pl/forum/viewforum.php?f=34",
            "https://garaz.autorevue.cz/forum-818/o-garazi-a-autorevue-cz.html",
            "https://stilldcf.com/forums/viewforum.php?f=3",
            "https://www.ao-universe.com/forum/viewforum.php?f=25",
            "https://www.eldemore.com/viewforum.php?f=25",
            "https://www.eurobabeforum.com/viewforum.php?f=48",
            "https://www.phpbb.pl/viewforum.php?f=156",
            "https://forum.asustor.com/viewforum.php?f=42",
        ],
        "invision": [
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
        ],
        "stackexchange": [
            "https://stackoverflow.com/questions?tab=votes&pagesize=50",
            "https://skeptics.stackexchange.com/questions",
            "https://stackoverflow.com/questions?tab=Bounties",
            "https://serverfault.com/questions?tab=Votes",
        ],
        "hackernews": [
            "https://news.ycombinator.com/show",
            "https://news.ycombinator.com/news",
            "https://news.ycombinator.com/front",
            "https://news.ycombinator.com/ask",
            "https://news.ycombinator.com/jobs",
            "https://news.ycombinator.com/newest",
        ],
        "vbulletin": [
            "https://www.ifans.pl/forumdisplay.php?118-Instrukcje",
            "https://www.airlinepilotforums.com/regional/",
            "https://forum.vbulletin.com/forum/vbulletin-5-connect/support-issues-questions",
            "https://spalumi.com/f21/",
            "https://spalumi.com/f285/",
            "https://volvoforums.org.uk/forumdisplay.php?s=58951fe509a56d94db9b0bb18431032b&f=9",
            "https://www.tenforums.com/windows-10-news/?s=336edc8a87c59dbe8c51bd2ebe2b13d1",
            "https://www.thctalk.com/cannabis-forum/forumdisplay.php?13-Novice-Section&s=678033746e67a7d44eaa65798eed96ae",
            "https://www.satsupreme.com/forumdisplay.php/150-Conditional-Access-Modules-%28CAM%29?s=a99397c6de8c85f383e6976ec655ad4f",
            "https://www.utzone.de/forum/forumdisplay.php?s=783010ffd9ddaa24cdeb01227a70a42f&f=51",
            "https://forum.thesettlersonline.pl/forums/177-Nowo%C5%9Bci-i-og%C5%82oszenia?s=c9c8f91e1585695d0bca8dcc816b5d7b",
            "https://mafia-game.ru/forum/forumdisplay.php?f=9",
            "http://www.mfarmer.ru/forumdisplay.php?f=14",
            "https://mdforum.su/forumdisplay.php?s=6544c986a9392e47b4fa18c655eaf10f&f=318",
            "https://www.hip-hop.ru/forum/russkiy-rap-f13",
            "https://www.mazdaforum.com/forum/mazda-cx-5-54/",
            "https://www.audiworld.com/forums/events-discussion-14/",
            "https://www.audizine.com/forum/forumdisplay.php/3-B5-S4-RS4",
            "https://www.ausjeepoffroad.com/forum/forum/market-place/4~sale",
            "https://doska.mogilev.by/forumdisplay.php?f=27",
            "https://forum.driver.ru/forum/%D0%BF%D0%BE%D0%B8%D1%81%D0%BA-%D0%B4%D1%80%D0%B0%D0%B9%D0%B2%D0%B5%D1%80%D0%BE%D0%B2/%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B8-%D0%B8-%D0%BF%D0%BB%D0%B0%D0%BD%D1%88%D0%B5%D1%82%D0%BD%D1%8B%D0%B5-%D0%BF%D0%BA",
            "https://7er.pl/forumdisplay.php/12-Seria-e38?s=9dfddc2ba0424ef453f10d31af632f81",
            "https://www.excelforum.com/word-formatting-and-general/",
            "https://forums.cnetfrance.fr/desinfection-pc-virus-malwares-et-logiciels-indesirables",
            "https://forums.edelbrock.com/forum/edelbrock-electronics-and-efi/legacy-efi-systems",
            "https://forums.edelbrock.com/forum/pro-flo-efi/pro-flo-xt",
            "https://doska.mogilev.by/forumdisplay.php?f=85",
        ],
    },
    "get_board": {
        "xmb": [
            "https://locostbuilders.co.uk/forum/",
            "https://div-arena.co.uk/forum2/index.php",
            "https://forum.postcrossing.com/",
            # "https://forum.solbu.net/",
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
        ],
        "xenforo.v1": [
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
        ],
        "xenforo.v2": [
            "https://www.mothering.com/forums/",
            "https://xenforo.com/community/",
            "https://www.veganforum.org/",
            "https://www.ignboards.com/",
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
            "https://longhaircareforums.com/",
            "https://kenhsinhvien.vn",
            "https://forums.mangadex.org/",
        ],
        "smf.v1": [
            "http://750mm.pl/index.php",
            "http://www.saberforum.com/index.php",
            "https://3inchforum.nl/index.php",
            "https://bitcointalk.org/index.php",
            "https://councilofexmuslims.com/index.php?action=forum",
            # "https://forum.ipfon.pl/index.php",
            # "https://forum.jac.or.id/index.php",
            "https://forum.uqm.stack.nl/index.php",
            "https://forums.zeldaspeedruns.com/index.php",
            "https://forumszkolne.pl/index.php",
            "https://wiird.gamehacking.org/forum/index.php",
        ],
        "smf.v2": [
            "https://forums.soldat.pl/index.php?action=forum",
            "https://www.chemicalforums.com/index.php",
            "https://www.nukeworker.com/forum/index.php",
            "https://forum.nasm.us/",
            "https://coppermine-gallery.com/forum/",
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
        ],
        "phpbb": [
            "http://askcodeman.com/index.php",
            "https://forum.anime-ultime.net/phpBB3/index.php",
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
        ],
        "invision": [
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
            "https://community.jaggedalliance.com/forums/",
            "https://processwire.com/talk/",
            "https://www.seeq.org/",
            "https://www.thehuntinglife.com/forums/",
        ],
        "stackexchange": [],
        "hackernews": [],
        "vbulletin": [
            "https://www.ifans.pl/forum.php?s=316321fab6629169595c1f4858884d2e",
            "https://www.airlinepilotforums.com/",
            "https://forum.vbulletin.com/",
            "https://spalumi.com/",
            "https://volvoforums.org.uk/",
            "https://www.tenforums.com/",
            "https://www.thctalk.com/cannabis-forum/index.php",
            "https://www.satsupreme.com/",
            "https://www.utzone.de/forum/",
            "https://forum.thesettlersonline.pl/forum.php",
            "https://mafia-game.ru/forum/",
            "http://www.mfarmer.ru/forum.php?s=4284911f2cd9b47667097ba78ea4b7f9",
            "https://mdforum.su/",
            "https://www.hip-hop.ru/forum/",
            "https://www.mazdaforum.com/forum/",
            "https://www.audiworld.com/forums/",
            "https://www.audizine.com/forum/",
            "https://www.ausjeepoffroad.com/forum/index.php",
            "https://doska.mogilev.by/",
            "https://forum.driver.ru/",
            "https://7er.pl/",
            "https://excelforum.com/",
            "https://forums.cnetfrance.fr/",
            "https://forums.edelbrock.com/",
        ],
    },
    "get_thread": {
        "xmb": [
            "https://www.akeet.com/viewthread.php?tid=441",
            # "https://www.alfapower.nu/viewthread.php?tid=31524",
            "https://www.club-k.co.nz/Forums/viewthread.php?tid=19038",
            "https://computernostalgiaheaven.co.uk/viewthread.php?tid=194",
            "https://div-arena.co.uk/forum2/viewthread.php?tid=169",
            "https://forum.kapital3.org/viewthread.php?tid=14",
            "https://forum.wendishresearch.org/viewthread.php?tid=4255",
            "https://locostbuilders.co.uk/forum/66/viewthread.php?tid=220286",
            "https://www.slotracinglemans.com/newforum/viewthread.php?tid=527",
            "https://www.sciencemadness.org/whisper/viewthread.php?tid=66122",
        ],
        "xenforo.v1": [
            "https://bmwfaq.org/threads/porra-mundial-motogp-2024.1053401/",
            "https://boards.theforce.net/threads/does-fun-games-really-need-to-be-separate-from-community.50060724/",
            "https://bukkit.org/threads/read-me-first-how-to-make-a-plugin-development-thread.395844/",
            "https://fanficslandia.com/tema/caf%C3%A9-creativo.60748/",
            "https://forum.xnxx.com/threads/i-discover-my-brother%E2%80%99s-girlfriend-also-likes-pussy.703374/",
            "https://forums.digitalpoint.com/threads/many-backlinks-from-the-same-site.2877987/",
            "https://forums.stevehoffman.tv/threads/hit-songs-from-the-seventies-and-eighties-that-had-some-pretty-cool-guitar-playing.1215885/",
            "https://kh-vids.net/threads/who-do-you-think-did-the-worst-voice-acting.5571/",
            "https://www.bigsoccer.com/threads/ideal-schedule-for-2030-cycle.2103402/",
            "https://www.hipforums.com/forum/threads/to-the-people-of-the-world.522013/",
            "https://www.jalopyjournal.com/forum/threads/set-of-ford-flathead-mushroom-exhaust-valves-new.930478/",
            "https://www.nucastle.co.uk/threads/electric.24808/",
            "https://www.the-mainboard.com/index.php?threads/california-tsunami.185780/",
            "https://www.tigerfan.com/threads/official-2024-recruiting-thread.256390/",
            "https://www.forumhouse.ru/threads/580163/",
            "https://xxx-files.org/threads/pisschicks-pissing-teens-russian-piss-peeing.148597/",
            "https://audiosex.pro/threads/which-dj-software-can-you-recommend.40064/",
            "https://damskiiclub.ru/threads/vegetarianskaja-eda.537/",
        ],
        "xenforo.v2": [
            "https://www.zoovilleforum.net/threads/how-was-your-first-time-with-a-female-dog.43275/",
            "https://www.mothering.com/threads/the-one-thread-june-24-30.699413/",
            "https://xenforo.com/community/threads/better-functionality-to-report-and-moderate-illegal-hate-speech.127828/",
            "https://www.veganforum.org/threads/vegan-friendly-towns.12901/",
            "https://www.ignboards.com/threads/donkey-kong-country-returns-hd.456969676/",
            "https://www.bigcricket.com/community/threads/footscray-cricket-association.3106/",
            "https://www.bigfooty.com/forum/threads/future-picks-2025-provisional-afl-draft-order-based-on-2024-h-a-ladder.1388116/",
            "https://www.blackhatworld.com/seo/not-tryna-be-the-karen-here-but-i-think-1000-messages-should-be-the-requirement-for-jr-vip.1667744/",
            "https://www.kia-forums.com/threads/amanti-acceleration-problems.31557/",
            "https://www.lexusrxowners.com/threads/the-official-welcome-thread.161/",
            "https://www.mazda6club.com/threads/car-crashed-into-a-fence.135733/",
            "https://www.reptileforums.co.uk/threads/id-of-british-spiders-and-bite-reports.861388/",
            "https://www.se7ensins.com/forums/threads/test-drive-unlimited-2-private-server.1700802/",
            "https://rune-server.org/threads/suggest-a-smiley.387012/",
            "https://www.woodworkingtalk.com/threads/what-tools-for-son-to-practise-alone-with.237630/",
            "https://www.shotgunworld.com/threads/other-hobbies.554361/",
            "https://www.watchuseek.com/threads/ball-forum-topper-fine-jewelers.343428/",
            "https://www.wranglerforum.com/threads/make-jeep-great-again.2476141/",
            "https://www.diychatroom.com/threads/new-toy-an-air-fryer.778538/",
            "https://www.dogforums.com/threads/summary-of-dna-tests-for-dogs.104035/",
            "https://longhaircareforums.com/threads/2024-sl-apl-challenge-support-thread.855363/",
            "https://kenhsinhvien.vn/t/anh-trai-em-gai-tao-dinh.3027/",
            "https://forums.mangadex.org/threads/scanlator-community-survey-all-scanlators-welcome.1069275/",
        ],
        "smf.v1": [
            "https://www.saberforum.com/index.php?topic=47627.0",
            "http://750mm.pl/index.php?topic=4849.0",
            "https://3inchforum.nl/index.php/topic,946.0.html",
            "https://bitcointalk.org/index.php?topic=5439960.0",
            "https://councilofexmuslims.com/index.php?topic=16018.0",
            "https://forum.uqm.stack.nl/index.php?PHPSESSID=de6d4fe9585b25a16b6622b952fb372f&topic=5772.0",
            "https://forums.zeldaspeedruns.com/index.php?PHPSESSID=c7c7435d22e314671a7479f8d1405440&topic=1565.0",
            "https://forumszkolne.pl/kuchnia-w-litere-l-t94671.0.html",
            "https://wiird.gamehacking.org/forum/index.php?topic=9891.0",
        ],
        "smf.v2": [
            "https://forums.soldat.pl/index.php?PHPSESSID=4ktu8vdkq0dk8sjop4reujlpp0&topic=44322.0",
            "https://www.chemicalforums.com/index.php?topic=3025.0",
            "https://www.nukeworker.com/forum/index.php/topic,45192.0.html",
            "https://forum.nasm.us/index.php?topic=2477.0",
            "https://coppermine-gallery.com/forum/index.php/topic,75957.0.html",
            "https://www.norotors.com/index.php?PHPSESSID=f238b7a65428e68a3dfb3816c6c9a586&topic=28603.0",
            "https://forums.camerabits.com/index.php?topic=16258.0",
            "https://czfirearms.us/index.php?PHPSESSID=65261a29e35b0184a953e3b5219320a8&topic=125449.0",
            "https://www.theflatearthsociety.org/forum/index.php?topic=56199.0",
            "https://www.tropicalfishforums.co.uk/index.php/topic,90841.0.html?PHPSESSID=520b51b5d6d0769207c23a7effab413a",
            "https://forum.kuntsevo.com/index.php?PHPSESSID=71fdadace36d60a100706840bf5f8a90&topic=9.0",
            "https://naijacrux.com/index.php?topic=9891.0",
            "https://arizonagunowners.com/index.php/topic,21986.0.html?PHPSESSID=0ddb7ee0cbc5bedb0194ded2939c4fb1",
            "http://forum.33cats.ru/index.php?PHPSESSID=c299323b70b9cc3d1dc3cbdeaebeac6d&topic=77.0",
            "https://www.simplemachines.org/community/index.php?topic=586863.0",
            "https://forums.cadillaclasalle.club/index.php?topic=154238.0",
            "https://tardisbuilders.com/index.php?topic=5478.0",
            "https://forums.cyotek.com/cyotek-palette-editor/colour-palettes-not-displaying-colours/",
            "https://tigerpedia.tigertms.com/index.php?PHPSESSID=fml221p8dnsdbhqm58t5rovas5&topic=224.0",
            "https://forums.2000ad.com/index.php?PHPSESSID=17821afd27d9c4229503d10a577aeb5e&topic=49772.0",
            "https://aleforum.pl/index.php?topic=65.0",
        ],
        "phpbb": [
            "https://forum.anime-ultime.net/phpBB3/viewtopic.php?f=28&t=18253",
            "https://garaz.autorevue.cz/viewtopic.php?f=810&t=810442",
            "https://forum.mobilmania.zive.cz/viewtopic.php?f=1&t=1308785",
            "https://forum.avmania.zive.cz/viewtopic.php?f=1703&t=1330095",
            "https://www.eurobabeforum.com/viewtopic.php?f=19&t=31917",
            "https://www.eldemore.com/viewtopic.php?f=6&t=12854",
            "http://askcodeman.com/viewtopic.php?f=14&t=184",
            "http://forum.akusherstvo.ru/viewtopic.php?f=40&t=21803",
            "https://forum.motec.com.au/viewtopic.php?f=67&t=5518&sid=1be7426359988de287dd9bbec393f0f3",
            "https://forum.ecc.kz/viewtopic.php?f=5&t=8596",
            "http://www.phpbb.pl/viewtopic.php?f=144&t=18044",
            "https://fungi.pl/forum/viewtopic.php?f=14&t=10057",
            "https://forum.asustor.com/viewtopic.php?t=13286",
            "https://stilldcf.com/forums/viewtopic.php?t=454",
            "https://www.ao-universe.com/forum/viewtopic.php?f=1&t=5521",
            "https://forum.aegean.gr/viewtopic.php?t=29623",
        ],
        "invision": [
            "https://invisioncommunity.com/forums/topic/477477-counters-not-working/",
            "https://linustechtips.com/topic/1593443-amd-rdna-4-gpus-will-allegedly-be-renamed/",
            "https://aslain.com/index.php?/topic/2997-editing-the-otm/",
            "https://forums.cgarchitect.com/topic/73597-outsourcing-disaster/",
            "https://forum.davidicke.com/index.php?/topic/37303-earthkeepers-summit-16th-to-the-20th-december/",
            "https://forum.fishingplanet.com/index.php?/topic/20779-pike-slasher/",
            "https://forum.frogcommunity.com/index.php?/topic/826-new-markbook-app/",
            "https://forum.htc.com/topic/2308-expected-shipping-times-black-friday/",
            "https://forum.invisionize.pl/topic/3556-zmiana-nick%C3%B3w-na-foruminvisionizepl/",
            "https://www.ipsfocus.com/forums/topic/7725-2015-and-ips-suite-4x/",
            "https://community.ironcad.com/index.php?/topic/8003-3d-smart-dimension-behavior/",
            "https://community.jaggedalliance.com/forums/topic/1687-ammunition/",
            "https://processwire.com/talk/topic/5040-events-fieldtype-inputfield-how-to-make-a-table-fieldtypeinputfield/",
            "https://www.seeq.org/topic/1483-creating-a-formula-parameters-string/",
            "https://www.thehuntinglife.com/forums/topic/24462-hanging/",
            "https://invisioncommunity.com/forums/topic/478170-invision-community-5-the-all-new-editor/",
        ],
        "stackexchange": [
            "https://serverfault.com/questions/9708/what-is-a-pem-file-and-how-does-it-differ-from-other-openssl-generated-key-file",
            "https://serverfault.com/questions/293217/our-security-auditor-is-an-idiot-how-do-i-give-him-the-information-he-wants",
            "https://serverfault.com/questions/180711/what-exactly-do-the-colors-in-htop-status-bars-mean",
            "https://stackoverflow.com/questions/8318911/why-does-html-think-chucknorris-is-a-color",
            "https://stackoverflow.com/questions/79275439/better-definition-of-the-reifying-memberd-t-3",
            "https://stackoverflow.com/questions/927358/how-do-i-undo-the-most-recent-local-commits-in-git",
            "https://skeptics.stackexchange.com/questions/6828/was-the-experiment-with-five-monkeys-a-ladder-a-banana-and-a-water-spray-condu",
            "https://skeptics.stackexchange.com/questions/3371/does-hot-water-freeze-faster-than-cold-water",
            "https://skeptics.stackexchange.com/questions/3060/do-cats-always-land-on-their-feet",
        ],
        "hackernews": [
            "https://news.ycombinator.com/item?id=41427563",
            "https://news.ycombinator.com/item?id=41425150",
            "https://news.ycombinator.com/item?id=41434637",
            "https://news.ycombinator.com/item?id=41425910",
            "https://news.ycombinator.com/item?id=42527265",
        ],
        "vbulletin": [
            "https://www.ifans.pl/showthread.php?8700-Umowa-gwarancyjna-Infiniti-QX-70-r-2016",
            "https://www.airlinepilotforums.com/regional/148412-when-will-regionals-hire-again.html",
            "https://forum.vbulletin.com/forum/vbulletin-5-connect/support-issues-questions/421946-starting-to-be-impressed-by-5-0",
            "https://spalumi.com/f285/fotos-falsas-en-valencia-133442.html",
            "https://volvoforums.org.uk/showthread.php?t=341051",
            "https://www.tenforums.com/windows-10-news/199082-known-resolved-issues-windows-10-version-22h2.html",
            "https://www.thctalk.com/cannabis-forum/showthread.php?190680-Is-my-plant-Male-or-Female-A-guide-with-images",
            "https://www.satsupreme.com/showthread.php/378762-Forever-IKS-Server-Hacked",
            "https://www.utzone.de/forum/showthread.php?t=1483",
            "https://forum.thesettlersonline.pl/threads/41348-Mi%C4%99dzynarodowa-tw%C3%B3rczo%C5%9Bc-graczy-Polska",
            "https://mafia-game.ru/forum/showthread.php?t=143",
            "http://www.mfarmer.ru/showthread.php?t=306",
            "https://mdforum.su/showthread.php?t=6581",
            "https://www.hip-hop.ru/forum/cd-sbornik-a-banditskii-rap-dlya-bratana-2a-81540/",
            "https://www.mazdaforum.com/forum/mazda-cx-5-54/no-individual-tire-pressure-display-49445/",
            "https://www.audiworld.com/forums/events-discussion-14/2007-northeast-audi-fall-mountain-trek-updated-info-9-17-07-a-2003067/",
            "https://www.audizine.com/forum/showthread.php/950653-Saving-a-Santorin-Avant",
            "https://www.ausjeepoffroad.com/forum/forum/jeep-garage/xj-mj-cherokee/10753-diesel-xj-parts-info",
            "https://doska.mogilev.by/showthread.php?t=160795",
            "https://forum.driver.ru/forum/%D0%BF%D0%BE%D0%B8%D1%81%D0%BA-%D0%B4%D1%80%D0%B0%D0%B9%D0%B2%D0%B5%D1%80%D0%BE%D0%B2/%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B8-%D0%B8-%D0%BF%D0%BB%D0%B0%D0%BD%D1%88%D0%B5%D1%82%D0%BD%D1%8B%D0%B5-%D0%BF%D0%BA/405-%D0%BD%D1%83%D0%B6%D0%BD%D1%8B-%D0%B4%D1%80%D0%BE%D0%B2%D0%B0-%D0%B4%D0%BB%D1%8F-asus-f50sl",
            "https://7er.pl/showthread.php/7759-hydraulika-klapy-baga%C5%BCnika-e38",
            "https://www.excelforum.com/excel-formulas-and-functions/401807-using-name-as-worksheet-reference.html",
            "https://forums.cnetfrance.fr/desinfection-pc-virus-malwares-et-logiciels-indesirables/6819218-pc-lent-malgre-antvirus-et-malwarbytes",
            "https://forums.edelbrock.com/forum/pro-flo-efi/pro-flo-xt/1127-innovate-lc-1-setup-and-idle-pid-tuning",
            "https://forums.edelbrock.com/forum/pro-flo-efi/pro-flo-4/50321-pf-4-o2-sensor-testing-video",
            "https://forum.vbulletin.com/forum/vbulletin-6/support-questions/4495811-sigpic-tools",
        ],
    },
    "get_user": {
        "xmb": [],
        "xenforo.v1": [],
        "xenforo.v2": [],
        "smf.v1": [],
        "smf.v2": [],
        "phpbb": [],
        "invision": [],
        "stackexchange": [
            "https://stackoverflow.com/users/17311253/djimenez",
            "https://stackoverflow.com/users/1031591/atlaste",
            "https://skeptics.stackexchange.com/users/41283/keshav-srinivasan",
            "https://skeptics.stackexchange.com/users/35049/spraff",
            "https://skeptics.stackexchange.com/users/56721/pinegulf",
            "https://stackoverflow.com/users/1718632/delphirules",
            "https://stackoverflow.com/users/1608796/apple",
            "https://serverfault.com/users/46527/eonil",
            "https://serverfault.com/users/2882/noah-goodrich",
            "https://serverfault.com/users/77159/kernel",
        ],
        "hackernews": [
            "https://news.ycombinator.com/user?id=vdfs",
            "https://news.ycombinator.com/user?id=jchw",
            "https://news.ycombinator.com/user?id=kragen",
            "https://news.ycombinator.com/user?id=lelanthran",
        ],
    },
}


def create_ex_threads(**kwargs):
    return forumscraper.Extractor(
        output=forumscraper.Outputs.write_by_id
        | forumscraper.Outputs.users
        | forumscraper.Outputs.reactions
        | forumscraper.Outputs.threads,
        undisturbed=True,
        **kwargs,
    )


def create_ex_forums_traverse(**kwargs):
    return forumscraper.Extractor(
        output=forumscraper.Outputs.write_by_id
        | forumscraper.Outputs.users
        | forumscraper.Outputs.reactions
        | forumscraper.Outputs.threads,
        thread_pages_max=1,
        pages_max=3,
        pages_forums_max=5,
        pages_threads_max=1,
        undisturbed=True,
        **kwargs,
    )


def create_ex_boards(**kwargs):
    return forumscraper.Extractor(
        output=forumscraper.Outputs.write_by_id
        | forumscraper.Outputs.forums
        | forumscraper.Outputs.tags
        | forumscraper.Outputs.boards,
        thread_pages_max=1,
        pages_max=2,
        pages_forums_max=1,
        pages_threads_max=1,
        undisturbed=True,
        **kwargs,
    )


class tester:
    def __init__(self, cassettedir, correctdir, tempdir):
        self.cassettedir = os.path.realpath(cassettedir)
        self.correctdir = os.path.realpath(correctdir)
        self.tempdir = os.path.realpath(tempdir)

    def run(self, tests):
        pwd = os.getcwd()
        # os.system(r"rm -r " + "'" + self.tempdir + "'")
        try:
            os.mkdir(self.tempdir)
        except Exception:
            pass
        os.chdir(self.tempdir)

        for i in tests:
            try:
                self.test(i)
            except vcr.errors.CannotOverwriteExistingCassetteException as e:
                print(i[0], i[2], file=sys.stderr)

        os.chdir(pwd)

    def test_r(self, data, dirname):
        func = data[1]
        url = data[2]
        dirname2 = strtosha256(url)
        pwd2 = os.getcwd()

        try:
            os.mkdir(dirname2)
            os.chdir(dirname2)
        except FileExistsError:
            return

        with open("!stdout", "w") as out:
            with open("!stderr", "w") as err:
                with vcr.use_cassette(
                    self.cassettedir + "/" + dirname + "/" + dirname2,
                    record_mode="none",  # none once all
                ):
                    func(url, out, err)

        os.chdir(pwd2)
        self.prettify_json(dirname2)
        self.test_check(
            self.correctdir + "/" + dirname + "/" + dirname2,
            self.tempdir + "/" + dirname + "/" + dirname2,
        )

    def test(self, data):
        pwd = os.getcwd()
        dirname = data[0]
        print(data[2], data[0])

        try:
            os.mkdir(dirname)
            os.mkdir(self.cassettedir + "/" + dirname)
        except Exception:
            pass

        os.chdir(dirname)
        exception = None

        try:
            self.test_r(data, dirname)
        except Exception as e:
            exception = e

        os.chdir(pwd)

        if exception is not None:
            raise exception

    def prettify_json(self, path):
        for i in os.scandir(path):
            if not i.is_file(follow_symlinks=False) or i.name[0] == "!":
                continue

            path = i.path

            with open(path, "r") as f:
                parsed = json.load(f)

            with open(path, "w") as f:
                json.dump(parsed, f, indent=2)

    def print_error(self, msg):
        print("###ERROR### {}".format(msg))

    def test_check(self, correct, temp):
        s1 = set([i.name for i in os.scandir(correct)])
        s2 = set([i.name for i in os.scandir(temp)])

        diff = s1 - s2
        if len(diff) != 0:
            self.print_error(
                "{} files were not created, that are in {}".format(str(diff), correct)
            )
        diff = s2 - s1
        if len(diff) != 0:
            self.print_error(
                "{} files were created, that are not in {}".format(str(diff), correct)
            )

        for i in s1 & s2:
            c1 = ""
            with open(correct + "/" + i) as f:
                c1 = f.read()
            c2 = ""
            with open(temp + "/" + i) as f:
                c2 = f.read()

            if c1 == c2:
                continue

            self.print_error("{} is different".format(temp + "/" + i))
            l1 = c1.split("\n")
            l2 = c2.split("\n")
            for line in fdiff(l1, l2):
                print(line)


def test_ignoring_hashed_before_identify():
    ex = create_ex_threads()
    ex.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/",
        output=forumscraper.Outputs.write_by_hash,
    )  # xenforo1
    ex.get_thread(
        "https://kh-vids.net/threads/story-time-with-jube-nagatoro-and-senpai.126609/",
        output=forumscraper.Outputs.write_by_hash,
    )  # xenforo1


def getattrs(obj, string):
    for i in string.split("."):
        try:
            obj = getattr(obj, i)
        except Exception:
            return
        if obj is None:
            break
    return obj


def print_identify(r, out, err):
    if isinstance(r, str):
        print(r, file=out)
    else:
        print(r.__class__.__name__, file=out)


def testurl(create_ex, attr, print_func=None):
    def func(url, out, err):
        ex = create_ex(
            logger=out,
            failed=err,
            requests={
                # "timeout": 60,
                # "retries": 2,
                # "wait": 1.2,
                # "wait_random": 1000,
                "allow_redirects": True,
                "verify": False,
            },
        )

        r = getattrs(ex, attr)
        if r is None:
            return r
        r = r(url)
        if print_func is not None:
            print_func(r, out, err)

    return func


def create_tests():
    for funcname in ["get_forum", "get_board"]:
        engines = tested_urls[funcname]
        for engine in engines.keys():
            urls = engines[engine]
            for url in urls:
                for name in [
                    (engine + "." + funcname),
                    (engine + ".guess"),
                    funcname,
                ]:
                    yield (name, testurl(create_ex_boards, name), url)

                yield (
                    "traverse-" + engine + "." + funcname,
                    testurl(create_ex_forums_traverse, engine + "." + funcname),
                    url,
                )

                for name in [
                    (engine + ".findroot"),
                    "findroot",
                    "identify",
                ]:
                    if (engine == "stackexchange" or engine == "hackernews") and name[
                        -8:
                    ] == "findroot":
                        continue
                    yield (
                        name,
                        testurl(create_ex_boards, name, print_func=print_identify),
                        url,
                    )

    for funcname in ["get_thread", "get_user"]:
        engines = tested_urls[funcname]
        for engine in engines.keys():
            urls = engines[engine]
            for url in urls:
                for name in [
                    (engine + "." + funcname),
                    (engine + ".guess"),
                    funcname,
                ]:
                    yield (name, testurl(create_ex_threads, name), url)

                for name in [
                    (engine + ".findroot"),
                    "findroot",
                    "identify",
                ]:
                    if (engine == "stackexchange" or engine == "hackernews") and name[
                        -8:
                    ] == "findroot":
                        continue
                    yield (
                        name,
                        testurl(create_ex_threads, name, print_func=print_identify),
                        url,
                    )


t = tester("cassettes", "correct", "temp")

t.run(create_tests())
