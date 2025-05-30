import os
import sys
import argparse
import ast
import gzip
import bz2
import lzma

from .utils import (
    url_valid,
    conv_curl_header_to_requests,
    conv_curl_cookie_to_requests,
)
from .defs import Outputs, __version__
from .extractors.extractor import *


def valid_directory(directory):
    try:
        return os.chdir(directory)
    except:
        raise argparse.ArgumentTypeError(
            'couldn\'t change directory to "{}"'.format(directory)
        )


def valid_names(name):
    if name == "id":
        return Outputs.write_by_id
    elif name == "hash":
        return Outputs.write_by_hash
    else:
        raise KeyError(f'"{name}" is neither id nor hash')


def valid_type(type_name):
    if url_valid(type_name) is not None:
        return type_name

    ret = [Extractor, "guess"]

    forums = {
        "all": Extractor,
        "smf": smf,
        "smf1": smf1,
        "smf2": smf2,
        "phpbb": phpbb,
        "xenforo": xenforo,
        "xenforo1": xenforo1,
        "xenforo2": xenforo2,
        "invision": invision,
        "xmb": xmb,
        "hackernews": hackernews,
        "stackexchange": stackexchange,
        "vbulletin": vbulletin,
    }
    forums_identifiers = ["all", "smf", "xenforo"]
    funcs = ["guess", "identify", "findroot", "thread", "user", "forum", "tag", "board"]

    names = type_name.split(".")
    namesl = len(names)

    if (namesl == 1 and len(names[0]) == 0) or namesl > 2:
        raise KeyError(f"{type_name} is not a valid scraper type")

    if namesl == 2 and len(names[0]) == 0 and len(names[1]) == 0:
        return ret

    if len(names[0]) > 0:
        r = forums.get(names[0])
        if not r:
            raise KeyError(f'"{names[0]}" forum scraper does not exists')
        ret[0] = r

    if namesl == 2 and len(names[1]) > 0:
        if names[1] in funcs:
            if (
                names[1] == "identify"
                and len(names[0])
                and names[0] not in forums_identifiers
            ):
                raise (f'{names[0]} does not have function "identify"')
            if names[1] not in ["guess", "identify", "findroot"]:
                names[1] = "get_" + names[1]
            ret[1] = names[1]
        else:
            raise KeyError(f'"{names[1]}" type does not exists')
    return ret


def valid_compression_type(type_name):
    types = {
        "lzma": lzma.compress,
        "bzip2": bz2.compress,
        "gzip": gzip.compress,
        "none": None,
    }

    if type_name not in types.keys():
        raise KeyError(f"{type_name} is not a valid compression type")
    return types.get(type_name)


def valid_header(src):
    r = conv_curl_header_to_requests(src)
    if r is None:
        raise argparse.ArgumentTypeError('Invalid header "{}"'.format(src))
    return r


def valid_cookie(src):
    r = conv_curl_cookie_to_requests(src)
    if r is None:
        raise argparse.ArgumentTypeError('Invalid cookie "{}"'.format(src))
    return r


def argparser():
    parser = argparse.ArgumentParser(
        description="Forum scraper that aims to be universal, automatic and extensive.",
        add_help=False,
    )

    parser.add_argument(
        "urls",
        metavar="URL|TYPE",
        type=valid_type,
        nargs="*",
        help="url pointing to source. Specifying type changes scraper for all next urls. Type consists of forum name which can be all, invision, phpbb, smf, smf1, smf2, xenforo, xenforo1, xenforo2, xmb, stackexchange, hackernews and it can by followed by a '.' and function name which can be guess, thread, forum, tag, board, user, identify, findroot. By default set to all.guess equivalent to .guess and .",
    )

    general = parser.add_argument_group("General")
    general.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help message and exit",
    )
    general.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="Print program version and exit",
    )
    general.add_argument(
        "-t",
        "--threads",
        metavar="NUM",
        type=int,
        help="run tasks using NUM of threads",
        default=1,
    )
    general.add_argument(
        "-p",
        "--pedantic",
        action="store_true",
        help="Exit if anything fails",
    )

    files = parser.add_argument_group("Files")
    files.add_argument(
        "-d",
        "--directory",
        metavar="DIR",
        type=valid_directory,
        help="Change directory to DIR",
    )
    files.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="forcefully overwrite files, may cause redownloading if found urls are not unique",
    )
    files.add_argument(
        "--names",
        metavar="NAME",
        type=valid_names,
        help="Change naming convention of created files to NAME, which can be either id or hash",
        default=Outputs.write_by_id,
    )
    files.add_argument(
        "--compression",
        metavar="ALGO",
        type=valid_compression_type,
        help="Compress created files using set algorithm, that can be none, gzip, bzip2, lzma",
        default=None,
    )
    files.add_argument(
        "-l",
        "--log",
        metavar="FILE",
        type=lambda x: open(x, "w"),
        help="log results to FILE (by default set to stdout)",
        default=sys.stdout,
    )
    files.add_argument(
        "-F",
        "--failed",
        metavar="FILE",
        type=lambda x: open(x, "w"),
        help="log failures to FILE (by default set to stderr)",
        default=sys.stderr,
    )
    files.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        type=lambda x: open(x, "w"),
        help="store results to FILE (by default set to stdout), work only for identify and findroot functions and --only-urls options",
        default=sys.stdout,
    )

    settings = parser.add_argument_group("Settings")
    settings.add_argument(
        "--html",
        action="store_true",
        help="save html files along side json output with .html extension",
    )
    settings.add_argument(
        "--nothreads",
        action="store_true",
        help="do not download threads (works only when page passed is not a thread)",
    )
    settings.add_argument(
        "--users",
        action="store_true",
        help="download users",
    )
    settings.add_argument(
        "--reactions",
        action="store_true",
        help="download reactions",
    )
    settings.add_argument(
        "--boards",
        action="store_true",
        help="create boards files",
    )
    settings.add_argument(
        "--tags",
        action="store_true",
        help="create tags files",
    )
    settings.add_argument(
        "--forums",
        action="store_true",
        help="create forums files",
    )
    settings.add_argument(
        "--only-urls-forums",
        action="store_true",
        help="output urls to found forums to output file without scraping",
    )
    settings.add_argument(
        "--only-urls-threads",
        action="store_true",
        help="output urls to found threads to output file without scraping",
    )
    settings.add_argument(
        "--thread-pages-max",
        metavar="NUM",
        type=int,
        help="set max number of pages traversed in threads",
    )
    settings.add_argument(
        "--pages-max",
        metavar="NUM",
        type=int,
        help="set max number of pages traversed in pages amassing threads e.g. forums, tags, boards",
    )
    settings.add_argument(
        "--pages-max-depth",
        metavar="NUM",
        type=int,
        help="set max recursion depth",
    )
    settings.add_argument(
        "--pages-forums-max",
        metavar="NUM",
        type=int,
        help="set max number of forums to be processed in every page",
    )
    settings.add_argument(
        "--pages-threads-max",
        metavar="NUM",
        type=int,
        help="set max number of threads to be processed in every page",
    )

    request_set = parser.add_argument_group("Request settings")
    request_set.add_argument(
        "-w",
        "--wait",
        metavar="SECONDS",
        type=float,
        help="Sets waiting time for each request to SECONDS",
    )
    request_set.add_argument(
        "-W",
        "--wait-random",
        metavar="MILISECONDS",
        type=int,
        help="Sets random waiting time for each request to be at max MILISECONDS",
    )
    request_set.add_argument(
        "-r",
        "--retries",
        metavar="NUM",
        type=int,
        help="Sets number of retries for failed request to NUM",
    )
    request_set.add_argument(
        "--retry-wait",
        metavar="SECONDS",
        type=float,
        help="Sets interval between each retry",
    )
    request_set.add_argument(
        "-m",
        "--timeout",
        metavar="SECONDS",
        type=float,
        help="Sets request timeout",
    )
    request_set.add_argument(
        "-k",
        "--insecure",
        action="store_false",
        help="Ignore ssl errors",
    )
    request_set.add_argument(
        "-A",
        "--user-agent",
        metavar="UA",
        type=str,
        help="Sets custom user agent",
    )
    request_set.add_argument(
        "-L",
        "--location",
        action="store_true",
        help="Allow for redirections, can be dangerous if credentials are passed in headers",
    )
    request_set.add_argument(
        "-x",
        "--proxies",
        metavar="DICT",
        type=lambda x: dict(ast.literal_eval(x)),
        help='Set requests proxies dictionary, e.g. -x \'{"http":"127.0.0.1:8080","ftp":"0.0.0.0"}\'',
    )
    request_set.add_argument(
        "-H",
        "--header",
        metavar="HEADER",
        type=valid_header,
        action="append",
        help="Set header, can be used multiple times e.g. -H 'User: Admin' -H 'Pass: 12345'",
    )
    request_set.add_argument(
        "-b",
        "--cookie",
        metavar="COOKIE",
        type=valid_cookie,
        action="append",
        help="Set cookie, can be used multiple times e.g. -b 'auth=8f82ab' -b 'PHPSESSID=qw3r8an829'",
    )

    return parser
