"""Filter objects for the scanner to use."""
# COPY THIS TO THE MAIN DIRECTORY AND MODIFY AS NEEDED.
import re

from filter_ import Filter

# See <https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams>
# and <https://doc.wikimedia.org/pywikibot/master/api_ref/pywikibot.comms.html#module-pywikibot.comms.eventstreams>
# for more information on configuring `sites`, `streamfilter`, and
# `streams`.
#
# See <https://www.mediawiki.org/wiki/Help:Namespaces#Localisation> for
# namespace numbers, or your wiki's internal documentation for ones
# not listed there.
filterlist = {i.name: i for i in [
    # BEGIN FILTER LIST HERE.
    Filter(
        name='example',
        # Not including "https://"
        sites=["en.wikipedia.org"],
        streamfilter={'type': ('edit', 'create'),
                      'bot': False,
                      'namespace': 2},  # `User:`
        streams=['recentchange', 'revision-create'],
        # Skip users with more edits than this. None to disable.
        max_edits=None,
        # List as many regexes as you want, although note that runtime
        # increases linearly with this list.  If a regex takes no flags,
        # use a 0 as the tuple's second value.
        regexes=[
            re.compile(r"\buserbox(e[ns])?\b", re.I),
            re.compile(r"some other regex")
        ]
    )
    # END FILTER LIST HERE.
]}
