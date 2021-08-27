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
STREAMS = ['recentchange', 'revision-create']
