# forumscraper

forumscraper aims to be an universal, automatic and extensive scraper for forums.

# Installation

    pip install forumscraper

# Supported forums

- Invision Power Board (only 4.x version)
- PhpBB (currently excluding 1.x version)
- Simple Machines Forum
- XenForo
- XMB
- Hacker News (has aggressive protection)
- StackExchange
- vBulletin (3.x and higher)

# Output examples

Are created by `create-format-examples` script and contained in [examples](https://github.com/TUVIMEN/forumscraper/tree/master/examples) directory where they're grouped based on scraper and version. Files are in `json` format.

# Discover

You can find forums discoverer script in [discover](discover).

# Usage

## CLI

### General

Download any kind of supported forums from `URL`s into `DIR`, creating json files for threads named by their id's, same for users but beginning with `m-` e.g. `24` `29` `m-89` `m-125`.

    forumscraper --directory DIR URL1 URL2 URL3

Above behaviour is set by default `--names id`, and can be changed with `--names hash` which names files by sha256 sum of their source urls.

    forumscraper --names hash --directory DIR URL

By default if files to be created are found and are not empty, function exits not overwriting them. This can be changed using `--force` option.

forumscraper output logging information to `stdout` (can be changed with `--log FILE`) and information about failures to `stderr` (can be changed with `--failed FILE`)

Failures are generally ignored but setting `--pedantic` flag stops the execution if any failure is encountered.

Download `URL`s into `DIR` using `8` threads and log failures into `failures.txt` (note that this option is specified before the `--directory` option, otherwise it would create it in the specified directory if relative path is used)

    forumscraper  --failures failures.txt --threads 8 --directory DIR URL1 URL2 URL3

Download `URL`s with different scrapers

    forumscraper URL1 smf URL2 URL3 .thread URL4 xenforo2.forum URL5 URL6

Type of scrapers can be defined in between `URL`s, where all following `URL`s are assigned to previous type i.e. URL1 to default, URL2 and URL3 to smf and so on.

Type consists of `scraper_name` followed by `.` and `function_name`.

`scraper_name` can be: `all`, `invision`, `phpbb`, `hackernews`, `stackexchange`, `vbulletin`, `smf`, `smf1`, `smf2`, `xenforo`, `xenforo1`, `xenforo2`, `xmb` where `all`, `xenforo` and `smf` are instances of identification class meaning that they have to download the `URL` to identify its type which may cause redownloading of existing content if many `URL`s are passed as arguments i.e. all resources extracted from once identified type are assumed to have the same type, but passing thousands of thread `URL`s as arguments will always download them before scraping. `smf1`, `smf2`, `xenforo1`, `xenforo2` are just scrapers with assumed version.

`function_name` can be: `guess`, `findroot`, `thread`, `user`, `forum`, `tag`, `board` (`board` being the main page of the forum where subforums are listed). `guess` guesses the other types based on the `URL`s alone, `findroot` find the main page of forum from any link on site (useful for downloading the whole forum from random urls), other names are self explainatory.

`all`, `xenforo` and `smf` have also `identify` function that identifies site type.

`findroot` and `identify` write results to file specified by the `--output` (by default set to `stdout`) option which is made specifically for these functions. `findroot` return url to board and url from which it was found, separated by `\t`. `identify` returns name of scraper and url from which it was identified, separated by `\t`.

Default type is set to `all.guess` and it is so efective that the only reason to not use it is to avoid redownloading from running the same command many times which is caused by identification process when using `--names id`.

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

`--location` Allow for redirections.

`--proxies DICT` (where `DICT` is python stringified dictionary) are directly passed to requests library, e.g. `--proxies '{"http":"127.0.0.1:8080","ftp":"0.0.0.0"}'`.

`--header "Key: Value"` very similar to `curl` `--header` option, can be specified multiple times e.g. `--header 'User: Admin' --header 'Pass: 12345'`. Similar to `curl` `Cookie` header will be parsed like `Cookie: key1=value1; key2=value2` and will be changed to cookies.

`--cookie "Key=Value"` very similar to `curl` `--cookie` option, can be specified multiple times e.g. `--cookie 'auth=8f82ab' --cookie 'PHPSESSID=qw3r8an829'`.


### Settings

`--nothreads` don't download threads unless url passed is a thread.

`--users` download users.

`--reactions` download reactions.

`--boards` create board files.

`--tags` create tags files.

`--forums` create forums files.

`--compression ALGO` compresses created files with `ALGO`, that can be `none`, `gzip`, `bzip2`, `lzma`.

`--only-urls-forums` write found forum urls to `output`, don't scrape.

`--only-urls-threads` write found thread urls to `output`, don't scrape.

`--thread-pages-max NUM` and `--pages-max NUM` set max number of pages traversed in each thread and forum respectively.

`--html` save html files.

`--pages-max-depth NUM` sets recursion limit for forums.

`--pages-forums-max NUM` limits number of forums that are processed from every page in forum.

`--pages-threads-max NUM` limits number of threads that are processed from every page in forum.

Combining some of the above you get:

    forumscraper --thread-pages-max 1 --pages-max 1 --pages-forums-max 1 --pages-threads-max 1 URL1 URL2 URL3

which downloads only one page in one thread from one forum found from every `URL` which is very useful for debugging.

## Library

### Code

```python
import os
import sys
from forumscraper import extractor, outputs, xenforo2

ex = extractor(timeout=90)

thread = ex.guess(
    "https://xenforo.com/community/threads/forum-data-breach.180995/",
    output=outputs.data | outputs.threads | outputs.users,
    timeout=60,
    retries=0,
)  # automatically identify forum and type of page and save results
thread["data"]["threads"][0]  # access the result
thread["data"]["users"]  # found users are also saved into an array

forum = ex.get_forum(
    "https://xenforo.com/community/forums/off-topic.7/",
    output=outputs.data | outputs.urls | outputs.threads,
    retries=0,
)  # get list of all threads and  urls from forum
forum["data"]["threads"]  # access the results
forum["urls"]["threads"]  # list of urls to found threads
forum["urls"]["forums"]  # list of urls to found forums

threads = ex.smf.get_forum(
    "https://www.simplemachines.org/community/index.php?board=1.0",
    output=outputs.only_urls_threads,
)  # gather only urls to threads without scraping data
threads["urls"]["threads"]
threads["urls"]["forums"]  # is also created

forums = ex.smf.get_board(
    "https://www.simplemachines.org/community/index.php",
    output=outputs.only_urls_forums,
)  # only get a list of urls to all forums
threads["urls"]["forums"]
threads["urls"]["boards"]
threads["urls"]["tags"]  # tags and boards are also gathered

ex.smf.get_thread(
    "https://www.simplemachines.org/community/index.php?topic=578496.0",
    output=outputs.only_urls_forums,
)  # returns none

os.mkdir("xenforo")
os.chdir("xenforo")

xen = xenforo2(
    timeout=30,
    retries=3,
    retry_wait=10,
    wait=0.4,
    wait_random=400,
    max_workers=8,
    output=outputs.write_by_id | outputs.threads,
)
# specifies global config, writes output in files by their id (beginning with m- in case of users) in current directory
# ex.xenforo.v2 is an initialized instance of xenforo2 with the same settings as ex
# output by default is set to outputs.write_by_id|outputs.threads anyway

failures = []
files = xen.guess(
    "https://xenforo.com/community/",
    logger=sys.stdout,
    failed=failures,
    undisturbed=true,
)
# failed=failures writes all the failed requests to be saved in failures array or file

for i in failures:  # try to download failed one last time
    x = i.split(" ")
    if len(x) == 4 and x[1] == "failed":
        xen.get_thread(x[0], state=files)  # append results

files["files"]["threads"]
files["files"]["users"]  # lists of created files

# the above uses scraper that is an instance of ForumExtractor
# if the instance is ForumExtractorIdentify, before checking if the files already exist based on url the page has to be downloaded to be indentified. because of that any getters from this class return results with 'scraper' field pointing to the indentified scraper type, and further requests should be done through that object.

xen = xenforo2(
    timeout=30,
    retries=3,
    retry_wait=10,
    wait=0.4,
    wait_random=400,
    max_workers=8,
    output=outputs.write_by_hash | outputs.threads,
    undisturbed=true,
)
# specifies global config, writes output in files by sha256 hash of their url in current directory

failures = []
files = xen.guess("https://xenforo.com/community/", logger=sys.stdout, failed=failures)
scraper = files["scraper"]  # identified forumscraper instance

for i in failures:  # try to download failed one last time
    x = i.split(" ")
    if len(x) == 4 and x[1] == "failed":
        scraper.get_thread(x[0], state=files)  # use of already identified class

os.chdir("..")
```

### Scrapers

forumscraper defines:

    invision
    phpbb
    smf1
    smf2
    xenforo1
    xenforo2
    xmb
    hackernews
    stackexchange
    vbulletin

scrapers that are instances of `ForumExtractor` class, and also:

    Extractor
    smf
    xenforo

that are instances of `ForumExtractorIdentify`.

Instances of `ForumExtractorIdentify` identify and pass requests to `ForumExtractor` instances in them. This means that content from the first link is downloaded regardless if files with finished work exist. (So running `get_thread` method on failures using these scrapers will cause needless redownloading, unless `forumscraper.Outputs.write_by_hash` is used)

`Extractor` scraper has `invision`, `phpbb`, `smf`, `xenforo`, `xmb`, `hackernews`, `stackexchange`, `vbulletin` fields that are already initialized scrapers of declared type.

`xenforo` and `smf` have `v1` and `v2` fields that are already initialized scrapers of declared versions.

Initialization of scrapers allows to specify `**kwargs` as settings that are kept for requests made from these scrapers.

All scrapers have the following methods:

    guess
    findroot
    get_thread
    get_user
    get_forum
    get_tag
    get_board

`ForumExtractorIdentify` scrapers additionally have `identify` method.

which take url as argument, optionally already downloaded html either as `str`, `bytes` or `reliq` and state which allows to append output to previous results, and the same type of settings used on initialization of class, e.g.

```python
    ex = forumscraper.Extractor(headers={"Referer":"https://xenforo.com/community/"},timeout=20)
    state = ex.guess('https://xenforo.com/community/threads/selling-and-buying-second-hand-licenses.131205/',timeout=90)

    html = requests.get('https://xenforo.com/community/threads/is-it-possible-to-set-up-three-websites-with-a-second-hand-xenforo-license.222507/').text
    ex.guess('https://xenforo.com/community/threads/is-it-possible-to-set-up-three-websites-with-a-second-hand-xenforo-license.222507/',html,state,timeout=40)
```

`guess` method identifies based only on the url what kind of page is being passed and calls other methods so other methods are needed mostly for exceptions.

For most cases using `Extractor` and `guess` is preferred since they work really well. The only exceptions are if site has irregular urls so that `guess` doesn't work, or if you make a lot of calls to the same site with `output=forumscraper.Outputs.write_by_id` e.g. trying to scraper failed urls.

`guess` method creates `scraper-method` field in output that is pointing to function used.

Methods called from instances of `ForumExtractorIdentify` do the same, but also create `scraper` field pointing to instance of `ForumExtractor` used. This allows to circumvent the need of redownloading for each call just for identification.

```python
failures = []
results = ex.guess('https://www.simplemachines.org/community/index.php',output=forumscraper.Outputs.urls|forumscraper.Outputs.data,failed=failures,undisturbed=True)
#results['scraper-method'] points to ex.smf.v2.get_board

scraper = results['scraper'] #points to ex.smf.v2

for i in failures: #try to download failed one last time
    x = i.split(' ')
    if len(x) == 4 and x[1] == 'failed':
        scraper.get_thread(x[0],state=results) #save results in 'results'
```

`identify` and `findroot` methods ignore state, even though they can take it as argument.

`findroot` method returns `None` on failure or url to the root of the site (i.e. board) from any link of site, that is very useful when having some random urls and wanting to automatically download the whole forum.

`identify` methods returns `None` on failure or initialized `ForumExtractor` that can scrape given url.

The get functions and `guess` return `None` in case of failure or `dict` defined as

    {
       'data': {
            "boards": [],
            "tags": [],
            "forums": [],
            'threads': [],
            'users': []
        },
        'urls': {
            'threads': [],
            'users': [],
            'reactions':[]
            'forums': [],
            'tags': [],
            'boards': []
        }
       'files': {
            "boards": [],
            "tags": [],
            "forums": [],
            'threads': [],
            'users': []
        },
        'visited': set(),
        "scraper": None,
        "scraper-method": None,
    }

Where `data` field contains resulting dictionaries of data.

`urls` field contains found urls of specific type.

`file` field contains created files with results.

`visited` field contains every url visited by scraper, which will refuse to visit them again, see `force` setting for more info.

### Settings

At initialization of scrapers and use of `get_` methods you can specify the same settings.

`output=forumscraper.Outputs.write_by_id|forumscraper.Outputs.urls|forumscraper.Outputs.threads` changes behaviour of scraper and results returned by id. It takes flags from `forumscraper.Outputs`:

 - `write_by_id` - write results in json in files named by their id (beginning with `m-` in case of users) e.g `21` `29` `m-24` `m-281`
 - `write_by_hash` - write results in json in files named by sha256 hash of their source url
 - `only_urls_threads` - do not scrape, just get urls to threads and things above them
 - `only_urls_forums` - ignore everything logging only urls to found forums, tags and boards
 - `urls`  - save url from which resources were scraped
 - `data` - save results in python dictionary
 - `threads` - scrape threads
 - `users` - scrape users
 - `reactions` - scrape reactions in threads
 - `boards` - scrape boards
 - `forums` - scrape forums
 - `tags` - scrape tags

Disabling `users` and `reactions` greatly speeds up getting `xenforo` and `invision` threads.

`boards` `forums` and `tags` create files with names beginning with respectively `b-`, `f-`, `t-` followed by sha256 hash of source url. These options may be useful for getting basic information about threads without downloading them.

`logger=None`, `failed=None` can be set to list or file to which information will be logged.

`logger` logs only urls that are downloaded.

`failed` logs failures in format:

```
RESOURCE_URL failed STATUS_CODE FAILED_URL
RESOURCE_URL failed completely STATUS_CODE FAILED_URL
```

Resource fails completely only because of `STATUS_CODE` e.g. `404`.

`undisturbed=False` if set, scraper doesn't care about standard errors.

`pedantic=False` if set, scraper fails because of errors in scraping resources related to currently scraped e.g. if getting users of reactions fails.

`force=False` if set, scraper overwrites files, but will still refuse to scrape urls found in `visited` field of state, if you are passing state between functions and you want to redownload them you will have to set it to empty set e.g. `state['visited'] = set()` before every function call.

`max_workers=1` set number of threads used for scraping.

`compress_func=None` set compression function that will be called when writing to files, function should accept data in `bytes` as the first argument, e.g. `gzip.compress`.

`verify=True` if set to `False` ignore ssl errors.

`timeout=120` request timeout.

`allow_redirects=False` allow for redirections.

`proxies={}` requests library proxies dictionary.

`headers={}` requests library headers dictionary.

`cookies={}` requests library cookies dictionary.

`user_agent=None` custom user-agent.

`wait=0` waiting time for each request.

`wait_random=0` random waiting time up to specified miliseconds.

`retries=3` number of retries attempted in case of failure.

`retry_wait=60` waiting time between retries.

`html=False` save html files.

`thread_pages_max=0` if greater than `0` limits number of pages traversed in threads.

`pages_max=0` limits number of pages traversed in each forum, tag or board.

`pages_max_depth=0` sets recursion limit for forums, tags and boards.

`pages_forums_max=0` limits number of forums that are processed from every page in forum or board.

`pages_threads_max=0` limits number of threads that are processed from every page in forum or tag.
