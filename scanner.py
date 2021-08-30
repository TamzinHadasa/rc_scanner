"""Scan an EventStream of RecentChanges for certain regexes.

Flags matches in the CLI and logs them to a dated subdirectory of
the changes subdirectory.

Command-line args:
  filter:  The name of a Filter listed in `config.filters`.
  -v / --verbose:  Print all changes, even ones that don't match.
"""
import json
from json.decoder import JSONDecodeError
import pathlib
import sys
import typing
from typing import Any, Optional

import requests
from requests import ConnectionError as RequestsConnectionError, ReadTimeout

try:
    import config
except ImportError:
    # To allow for linting of the repo by Github Action, and to ensure
    # through that that `config_example` is up to date.
    import config_example as config  # type: ignore
from classes import Change, Filter


def get_sys_args() -> tuple[Filter, bool]:
    """Get command line arguments.

    Returns:
      A tuple of two strs, respectively a Filter object to use and a
      bool indicating whether `--verbose` was specified.  The tuple
      members' order matches the order of the args to `run`.
    """
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    try:
        filter_ = config.filters[sys.argv[1]]
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
            eval_change(typing.cast(Change, change), filter_, verbose)
    except (RequestsConnectionError, ReadTimeout) as e:
        print(f"{e.__class__.__name__}: {e.args[0]}")
        if yesno("Restart?"):
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
    user = get_editcount(api, change['user'])

    if count_check(user):
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
            filename = f"{change['user']}_{new_revision}".replace(":", "-")

            if config.LOG_LEVEL:
                log_revid(new_revision)
            if config.LOG_LEVEL == 2:
                log_flagged_change(change, filtername=filter_.name)
            elif config.LOG_LEVEL == 3:
                log_content(
                    folder,
                    filename,
                    f"{filter_.name}\n\n{message}\n\n{change}\n\n{text}"
                )
                log_flagged_change(change,
                                   (folder, filename),
                                   filtername=filter_.name)
    elif verbose:
        print(f"Skipping.  Edit count was {user['editcount']} > "
              + str(config.MAX_EDIT_COUNT))


# Avoid having to check `config.MAX_EDIT_COUNT` on every loop.
def count_check(user: dict[str, Any]) -> bool:
    """Compare an edit count to `config.MAX_EDIT_COUNT`, if specified.

    If `config.MAX_EDIT_COUNT` is None, return True always.

    Arg:
      user:  A dict of user data drawn from the EventStream.

    Returns:
      A bool indicating whether the user's edit count was under the max,
      or indicating that no max was specified.
    """
    if config.MAX_EDIT_COUNT is None:
        return True
    try:
        return user['editcount'] < config.MAX_EDIT_COUNT
    # Trying to figure out why this happened once.  Will replace with
    # proper error handling once it's clear why.
    except KeyError:
        print(user)
        raise


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
    # Trying to figure out why this happened once.  Will replace with
    # proper error handling once it's clear why.
    except KeyError:
        print(r.json())
        raise


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
    # Trying to figure out why this happened once.  Will replace with
    # proper error handling once it's clear why.
    except KeyError:
        print(r.json())
        raise


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


def log_flagged_change(change: Change,
                       changes_path: Optional[tuple[str, str]] = None,
                       *,
                       filtername: str) -> None:
    """Log that a change has been flagged.

    Args:
      change:  A dict of the change, taken from the EventStream.
      changes_path:  None or a tuple of two strs, representing the
        folder and file to which a change was logged.
      filtername:  The name of a Filter object.
    """
    log_path = f"{config.LOG_DIR}/{config.FLAGGED_CHANGES_LOG}"
    with open(log_path, 'r', encoding='utf-8') as flaglog:
        try:
            data = json.load(flaglog)
        except JSONDecodeError:
            print(f"Failed to read {log_path}")
            if not yesno("RESET ALL DATA? (y/n)  (If this is your first time "
                         "running the Scanner at LOG_LEVEL 3, say 'y'.)"):
                sys.exit()
            data = []

    entry: dict[str, Any] = {'filter': filtername, 'change': change}
    if changes_path:
        entry['log'] = {'folder': changes_path[0],
                        'file': changes_path[1]}
    data.append(entry)

    assert data, "Something is terribly wrong."
    with open(log_path, 'w', encoding='utf-8') as flaglog:
        json.dump(data, flaglog, indent=4)


def yesno(question: str) -> bool:
    """Prompt a y/n question to the user

    Arg:
      question:  The question to ask

    Returns:
      bool
    """
    prompt = f'{question} '
    ans = input(prompt).strip().lower()
    if ans not in ('y', 'n'):
        print(f'{ans} is invalid.  Please try again.')
        return yesno(question)
    return ans == 'y'


if __name__ == '__main__':
    run(*get_sys_args())
