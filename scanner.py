"""Scan an EventStream of RecentChanges for certain regexes.

Flags matches in the CLI and logs them to a dated subdirectory of
the changes subdirectory.

Command-line arg:
  -v / --verbose:  Print all changes, even ones that don't match.
"""
import json
from json.decoder import JSONDecodeError
import pathlib
import sys
import typing
from typing import Any, Optional, Tuple, TypedDict

import requests
from requests import ReadTimeout
from pywikibot.comms.eventstreams import EventStreams

import config  # pylint: disable=import-error

_API = f"https://{config.SITE}/w/api.php?"


class Meta(TypedDict):
    """Structure of Change.meta."""
    domain: str
    partition: int
    uri: str
    offset: int
    topic: str
    request_id: str
    schema_uri: str
    dt: str
    id: str


class Change(TypedDict):
    """Structure of a change in the EventStream."""
    comment: str
    wiki: str
    type: str
    server_name: str
    server_script_path: str
    namespace: int
    title: str
    bot: bool
    server_url: str
    length: dict[str, int]
    meta: Meta
    user: str
    timestamp: int
    patrolled: bool
    id: int
    minor: bool
    revision: dict[str, int]


def run(verbose: bool = False) -> None:
    """Execute the script.

    Arg:
      verbose:  A bool of whether to print events that don't match.
    """
    make_dirs()
    stream = EventStreams(streams=config.STREAMS)
    stream.register_filter(**config.FILTER)

    print('Current settings:')
    if verbose:
        print('Verbose -> True')
    print('\n'.join(f"{k} = {v}" for k, v in vars(config).items()
                    if k.upper() == k))
    if config.LOG_LEVEL > 3:
        raise ValueError("LOG_LEVEL must be between 0 and 3 inclusive.")
    print('Waiting for first edit.')

    for change in stream:
        change = typing.cast(Change, change)
        user = get_user(change['user'])

        if count_check(user):
            text = get_text(change['revision']['new'])
            hits = [r for r in config.REGEXES if r.search(text)]
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
                    log_flagged_change(change)
                elif config.LOG_LEVEL == 3:
                    log_content(folder,
                                filename,
                                f"{message}\n\n{change}\n\n{text}")
                    log_flagged_change(change, (folder, filename))
        elif verbose:
            print(f"Skipping - edit count was {user['editcount']} > "
                  + str(config.MAX_EDIT_COUNT))


def make_dirs() -> None:
    """Make the necessary directories and files if they don't exist."""
    if config.LOG_LEVEL >= 1:
        pathlib.Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
        pathlib.Path(
            config.LOG_DIR, config.REVID_LOG
        ).touch(exist_ok=True)
    else:
        return
    if config.LOG_LEVEL >= 2:
        pathlib.Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
        pathlib.Path(config.LOG_DIR,
                     config.FLAGGED_CHANGES_LOG).touch(exist_ok=True)
    if config.LOG_LEVEL >= 3:
        pathlib.Path(config.LOG_DIR,
                     config.CHANGES_SUBDIR).mkdir(parents=True, exist_ok=True)


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


def get_text(revision: int) -> str:
    """Get a revision's text, given its ID #.

    Arg:
      revision:  An int of a MediaWiki oldid.

    Returns:
      A str of the revision's HTML.
    """
    params: dict[str, str | int] = {'format': 'json',
                                    'action': 'parse',
                                    'oldid': revision,
                                    'prop': 'wikitext'}
    r = requests.get(url=_API, params=params)
    try:
        return r.json()['parse']['wikitext']['*']
    # Trying to figure out why this happened once.  Will replace with
    # proper error handling once it's clear why.
    except KeyError:
        print(r.json())
        raise


def get_user(username: str) -> dict[str, Any]:
    """Get a user

    Arg:
      username:  A str of a username

    Returns:
      A dict of user attributes
    """
    params: dict[str, str] = {'format': 'json',
                              'action': 'query',
                              'list': 'users',
                              'ususers': username,
                              'usprop': config.USER_PROPS}
    r = requests.get(url=_API, params=params)
    try:
        return r.json()['query']['users'][0]
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


def log_flagged_change(change: dict[str, Any],
                       changes_path: Optional[Tuple[str, str]] = None) -> None:
    """Log that a change has been flagged.

    Args:
      folder:  A str of the dated subfolder.
      filename:  A str of the filename.
      change:  A dict of the change, taken from the EventStream.
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

    entry = {'change': change}
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
    verbosity = '-v' in sys.argv or '--verbose' in sys.argv
    try:
        run(verbosity)
    except ReadTimeout as e:
        if yesno(f"ReadTimeout with message {e.args[0]}.  Restart?"):
            run(verbosity)
        else:
            raise
