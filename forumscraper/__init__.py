import sys
import os

from .enums import Outputs, __version__
from .extractors.extractor import *
from .args import argparser

__all__ = [
    "Outputs",
    "net",
    "ForumExtractor",
    "ForumExtractorIdentify",
    "ItemExtractor",
    "Extractor",
    "invision",
    "phpbb",
    "smf",
    "smf1",
    "smf2",
    "xenforo",
    "xenforo1",
    "xenforo2",
    "xmb",
    "main",
    "__version__",
]


def main():
    args = argparser().parse_args(sys.argv[1:] if sys.argv[1:] else ["-h"])

    disturbed = {"undisturbed": True, "pedantic": False}
    if args.pedantic:
        disturbed = {"undisturbed": False, "pedantic": True}

    settings = {
        "output": args.names,
        "max_workers": args.threads,
        "logger": args.log,
        "failed": args.failed,
        "nousers": args.nousers,
        "noreactions": args.noreactions,
        "force": args.force,
        **disturbed,
        "thread_pages_max": args.thread_pages_max,
        "pages_max": args.pages_max,
        "pages_max_depth": args.pages_max_depth,
        "pages_threads_max": args.pages_threads_max,
        "wait": args.wait,
        "wait_random": args.wait_random,
        "retries": args.retries,
        "retry_wait": args.retry_wait,
        "timeout": args.timeout,
        "user-agent": args.user_agent,
        "verify": args.insecure,
        "proxies": args.proxies,
        "headers": args.headers,
        "cookies": args.cookies,
    }

    ex = Extractor(**settings)
    func_name = "guess"
    func = getattr(ex, func_name)

    for url in args.urls:
        if isinstance(url, list):
            ex = url[0](**settings)
            func_name = url[1]
            func = getattr(ex, func_name)
            continue

        ret = func(url, **settings)
        if func_name == "findroot":
            print(f"{ret}\t{url}", file=args.output)
        elif func_name == "identify":
            print(
                "{}\t{}".format(ret if ret is None else ret.__class__.__name__, url),
                file=args.output,
            )

    for i in [args.log, args.failed, args.output]:
        if i not in [sys.stdout, sys.stderr]:
            i.close()
