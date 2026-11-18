import sqlite3

from measure.catalog import UnknownRevision, insert_revision, load_revision
from measure.parse import parse_batch
from measure.validate import BatchInputError, validate_batch
from publish.store import write_transaction


class BatchWriteError(RuntimeError):
    pass


def register_batch(archive, name, unit, columns, rows, *, parent_rev=None) -> int:
    try:
        parsed = parse_batch(name, unit, columns, rows)
    except ValueError as exc:
        raise BatchInputError(str(exc)) from exc
    batch = validate_batch(parsed)

    try:
        with write_transaction(archive):
            if parent_rev is not None:
                load_revision(archive, parent_rev)
            revision_id = insert_revision(archive, batch, parent_rev)
    except UnknownRevision as exc:
        raise BatchInputError(f'correction parent: {exc}') from exc
    except sqlite3.Error as exc:
        raise BatchWriteError('measurement revision could not be saved') from exc
    return revision_id
