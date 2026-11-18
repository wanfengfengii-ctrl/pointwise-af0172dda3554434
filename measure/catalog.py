import json
import sqlite3
from dataclasses import dataclass

from measure.rationals import format_rational, parse_rational
from measure.validate import ValidatedBatch, Vector


class UnknownRevision(LookupError):
    pass


@dataclass(frozen=True)
class BatchRevision:
    revision_id: int
    name: str
    unit: str
    parent_rev: int | None
    rows: tuple[Vector, ...]


def initialize_catalog(archive: sqlite3.Connection) -> None:
    archive.execute(
        '''CREATE TABLE IF NOT EXISTS batch_revisions (
               revision_id INTEGER PRIMARY KEY,
               name TEXT NOT NULL,
               unit TEXT NOT NULL,
               parent_rev INTEGER REFERENCES batch_revisions(revision_id),
               rows_json TEXT NOT NULL
           )'''
    )


def insert_revision(archive: sqlite3.Connection, batch: ValidatedBatch, parent_rev: int | None) -> int:
    rows = [[format_rational(value) for value in row] for row in batch.rows]
    cursor = archive.execute(
        'INSERT INTO batch_revisions (name, unit, parent_rev, rows_json) VALUES (?, ?, ?, ?)',
        (batch.name, batch.unit, parent_rev, json.dumps(rows, separators=(',', ':'))),
    )
    return cursor.lastrowid


def load_revision(archive: sqlite3.Connection, revision_id: int) -> BatchRevision:
    if (not isinstance(revision_id, int) or isinstance(revision_id, bool)
            or not 0 < revision_id < 2**63):
        raise UnknownRevision(f'invalid measurement revision {revision_id!r}')
    record = archive.execute(
        'SELECT name, unit, parent_rev, rows_json FROM batch_revisions WHERE revision_id = ?',
        (revision_id,),
    ).fetchone()
    if record is None:
        raise UnknownRevision(f'unknown measurement revision {revision_id}')
    name, unit, parent_rev, payload = record
    rows = tuple(tuple(parse_rational(value) for value in row) for row in json.loads(payload))
    return BatchRevision(revision_id, name, unit, parent_rev, rows)
