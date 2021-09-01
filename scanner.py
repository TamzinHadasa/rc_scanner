"""Scan an EventStream of RecentChanges for certain regexes.

Flags matches in the CLI and logs them to a dated subdirectory of
the changes subdirectory.

Command-line args:
  filter:  The name of a Filter listed in `config.filters`.
  -v / --verbose:  Print all changes, even ones that don't match.
"""
import pathlib
import sys
import typing
from typing import Any

import requests
from requests import ConnectionError as RequestsConnectionError, ReadTimeout

try:
    import config
except ImportError:
    # To allow for linting of the repo by Github Action, and to ensure
    # through that that the example file is up to date.
    from examples import config
try:
    import filterlist
except ImportError:
    from examples import filterlist  # pylint: disable=ungrouped-imports
import utils
from utils import Change, QueryRaceCondition
from filter_ import Filter
import flaglog


def _get_sys_args() -> tuple[Filter, bool]:
    """Get command line arguments.

    Returns:
      A tuple of two strs, respectively a Filter object to use and a
      bool indicating whether `--verbose` was specified.  The tuple
      members' order matches the order of the args to `run`.
    """
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    try:
        filter_ = filterlist.filterlist[sys.argv[1]]
    except IndexError:
        print("Error: No filter specified from `config.filters`.")
    except KeyError:
        print(f"Error: {sys.argv[1]} is not a valid key in `config.filters`.")
    else:
        return filter_, verbose
    sys.exit()


def run(filter_: Filter, verbose: bool) -> None:
    """Execute the script.

    Args:
      filter_:  A Filter to use.
      verbose:  A bool of whether to print events that don't match.
    """
    make_dirs()
    stream = filter_.create_stream()

    print("Current settings:")
    print(f"Filter: {filter_.name}")
    if verbose:
        print('Verbose: True')
    print('\n'.join(f"{k} == {v}" for k, v in vars(config).items()
                    if k.upper() == k))
    if config.LOG_LEVEL > 3:
        raise ValueError("LOG_LEVEL must be between 0 and 3 inclusive.")
    print('Waiting for first edit.')

    try:
        for change in stream:
            try:
                eval_change(typing.cast(Change, change), filter_, verbose)
            except QueryRaceCondition as e:
                print("A race condition occurred, likely due to a page being "
                      "deleted before it could be queried. The API returned "
                      "the following error message:\n", e.args[0])
    except (RequestsConnectionError, ReadTimeout) as e:
        print(f"{e.__class__.__name__}: {e.args[0]}")
        if utils.yesno("Restart?"):
            run(filter_, verbose)
        else:
            print("Shutting down.")
            sys.exit()


def make_dirs(level: int = config.LOG_LEVEL) -> None:
    """Make the necessary directories and files if they don't exist.

    For any given nonzero level, starts by recursively calling for the
    lower level.  So level 3 calls for 2, which calls for 1, which calls
    for 0.

    Arg:
      level:  An int of the logging level.  `config.LOG_LEVEL` by
        default.
    """
    if level > 1:
        make_dirs(level - 1)
    match level:
        case 1:
            pathlib.Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
            pathlib.Path(config.LOG_DIR,
                         config.REVID_LOG).touch(exist_ok=True)
        case 2:
            pathlib.Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
            pathlib.Path(config.LOG_DIR,
                         config.FLAGGED_CHANGES_LOG).touch(exist_ok=True)
            flaglog.init()
        case 3:
            pathlib.Path(config.LOG_DIR,
                         config.CHANGES_SUBDIR).mkdir(parents=True,
                                                      exist_ok=True)


def eval_change(change: Change, filter_: Filter, verbose: bool) -> None:
    """Parse a change and log it if applicable.

    Args:
      change:  A Change to evaluate.
      filter_:  A Filter to use.
      verbose:  A bool of whether to print events that don't match.
    """
    api = filter_.apis[change['server_name']]
    username = change['user']
    editcount = get_editcount(api, username)
    if not filter_.count_under_max(editcount):
        if verbose:
            print(f"Skipping.  Edit count was {editcount} > "
                  f"{filter_.max_edits}.")
        return
    if filter_.page_is_repeat(change['title']):
        if verbose:
            print("Skipping.  Page already in flagged changes log.")
        return

    text = get_text(api, change['revision']['new'])
    hits = filter_.search_regexes(text)
    if verbose or hits:
        print('{user} {verb} "{title}" at {meta[dt]}.'
              .format(verb=change['type'].removesuffix("e") + "ed",
                      **change))
    if hits:
        message = ("***MATCH*** with regex"
                   + ("es " if len(hits) > 1 else " ")
                   + ", ".join(f"`{r.pattern}`" for r in hits)
                   + ": " + change['meta']['uri'])
        print(message)

        folder = (f"{config.LOG_DIR}/{config.CHANGES_SUBDIR}/"
                  + change['meta']['dt'][:10])
        new_revision = change['revision']['new']
        # Colons are invalid in most filenames.
        filename = f"{username}_{new_revision}".replace(":", "-")
        if config.LOG_LEVEL:
            log_revid(new_revision)
        if config.LOG_LEVEL == 2:
            flaglog.append({'filter': filter_.name,
                            'change': change,
                            'log': {'folder': None,
                                    'file': None}})
        elif config.LOG_LEVEL == 3:
            log_content(
                folder,
                filename,
                f"{filter_.name}\n\n{message}\n\n{change}\n\n{text}"
            )
            flaglog.append({'filter': filter_.name,
                            'change': change,
                            'log': {'folder': folder,
                                    'file': filename}})


def get_text(api: str, revision: int) -> str:
    """Get a revision's text, given its ID #.

    Args:
      api:  A str of a Wikimedia site's API URL.
      revision:  An int of a MediaWiki oldid.

    Returns:
      A str of the revision's HTML.
    """
    params: dict[str, str | int] = {'format': 'json',
                                    'action': 'parse',
                                    'oldid': revision,
                                    'prop': 'wikitext'}
    r = requests.get(url=api, params=params)
    try:
        return r.json()['parse']['wikitext']['*']
    except KeyError as e:
        raise QueryRaceCondition(r.json()) from e


def get_editcount(api: str, username: str) -> dict[str, Any]:
    """Get a user, given their username.

    Args:
      api:  A str of a Wikimedia site's API URL.
      username:  A str of a username

    Returns:
      An int of a user's edit count.
    """
    params: dict[str, str] = {'format': 'json',
                              'action': 'query',
                              'list': 'users',
                              'ususers': username,
                              'usprop': 'editcount'}
    r = requests.get(url=api, params=params)
    try:
        return r.json()['query']['users'][0]['editcount']
    except KeyError as e:
        raise QueryRaceCondition(r.json()) from e


def log_revid(revid: int) -> None:
    """Log a revision ID to the revid log.

    Arg:
      revid:  An int of a MediaWiki olid.
    """
    with open(
        f"{config.LOG_DIR}/{config.REVID_LOG}",
        "a",
        encoding='utf-8'
    ) as f:
        f.write(f"{revid}\n")


def log_content(folder: str, filename: str, content: str) -> None:
    """Log a revision's content to a dated subfolder of `logs/`.

    Args:
      folder:  A str of the dated subfolder.
      filename:  A str of the filename.
      content:  A str of what to log.
    """
    try:
        f = open(f"{folder}/{filename}", 'w+', encoding='utf-8')  # pylint: disable=consider-using-with
    except FileNotFoundError:
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        f = open(f"{folder}/{filename}", 'w+', encoding='utf-8')
    with f:
        f.write(content)


if __name__ == '__main__':
    run(*_get_sys_args())
