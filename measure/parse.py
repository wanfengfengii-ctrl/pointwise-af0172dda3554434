from collections.abc import Mapping, Set
from dataclasses import dataclass
from fractions import Fraction

from measure.rationals import parse_rational


@dataclass(frozen=True)
class ParsedBatch:
    name: str
    unit: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Fraction, ...], ...]


def _ordered_items(value, label):
    if isinstance(value, (str, bytes, bytearray, Mapping, Set)):
        raise ValueError(f'{label} must be an ordered sequence')
    try:
        return tuple(value)
    except TypeError as exc:
        raise ValueError(f'{label} must be an ordered sequence') from exc


def _required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value.strip()


def parse_batch(name, unit, columns, rows) -> ParsedBatch:
    name = _required_text(name, 'batch name')
    unit = _required_text(unit, 'measurement unit')
    columns = _ordered_items(columns, 'columns')
    parsed_rows = []
    for number, row in enumerate(_ordered_items(rows, 'rows'), start=1):
        try:
            values = _ordered_items(row, 'row')
            parsed_rows.append(tuple(parse_rational(value) for value in values))
        except ValueError as exc:
            raise ValueError(f'row {number}: {exc}') from exc
    return ParsedBatch(name, unit, columns, tuple(parsed_rows))
