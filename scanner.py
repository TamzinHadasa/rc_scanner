"""Scan an EventStream of RecentChanges for certain regexes.

Flags matches in the CLI and logs them to a dated subfolder of `logs/`.

Command-line arg:
  -v / --verbose:  Print all changes, even ones that don't match.
"""
import datetime as dt
import json
import os
from re import T
import shutil
import sys
from json.decoder import JSONDecodeError
from pathlib import Path

import requests
from pywikibot.comms.eventstreams import EventStreams

import config

_API = f"https://{config.SITE}/w/api.php?"
_EDITCOUNT = config.SETTINGS['edit_count']
_LOGLEVEL = config.SETTINGS['log_level']
_LOGDIR = config.SETTINGS['log_dir']


def run(verbose: bool = False) -> None:
    """Execute the script.

    Arg:
      verbose:  A bool of whether to print events that don't match.
    """
    stream = EventStreams(streams=config.STREAMS)
    stream.register_filter(**config.FILTER)

    if verbose:
        print('Current settings:')
        print('Verbose -> True')
        for setting in config.SETTINGS:
            print(setting, '->', config.SETTINGS[setting])
        print('\n')

    if _LOGLEVEL >= 3:
        user_logging_enabled = True
        flagged_changes_enabled = True
        revid_logging_enabled = True
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['user_log_dir']
        ).mkdir(
            parents=True,
            exist_ok=True
        )
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['flagged_changes_log']
        ).touch(
            exist_ok=True
        )
        Path(
            _LOGDIR
        ).mkdir(
            parents=True,
            exist_ok=True
        )
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['revid_log']
        ).touch(
            exist_ok=True
        )
    elif _LOGLEVEL >= 2:
        flagged_changes_enabled = True
        revid_logging_enabled = True
        Path(
            _LOGDIR
        ).mkdir(
            parents=True,
            exist_ok=True
        )
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['flagged_changes_log']
        ).touch(
            exist_ok=True
        )
        Path(
            _LOGDIR
        ).mkdir(
            parents=True,
            exist_ok=True
        )
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['revid_log']
        ).touch(
            exist_ok=True
        )
    elif _LOGLEVEL >= 1:
        revid_logging_enabled = True
        Path(
            _LOGDIR
        ).mkdir(
            parents=True,
            exist_ok=True
        )
        Path(
            _LOGDIR,
            '/',
            config.SETTINGS['revid_log']
        ).touch(
            exist_ok=True
        )
    else:
        user_logging_enabled = False
        flagged_changes_enabled = False
        revid_logging_enabled = False

    # Inform user we are now waiting..
    print('Waiting for first edit..')

    for change in stream:
        user = get_user(change['user'])

        # If edit count filter is disabled, or if less than filter...
        if _EDITCOUNT == 0 or user['editcount'] < _EDITCOUNT:
            text = get_text(change['revision']['new'])
            hits = []
            for r in config.REGEXES:
                if r.search(text):
                    hits.append(r)
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

                folder = f"{_LOGDIR}/{config.SETTINGS['user_log_dir']}/{change['meta']['dt'][:10]}"
                new_revision = "{revision[new]}".format(**change)
                username = change['user']
                # Colons are invalid in most filenames
                filename = f"{username}_{new_revision}".replace(":", "-")
                content = f"{message}\n\n{change}\n\n{text}"

                if revid_logging_enabled:
                    with open(
                        f"{_LOGDIR}/{config.SETTINGS['revid_log']}",
                        "a",
                        encoding='utf-8'
                    ) as f:
                        f.write(f"{new_revision}\n")

                if user_logging_enabled:
                    try:
                        f = open(f"/{filename}", 'w+', encoding='utf-8')
                    except FileNotFoundError:
                        Path(folder).mkdir(parents=True, exist_ok=True)
                        f = open(f"/{filename}", 'w+', encoding='utf-8')
                    with f:
                        f.write(content)
                
                if flagged_changes_enabled:
                    with open(
                        f"{_LOGDIR}/{config.SETTINGS['flagged_changes_log']}",
                        'r',
                        encoding='utf-8'
                    ) as flaglog:
                        try:
                            data = json.load(flaglog)
                        except JSONDecodeError:
                            # No safeguards here
                            if verbose:
                                print(f"Failed to read {_LOGDIR}/{config.SETTINGS['flagged_changes_log']}")
                                if yesno("Reset data and continue") is False:
                                    exit()
                            data = []
                        
                        data.append({'change': change,
                                    'log': {'folder': folder,
                                            'file': filename}})
                        assert data  # Something is terribly wrong.

                        # Now "close and flush", and open for writing

                    with open(
                        f"{_LOGDIR}/{config.SETTINGS['flagged_changes_log']}",
                        'w',
                        encoding='utf-8'
                    ) as flaglog:
                        json.dump(data, flaglog, indent=4)
        else:
            if verbose:
                print(f"Skipping - edit count was {user['editcount']} > {_EDITCOUNT}")


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
    except KeyError:
        print(r.json())
        raise


def get_user(username: str) -> dict:
    """Get a user

    Arg:
      username:  A str of a username

    Returns:
      dict
    """
    params: dict[str, str | int] = {'format': 'json',
                                    'action': 'query',
                                    'list': 'users',
                                    'ususers': username,
                                    'usprop': config.SETTINGS['user_props']}
    r = requests.get(url=_API, params=params)
    try:
        return r.json()['query']['users'][0]
    except KeyError:
        print(r.json())
        raise


def yesno(question: str) -> bool:
    """Prompt a y/n question to the user

    Arg:
      question:  The question to ask

    Returns:
      bool
    """
    prompt = f'{question} ? (y/n): '
    ans = input(prompt).strip().lower()
    if ans not in ['y', 'n']:
        print(f'{ans} is invalid, please try again...')
        return yesno(question)
    if ans == 'y':
        return True
    return False


if __name__ == '__main__':
    run('-v' in sys.argv or '--verbose' in sys.argv)
