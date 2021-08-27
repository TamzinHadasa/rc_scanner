"""Configuration data for `scanner`.

Modify as needed and then save as `config.py`.
"""
import re

# NOT including "https" etc.
SITE = "en.wikipedia.org"
# As many as you want, although note that runtime increases linearly
# with this list.
REGEXES = [re.compile(i, flags=j) for i, j in [
    (r"\buserbox(e[ns])?\b", re.I),
    (r"some other regex; use 0 for no flags", 0)
]]
# See <https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams>
# and <https://doc.wikimedia.org/pywikibot/master/api_ref/pywikibot.comms.html#module-pywikibot.comms.eventstreams>
# for more information on configuring FILTER and STREAMS.
FILTER = {
    'server_name': SITE,
    'type': ('edit', 'create'),
    'bot': False,
    # <https://www.mediawiki.org/wiki/Help:Namespaces#Localisation> for
    # namespace numbers, or your wiki's internal documentation for ones
    # not listed there.
    'namespace': 0
}

# Skip users with more edits than this. `None` to disable.
MAX_EDIT_COUNT = None
# 0:  Log nothing.
# 1:  Log revids to `REVID_LOG`.
# 2:  Also log flagged changes to `FLAGGED_CHANGES`.
# 3:  Also log content of flagged changes to dated subfolder
#     of `LOG_DIR`.
LOG_LEVEL = 3
USER_PROPS = 'blockinfo|groups|editcount'  # User properties to return
LOG_DIR = 'logs'  # Main log directory
FLAGGED_CHANGES_LOG = 'flagged_changes.json'
REVID_LOG = 'revids.txt'
STREAMS = ['recentchange', 'revision-create']
