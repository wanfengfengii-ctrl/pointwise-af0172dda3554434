import re
import sqlite3


class ResultLinkError(LookupError):
    pass


def result_key(identifier, kind: str) -> int:
    pattern = rf'{kind}:([1-9][0-9]{{0,18}})'
    match = re.fullmatch(pattern, identifier) if isinstance(identifier, str) else None
    if match:
        key = int(match[1])
        if key < 2**63:
            return key
    raise ValueError(f'expected a {kind} identifier, got {identifier!r}')


def record_fit_link(archive: sqlite3.Connection, key: int, train_rev: int) -> None:
    archive.execute('INSERT INTO fit_links (fit_id, train_rev) VALUES (?, ?)', (key, train_rev))


def record_report_links(archive: sqlite3.Connection, key: int, fit_key: int,
                        left_rev: int, right_rev: int) -> None:
    archive.execute(
        'INSERT INTO report_links (report_id, fit_id, left_rev, right_rev) VALUES (?, ?, ?, ?)',
        (key, fit_key, left_rev, right_rev),
    )


def load_fit_link(archive: sqlite3.Connection, key: int) -> int:
    row = archive.execute(
        '''SELECT l.train_rev FROM fit_links AS l
           JOIN batch_revisions AS train ON train.revision_id = l.train_rev
           WHERE l.fit_id = ?''',
        (key,),
    ).fetchone()
    if row is None:
        raise ResultLinkError(f'fit:{key} has no valid training link')
    return row[0]


def load_report_links(archive: sqlite3.Connection, key: int) -> tuple[int, int, int]:
    row = archive.execute(
        '''SELECT l.fit_id, l.left_rev, l.right_rev FROM report_links AS l
           JOIN fits AS f ON f.fit_id = l.fit_id
           JOIN batch_revisions AS lhs ON lhs.revision_id = l.left_rev
           JOIN batch_revisions AS rhs ON rhs.revision_id = l.right_rev
           WHERE l.report_id = ?''',
        (key,),
    ).fetchone()
    if row is None:
        raise ResultLinkError(f'report:{key} has no valid fit and condition links')
    return row
