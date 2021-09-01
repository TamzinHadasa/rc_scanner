"""Holds Filter class."""
import re
from typing import Any, Optional

from pywikibot.comms.eventstreams import EventStreams

try:
    import config
except ImportError:
    # To allow for linting of the repo by Github Action, and to ensure
    # through that that the example file is up to date.
    from examples import config  # type: ignore
from utils import ConfigError
import flaglog


class Filter:  # pylint: disable=too-many-instance-attributes
    """Object to filter the EventStream and its output.

    Attributes:
      name:  A str of the filter's name.  This is the name to refer to
        it by from the command line, and the name that will appear in
        `flagged_changes.json`.
      apis:  A list of strs of API URLs for all sites the filter is
        scanning.
    """

    def __init__(self,  # pylint: disable=too-many-arguments
                 *,
                 name: str,
                 sites: list[str],
                 streamfilter: dict[str, Any],
                 streams: list[str],
                 max_edits: Optional[int],
                 regexes: list[re.Pattern[str]],
                 skip_repeats: bool = config.LOG_LEVEL >= 2) -> None:
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
        if skip_repeats and config.LOG_LEVEL < 2:
            raise ConfigError("`skip_repeats` can only be set to True if "
                              "`config.LOG_LEVEL` is >= 2")
        self.name = name
        self.apis = {i: f"https://{i}/w/api.php?" for i in sites}
        streamfilter['server_name'] = sites
        self.max_edits = max_edits
        self._streamfilter = streamfilter
        self._streams = streams
        self._regexes = regexes
        self._skip_repeats = skip_repeats

    def __repr__(self) -> str:
        sites = self._streamfilter['server_name']
        streamfilter = {k: v for k, v in self._streamfilter.items()
                        if k != 'server_name'}
        return ("Filter("
                + ", ".join(repr(i) for i in [
                    self.name, sites, streamfilter, self._streams,
                    self.max_edits, self._regexes, self._skip_repeats
                ])
                + ")")

    def count_under_max(self, editcount: int) -> bool:
        """Compare an edit count to `max_edits`.

        If `max_edits` is None, always returns True.

        Arg:
          editcount:  An int of a user's edit count.

        Returns:
          A bool, with True indicating either that the edit count was
          under `max_edits`, or that `max_edits` is None.
        """
        return self.max_edits is None or editcount <= self.max_edits

    def page_is_repeat(self, pagename: str) -> bool:
        """Check whether a page is already in the flagged changes log.

        If `_skip_repeats` is False, always returns False.

        Arg:
          pagename:  A page's name.

        Returns:
          A bool, with True indicating either that the page is in the
          flagged changes log or that `skip_repeats` is False."""
        return (self._skip_repeats
                and pagename in [i['change']['title'] for i in flaglog.read()])

    def create_stream(self) -> EventStreams:
        """Create an EventStreams object from the Filter's attributes."""
        stream = EventStreams(streams=self._streams)
        stream.register_filter(**self._streamfilter)
        return stream

    def search_regexes(self, text: str) -> list[re.Pattern[str]]:
        """Get a list of regexes that contain `text`"""
        return [i for i in self._regexes if i.search(text)]
