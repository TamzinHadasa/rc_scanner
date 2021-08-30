"""Holds classes for use elsewhere."""
import re
from typing import Any, TypedDict

from pywikibot.comms.eventstreams import EventStreams


class QueryRaceCondition(Exception):
    """Error for race conditions while querying the API."""


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


class Filter:
    """Object to filter the EventStream and its output.

    Attributes:
      name:  A str of the filter's name.  This is the name to refer to
        it by from the command line, and the name that will appear in
        `flagged_changes.json`.
      apis:  A list of strs of API URLs for all sites the filter is
        scanning.
    """

    def __init__(self,  # pylint: disable=too-many-arguments
                 name: str,
                 sites: list[str],
                 streamfilter: dict[str, Any],
                 streams: list[str],
                 regexes: list[tuple[str, re.RegexFlag | int]]) -> None:
        """Initialize a Filter.

        Args:
          name:  A str to serve as the Filter's name.
          sites:  A list of strs of sites' names, not including
            "https://".
          streamfilter:  A dict where every key is one found in Change,
            and every value is either an object of the correct type or
            an iterable of such objects.  See
            `EventStreams.register_filter` documentation for more
            information.
          streams:  A list of strs of streams to follow.
          regexes:  A list of 2-tuples where the first item is a string
            that will compile to a regex and the second is a regex flag
            or a sum thereof.
        """
        self.name = name
        self.apis = {i: f"https://{i}/w/api.php?" for i in sites}
        streamfilter['server_name'] = sites
        self._streamfilter = streamfilter
        self._streams = streams
        self._regexes = [re.compile(i, flags=j) for i, j in regexes]

    def __repr__(self) -> str:
        return (f"Filter({self._streamfilter['server_name']}, "
                + str({k: v for k, v in self._streamfilter.items()
                       if k != 'server_name'})
                + f", {self._streams}, {self._regexes})")

    def create_stream(self) -> EventStreams:
        """Create an EventStreams object from the Filter's attributes."""
        stream = EventStreams(streams=self._streams)
        stream.register_filter(**self._streamfilter)
        return stream

    def search_regexes(self, text: str) -> list[re.Pattern[str]]:
        """Get a list of regexes that contain `text`"""
        return [i for i in self._regexes if i.search(text)]
