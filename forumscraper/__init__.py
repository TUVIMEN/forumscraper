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
        "failed": args.failures,
        "nousers": args.nousers,
        "noreactions": args.noreactions,
        "force": args.force,
        **disturbed,
        "thread_pages_max": args.thread_pages_max,
        "pages_max": args.pages_max,
        "pages_max_depth": args.pages_max_depth,
        "pages_threads_max": args.pages_threads_max,
        "wait": args.wait,
        "random_wait": args.random_wait,
        "retries": args.retries,
        "retry_wait": args.retry_wait,
        "timeout": args.timeout,
        "verify": args.insecure,
        "proxies": args.proxies,
        "headers": args.headers,
    }

    ex = Extractor(**settings)
    func = getattr(ex, "guess")

    for url in args.urls:
        if isinstance(url, list):
            ex = url[0](**settings)
            func = getattr(ex, url[1])
            continue

        func(url)

    if args.log != sys.stdout:
        args.log.close()
    if args.failures != sys.stderr:
        args.failures.close()
