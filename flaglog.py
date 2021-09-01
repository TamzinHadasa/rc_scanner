"""Interacts with the log of flagged changes."""
from contextlib import contextmanager
import json
from typing import Generator, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import OpenTextMode
else:
    OpenTextMode = str
# pylint: disable=wrong-import-position
import config
from utils import FlagLogEntry


@contextmanager
def _manager(mode: OpenTextMode) -> Generator[TextIO, None, None]:  # pylint: disable=used-before-assignment
    yield open(f"{config.LOG_DIR}/{config.FLAGGED_CHANGES_LOG}",
               mode,
               encoding='utf-8')


def read() -> list[FlagLogEntry]:
    """Read the flagged-changes log as JSON.

    Returns:
      A list of FlagLogEntry objects.
    """
    with _manager('r') as logfile:
        return json.load(logfile)


def write(data: list[FlagLogEntry]) -> None:
    """Write JSON to the flagged-changes log.

    CAUTION: Overwrites existing contents.

    Arg:
      data:  A list of FlagLogEntry objects to overwrite the flagged-
        changes log with.
    """
    assert data, "Tried to save data but data was empty."
    with _manager('w') as logfile:
        json.dump(data, logfile, indent=4)


def init() -> None:
    """Initialize the flagged-changes log as an empty list."""
    with _manager('r+') as logfile:
        if not logfile.read():
            logfile.write('[]')


def append(entry: FlagLogEntry) -> None:
    """Add a FlagLogEntry to the flagged-changes log.

    Arg:
      entry:  A FlagLogEntry to append.
    """
    data = read()
    data.append(entry)
    write(data)
