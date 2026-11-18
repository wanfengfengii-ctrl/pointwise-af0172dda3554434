from fractions import Fraction

from measure.catalog import load_revision
from measure.validate import BatchInputError
from tests.support import ArchiveCase, UNIT


class MeasureTests(ArchiveCase):
    def test_registers_two_independent_revisions(self):
        original = self.register('table', [(1, 2, 3), (4, 5, 6)])
        correction = self.register('table', [(1, 2, 3), (7, 5, 6)], parent_rev=original)
        self.assertNotEqual(original, correction)
        self.assertEqual(load_revision(self.archive, original).rows, ((1, 2, 3), (4, 5, 6)))
        current = load_revision(self.archive, correction)
        self.assertEqual(current.parent_rev, original)
        self.assertEqual(current.rows, ((1, 2, 3), (7, 5, 6)))

    def test_named_axis_order_and_exact_readings(self):
        original = self.register('table', [(1, 2, 3), (4, 5, 6)])
        correction = self.register('table', [('3.0', 1, '2/1'), (6, 7, '5.25')],
                                   columns=('Z', 'X', 'Y'), parent_rev=original)
        old_batch = load_revision(self.archive, original)
        new_batch = load_revision(self.archive, correction)
        self.assertEqual(old_batch.rows, ((1, 2, 3), (4, 5, 6)))
        self.assertEqual(new_batch.rows, ((1, 2, 3), (7, Fraction(21, 4), 6)))
        self.assertEqual((new_batch.revision_id, new_batch.parent_rev, new_batch.unit),
                         (correction, original, UNIT))

    def test_missing_axis_rejects_whole_correction(self):
        original = self.register('table', [(1, 2, 3)])
        before = self.counts()
        with self.assertRaises(BatchInputError):
            self.register('table', [(4, 5, 6), (7, 8)], parent_rev=original)
        self.assertEqual(self.counts(), before)
        self.assertEqual(load_revision(self.archive, original).rows, ((1, 2, 3),))

    def test_other_invalid_batches_leave_original_intact(self):
        original = self.register('table', [(1, 2, 3)])
        before = self.counts()
        for options, rows in (
            ({}, []),
            ({'columns': ('X', 'X', 'Z')}, [(1, 2, 3)]),
            ({'columns': ('X', 'Y')}, [(1, 2, 3)]),
            ({}, [(1, None, 3)]),
            ({}, [(1, '', 3)]),
            ({}, [(1, '1/0', 3)]),
            ({}, [(1, True, 3)]),
            ({}, [(1, 0.5, 3)]),
            ({'unit': ''}, [(1, 2, 3)]),
            ({'parent_rev': 999}, [(1, 2, 3)]),
        ):
            with self.subTest(options=options, rows=rows):
                options = {'parent_rev': original, **options}
                with self.assertRaises(BatchInputError):
                    self.register('table', rows, **options)
                self.assertEqual(self.counts(), before)
                self.assertEqual(load_revision(self.archive, original).rows, ((1, 2, 3),))
