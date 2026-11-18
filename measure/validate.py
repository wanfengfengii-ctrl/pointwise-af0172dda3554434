from dataclasses import dataclass
from fractions import Fraction

from measure.parse import ParsedBatch


AXES = ('X', 'Y', 'Z')
Vector = tuple[Fraction, Fraction, Fraction]


class BatchInputError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedBatch:
    name: str
    unit: str
    rows: tuple[Vector, ...]


def validate_batch(batch: ParsedBatch) -> ValidatedBatch:
    if (len(batch.columns) != len(AXES)
            or any(not isinstance(axis, str) for axis in batch.columns)
            or set(batch.columns) != set(AXES)):
        raise BatchInputError('columns must contain X, Y, and Z exactly once')
    if not batch.rows:
        raise BatchInputError('a batch must contain at least one row')

    x, y, z = (batch.columns.index(axis) for axis in AXES)
    normalized = []
    for number, row in enumerate(batch.rows, start=1):
        if len(row) != len(AXES):
            raise BatchInputError(f'row {number} must contain all three axis values')
        normalized.append((row[x], row[y], row[z]))
    return ValidatedBatch(batch.name, batch.unit, tuple(normalized))
