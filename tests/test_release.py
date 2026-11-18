from fractions import Fraction

from audit.decision import report
from measure.catalog import load_revision
from publish.commit import PublicationError
from review.handoff import read_result
from review.lookup import ResultReadError
from tests.support import ArchiveCase, OFFSET


class ReleaseTests(ArchiveCase):
    def test_report_body_and_links_roll_back_together(self):
        _, fit_id, left, right = self.fit_and_conditions(OFFSET)
        old_id, passed = report(self.archive, fit_id, left, right, '1/2', '1/2')
        self.assertIs(passed, True)
        old_view = read_result(self.archive, 'report', old_id)
        before = self.counts()
        staged = []

        def fail_after_write():
            owners = self.archive.execute(
                'SELECT fit_id, left_rev, right_rev FROM report_links ORDER BY report_id DESC LIMIT 1'
            ).fetchone()
            staged.append((self.counts(), owners))
            raise RuntimeError('report write interrupted')

        with self.assertRaisesRegex(PublicationError, 'report publication failed'):
            report(self.archive, fit_id, right, left, '3/4', '3/4', before_commit=fail_after_write)
        expected_counts = before[:3] + (before[3] + 1, before[4] + 1)
        self.assertEqual(staged, [(expected_counts, (int(fit_id.split(':')[1]), right, left))])
        self.reopen()
        self.assertEqual(self.counts(), before)
        self.assertEqual(read_result(self.archive, 'report', old_id), old_view)
        new_id, passed = report(self.archive, fit_id, right, left, '3/4', '3/4')
        self.assertNotEqual(old_id, new_id)
        self.assertIs(passed, False)
        self.assertIs(read_result(self.archive, 'report', new_id)['passed'], False)

    def test_archive_reopen_after_source_corrections(self):
        train, fit_id, left, right = self.fit_and_conditions(OFFSET)
        report_id, passed = report(self.archive, fit_id, left, right, '1/2', '1/2')
        self.assertIs(passed, True)
        fit_before = read_result(self.archive, 'fit', fit_id)
        report_before = read_result(self.archive, 'report', report_id)
        train_new = self.register('training', [(4, -3, '1/2'), (0, -3, '1/2')], parent_rev=train)
        right_new = self.register('right condition', [(2, -1, '1/2')], parent_rev=right)
        before_reopen = self.counts()

        for _ in range(2):
            self.reopen()
            self.assertEqual(self.counts(), before_reopen)
            frozen = read_result(self.archive, 'fit', fit_id)
            review = read_result(self.archive, 'report', report_id)
            self.assertEqual(frozen, fit_before)
            self.assertEqual(review, report_before)
            self.assertEqual((frozen['train_rev'], frozen['center']), (train, ['2/1', '-3/1', '1/2']))
            self.assertEqual((review['fit_id'], review['train_rev'], review['left_rev'], review['right_rev']),
                             (fit_id, train, left, right))
            self.assertEqual((review['lo_left'], review['lo_right'], review['passed']), ('1/2', '1/2', True))
            self.assertEqual(review['center'], ['2/1', '-3/1', '1/2'])
            self.assertEqual(review['energy_unit'], '(mm/s)^2')
            self.assertEqual(load_revision(self.archive, train).rows[0], (3, -3, Fraction(1, 2)))
            self.assertEqual(load_revision(self.archive, right).rows, ((2, -2, Fraction(1, 2)),))
            self.assertEqual(load_revision(self.archive, train_new).rows[0], (4, -3, Fraction(1, 2)))
            self.assertEqual(load_revision(self.archive, right_new).rows, ((2, -1, Fraction(1, 2)),))
            self.assertEqual(load_revision(self.archive, right_new).parent_rev, right)

    def test_result_lookup_rejects_unknown_ids_and_mismatched_types(self):
        _, fit_id, left, right = self.fit_and_conditions()
        report_id, _ = report(self.archive, fit_id, left, right, 0, 0)
        before = self.counts()
        for kind, identifier, reason in (
            ('fit', 'fit:999', 'unknown fit'),
            ('report', 'report:999', 'unknown report'),
            ('fit', report_id, 'expected a fit identifier'),
            ('report', fit_id, 'expected a report identifier'),
            ('batch', fit_id, 'unknown result kind'),
        ):
            with self.subTest(kind=kind, identifier=identifier):
                with self.assertRaisesRegex(ResultReadError, reason):
                    read_result(self.archive, kind, identifier)
                self.assertEqual(self.counts(), before)
