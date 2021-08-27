"""Scan an EventStream of RecentChanges for certain regexes.

Flags matches in the CLI and logs them to a dated subfolder of `logs/`.

Command-line arg:
  -v / --verbose:  Print all changes, even ones that don't match.
"""
import os
import sys

from pywikibot.comms.eventstreams import EventStreams
import requests

import config

_API = f"https://{config.SITE}/w/api.php?"


def run(verbose: bool = False) -> None:
    """Execute the script.

    Arg:
      verbose:  A bool of whether to print events that don't match.
    """
    stream = EventStreams(streams=config.STREAMS)
    stream.register_filter(**config.FILTER)

    for change in stream:
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
            folder = f"logs/{change['meta']['dt'][:10]}"
            filename = "{user} {revision[new]}".format(**change)
            content = f"{message}\n\n{change}\n\n{text}"
            try:
                f = open(f"{folder}/{filename}", 'w+', encoding='utf-8')
            except FileNotFoundError:
                os.makedirs(folder)
                f = open(f"{folder}/{filename}", 'w+', encoding='utf-8')
            with f:
                f.write(content)


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


if __name__ == '__main__':
    run('-v' in sys.argv or '--verbose' in sys.argv)
