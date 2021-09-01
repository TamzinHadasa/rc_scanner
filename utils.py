"""Holds classes for use elsewhere."""
from typing import TypedDict


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


class FlagLogEntry(TypedDict):
    """Structure of an entry in the flagged changes log."""
    filter: str
    change: Change
    log: dict[str, str]


class ConfigError(Exception):
    """Error for invalid configuration."""


class QueryRaceCondition(Exception):
    """Error for race conditions while querying the API."""


def yesno(question: str) -> bool:
    """Asks a y/n question to the user.

    If the user gives an invalid answer, calls itself to ask again

    Arg:
      question:  The question to ask.

    Returns:
      A bool corresponding to their answer.
    """
    prompt = f'{question} '
    ans = input(prompt).strip().lower()
    if ans not in ('y', 'n'):
        print(f'{ans} is invalid.  Please try again.')
        return yesno(question)
    return ans == 'y'
