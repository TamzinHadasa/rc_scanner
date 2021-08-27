"""Scan an EventStream of RecentChanges for given regexes"""
from pywikibot.comms.eventstreams import EventStreams
import requests

import config

_API = f"https://{config.SITE}/w/api.php?"


def run() -> None:
    """Execute the script."""
    stream = EventStreams(streams=config.STREAMS)
    stream.register_filter(**config.FILTER)

    for change in stream:
        print(
            '{user} {verb} "{title}" at {meta[dt]}.'
            .format(verb=change['type'].removesuffix("e") + "ed", **change)
        )
        text = get_text(change['revision']['new'])
        for r in config.REGEXES:
            if r.search(text):
                print(f"MATCH with regex `{r.pattern}`. "
                      + change['meta']['uri'])
                with open("logs/{user} {revision[new]}".format(**change),
                          'w+',
                          encoding='utf-8') as f:
                    f.write(f"{r.pattern}\n\n{change}\n\n{text}")


def get_text(revision: int) -> str:
    """Get a revision's text, given its ID #.

    Args:
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
    run()
