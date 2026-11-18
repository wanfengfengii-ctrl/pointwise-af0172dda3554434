import sqlite3
from contextlib import contextmanager

from measure.catalog import initialize_catalog


_RESULT_SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS fits (
           fit_id INTEGER PRIMARY KEY,
           payload TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS fit_links (
           fit_id INTEGER PRIMARY KEY REFERENCES fits(fit_id),
           train_rev INTEGER NOT NULL REFERENCES batch_revisions(revision_id)
       )''',
    '''CREATE TABLE IF NOT EXISTS reports (
           report_id INTEGER PRIMARY KEY,
           payload TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS report_links (
           report_id INTEGER PRIMARY KEY REFERENCES reports(report_id),
           fit_id INTEGER NOT NULL REFERENCES fits(fit_id),
           left_rev INTEGER NOT NULL REFERENCES batch_revisions(revision_id),
           right_rev INTEGER NOT NULL REFERENCES batch_revisions(revision_id)
       )''',
)


def open_archive(path) -> sqlite3.Connection:
    archive = sqlite3.connect(path, isolation_level=None)
    try:
        archive.execute('PRAGMA foreign_keys = ON')
    except BaseException:
        archive.close()
        raise
    return archive


@contextmanager
def write_transaction(archive: sqlite3.Connection):
    archive.execute('BEGIN IMMEDIATE')
    try:
        yield
        archive.commit()
    except BaseException:
        if archive.in_transaction:
            archive.rollback()
        raise


def initialize_archive(archive: sqlite3.Connection) -> None:
    with write_transaction(archive):
        initialize_catalog(archive)
        for statement in _RESULT_SCHEMA:
            archive.execute(statement)
