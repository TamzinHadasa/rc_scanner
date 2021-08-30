"""Configuration data for `scanner`."""
import re

from classes import Filter

# 0:  Log nothing.
# 1:  Log revids to `REVID_LOG`.
# 2:  Also log flagged changes to `FLAGGED_CHANGES`.
# 3:  Also log content of flagged changes to dated subfolder
#     of `LOG_DIR`.
LOG_LEVEL = 3
# Main log directory.
LOG_DIR = 'logs'
# Subdirectory of `LOG_DIR` for copies of changes.
CHANGES_SUBDIR = 'changes'
# File in `LOG_DIR` to list metadata about flagged changes in.
FLAGGED_CHANGES_LOG = 'flagged_changes.json'
# File in `REVID_LOG` to list flagged revids in.
REVID_LOG = 'revids.txt'


# See <https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams>
# and <https://doc.wikimedia.org/pywikibot/master/api_ref/pywikibot.comms.html#module-pywikibot.comms.eventstreams>
# for more information on configuring `sites`, `streamfilter`, and
# `streams`.
#
# See <https://www.mediawiki.org/wiki/Help:Namespaces#Localisation> for
# namespace numbers, or your wiki's internal documentation for ones
# not listed there.
filters = {i.name: i for i in [
    # BEGIN FILTER LIST HERE.
    Filter(
        name='minors',
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
            (r"\buserbox(e[ns])?\b", re.I),
            (r"some other regex; use 0 for no flags", 0)
        ]
    )
    # END FILTER LIST HERE.
]}
