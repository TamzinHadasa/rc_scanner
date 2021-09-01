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
    with _manager('r') as logfile:
        return json.load(logfile)


def write(data: list[FlagLogEntry]) -> None:
    assert data, "Tried to save data but data was empty."
    with _manager('w') as logfile:
        json.dump(data, logfile, indent=4)


def init() -> None:
    with _manager('r+') as logfile:
        if not logfile.read():
            logfile.write('[]')


def append(entry: FlagLogEntry) -> None:
    data = read()
    data.append(entry)
    write(data)
