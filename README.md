# forumscraper

forumscraper aims to be an universal, automatic and extensive scraper for forums.

# Installation

    pip install forumscraper

# Supported forums

    invision
    phpbb (currently excluding 1.x version)
    smf
    xenforo
    xmb

# Usage

## CLI

### General

Download any kind of supported forums from `URL`s into `DIR`, creating json files for threads named by their id's, same for users but beginning with `m-`.

    forumscraper --directory DIR URL1 URL2 URL3

Above behaviour is set by default(`--names id`), and can be changed with `--names hash` which names files by sha256 sum of their source urls.

    forumscraper --names hash --directory DIR URL

By default if files to be created are found and are not empty function exits not overwriting them. This can be changed using `--force` option.

forumscraper output logging information to `stdout` (can be changed with `--log FILE`) and information about failures to `stderr` (can be changed with `--failures FILE`)

Failures are generally ignored but setting `--pedantic` flag stops the execution if any failure is encountered.

Download `URL`s into `DIR` using `8` threads and log failures into `failures.txt` (note that this option is specified before the `--directory` option, otherwise it would create it in the specified directory if relative path is used)

    forumscraper  --failures failures.txt --threads 8 --directory DIR URL1 URL2 URL3

Download `URL`s with different scrapers

    forumscraper URL1 smf URL2 URL3 .thread URL4 xenforo2.forum URL5 URL6

Type of scrapers can be defined inbetween `URL`s, where all following `URL`s are assigned to previous type i.e. URL1 to default, URL2 and URL3 to smf URL4 and so on.

Type consists of `scraper_name` followed by `.` and `function_name`.

`scraper_name` can be: `all`, `invision`, `phpbb`, `smf`, `smf1`, `smf2`, `xenforo`, `xenforo1`, `xenforo2`, `xmb` where `all`, `xenforo` and `smf` are instances of identification class meaning that they have to download the `URL` to identify its type which may cause redownloading of existing content if many `URL`s are passed as arguments i.e. all resources extracted from once identified type are assumed to have the same type, but passing thousands of thread `URL`s as arguments will always download them before scraping. `smf1`, `smf2`, `xenforo1`, `xenforo2` are just scrapers with assumed version.

`function_name` can be: `guess`, `thread`, `forum`, `tag`, `board` (`board` being the main page of the forum where subforums are listed, and `guess` guesses the other types based on the `URL`s alone, other names are self explainatory).

Default type is set to `all.guess` and it is so efective that the only reason to not use it is to avoid redownloading from running the same command many times which is caused by identification process.

Types can also be shortened e.g. `.` is equivalent to `all.guess`, `.thread` is equivalent to `all.thread` and `xenforo` is equivalent to `xenforo.guess`.

Get version

    forumscraper --version

Get some help (you might discover that many options are abbreviated to single letter)

    forumscraper --help

### Request options

Download `URL` with waiting `0.8` seconds and randomly waiting up to `400` miliseconds for each request

    forumscraper --wait 0.8 --wait-random 400 URL

Download `URL` using `5` retries and waiting `120` seconds between them

    forumscraper --retries 5 --retry-wait 120 URL

By default when encountered a non fatal failure (e.g. status code 301 and not 404) forumscraper tries 3 times waiting 60 seconds before the next attempt, setting `--retries 0` would disable retries and it's a valid (if not better) method assuming that one handles the `--failures` option correctly.

Download `URL` ignoring ssl errors with timeout set to `60` seconds and custom user-agent

    forumscraper --insecure --timeout 60 --user-agent 'why are we still here?'

`--proxies DICT`, `--headers DICT` and `--cookies DICT` (where `DICT` is python stringified dictionary) are directly passed to requests.

### Settings

`--nousers` and `--noreactions` (working only on `xenforo2` and `invision` scrapers) cause ignoring users and reactions respectively, which greatly increases speed of scraping, if you have no use for them you SHOULD consider using these flags (they are not set by default because of choosing extensivity by default).

`--thread-pages-max NUM` and `--pages-max NUM` set max number of pages traversed in each thread and forum respectively.

`--pages-max-depth NUM` limits recursion limit for forums.

`--pages-threads-max NUM` limits number of threads that are processed from every page in forum.

Combining some of the above you get:

    forumscraper --nousers --thread-pages-max 1 --pages-max 1 --pages-threads-max 1 URL1 URL2 URL3

which downloads only one page in one thread for all forums found from every `URL` which is very useful for debugging.

## Library
