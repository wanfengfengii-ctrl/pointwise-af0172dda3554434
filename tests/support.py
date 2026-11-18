import unittest
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

from measure.revisions import register_batch
from measure.validate import AXES
from publish.store import initialize_archive, open_archive
from train.freeze import fit


UNIT = 'mm/s'
ZERO = (0, 0, 0)
X = (1, 0, 0)
Y = (0, 1, 0)
OFFSET = (2, -3, Fraction(1, 2))


def shifted(center, vector):
    return tuple(a + b for a, b in zip(center, vector, strict=True))


def opposite(vector):
    return tuple(-value for value in vector)


def training_rows(center, *directions):
    return [shifted(center, vector)
            for direction in directions for vector in (direction, opposite(direction))]


class ArchiveCase(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'lab.sqlite3'
        self.archive = None
        self.addCleanup(self.close_archive)
        self.reopen()

    def close_archive(self):
        if self.archive is not None:
            self.archive.close()
            self.archive = None

    def reopen(self):
        self.close_archive()
        self.archive = open_archive(self.path)
        initialize_archive(self.archive)

    def register(self, name, rows, *, columns=AXES, unit=UNIT, parent_rev=None):
        return register_batch(self.archive, name, unit, columns, rows, parent_rev=parent_rev)

    def counts(self):
        tables = ('batch_revisions', 'fits', 'fit_links', 'reports', 'report_links')
        return tuple(self.archive.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                     for table in tables)

    def fit_and_conditions(self, center=ZERO, axes=(X, Y), *, unique=False):
        directions = axes[:1] if unique else axes
        source = self.register('training', training_rows(center, *directions))
        fit_id = fit(self.archive, source, 1 if unique else '1/2')
        left = self.register('left condition', [shifted(center, axes[0])])
        right = self.register('right condition', [shifted(center, axes[1])])
        return source, fit_id, left, right
