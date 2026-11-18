import json
import sqlite3
from dataclasses import dataclass
from fractions import Fraction

from measure.validate import Vector
from publish.codec import decode_fit_payload, encode_fit_payload
from publish.links import load_fit_link, result_key


class UnknownFit(LookupError):
    pass


@dataclass(frozen=True)
class FitRecord:
    fit_id: str
    train_rev: int
    unit: str
    center: Vector
    largest: Fraction
    basis: tuple[Vector, ...]


def insert_fit(archive: sqlite3.Connection, unit, center, largest, basis) -> int:
    payload = encode_fit_payload(unit, center, largest, basis)
    cursor = archive.execute(
        'INSERT INTO fits (payload) VALUES (?)',
        (json.dumps(payload, separators=(',', ':')),),
    )
    return cursor.lastrowid


def load_fit(archive: sqlite3.Connection, fit_id: str) -> FitRecord:
    key = result_key(fit_id, 'fit')
    row = archive.execute('SELECT payload FROM fits WHERE fit_id = ?', (key,)).fetchone()
    if row is None:
        raise UnknownFit(f'unknown fit {fit_id!r}')
    train_rev = load_fit_link(archive, key)
    fields = decode_fit_payload(json.loads(row[0]))
    return FitRecord(fit_id=fit_id, train_rev=train_rev, **fields)
