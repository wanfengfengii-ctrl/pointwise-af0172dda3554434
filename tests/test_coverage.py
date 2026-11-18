from fractions import Fraction

from audit.decision import report
from audit.request import CoverageInputError
from review.handoff import read_result
from tests.support import ArchiveCase, OFFSET, X, shifted


class CoverageTests(ArchiveCase):
    def _verdicts(self, fit_id, left, right, thresholds):
        return [report(self.archive, fit_id, left, right, lo_left, lo_right)[1]
                for lo_left, lo_right in thresholds]

    def test_joint_axis_coverage(self):
        source, fit_id, left, right = self.fit_and_conditions()
        thresholds = [('1/2', '1/2'), ('3/4', '3/4')]
        releases = [report(self.archive, fit_id, left, right, *pair) for pair in thresholds]
        self.assertEqual([passed for _, passed in releases], [True, False], 'JOINT_AXIS_COVERAGE')
        for (report_id, passed), (lo_left, lo_right) in zip(releases, thresholds, strict=True):
            view = read_result(self.archive, 'report', report_id)
            self.assertEqual((view['fit_id'], view['train_rev'], view['left_rev'], view['right_rev']),
                             (fit_id, source, left, right))
            self.assertEqual((view['lo_left'], view['lo_right']), (lo_left, lo_right))
            self.assertIs(view['passed'], passed)

    def test_translated_cases_use_the_training_center(self):
        _, fit_id, left, right = self.fit_and_conditions(OFFSET)
        self.assertEqual(self._verdicts(fit_id, left, right, [('1/2', '1/2'), ('3/4', '3/4')]),
                         [True, False])

    def test_oblique_metric_preserves_physical_coverage(self):
        p = tuple(Fraction(value, 3) for value in (2, 1, -2))
        q = tuple(Fraction(value, 3) for value in (2, -2, 1))
        _, fit_id, left, right = self.fit_and_conditions(OFFSET, (p, q))
        frozen = read_result(self.archive, 'fit', fit_id)
        self.assertEqual(frozen['basis'], [['-2/1', '1/1', '0/1'], ['-2/1', '0/1', '1/1']])
        self.assertEqual(self._verdicts(fit_id, left, right, [('1/2', '1/2'), ('3/4', '3/4')]),
                         [True, False])

    def test_algebraic_direction_on_both_closed_thresholds(self):
        _, fit_id, left, right = self.fit_and_conditions()
        self.assertEqual(self._verdicts(fit_id, left, right, [('1/3', '2/3'), ('11/30', '2/3')]),
                         [True, False])

    def test_isolated_projection_outside_the_finite_coordinate_chart(self):
        _, fit_id, left, right = self.fit_and_conditions()
        self.assertEqual(self._verdicts(fit_id, left, right, [(0, 1), (0, '101/100')]), [True, False])

    def test_zero_form_does_not_exclude_a_finite_double_root(self):
        _, fit_id, _, _ = self.fit_and_conditions()
        zero = self.register('quiet condition', [(0, 0, 0)])
        diagonal = self.register('diagonal condition', [(1, 1, 0)])
        self.assertEqual(self._verdicts(fit_id, zero, diagonal, [(0, 2), (0, '201/100')]),
                         [True, False])

    def test_negative_threshold_leaves_no_report(self):
        _, fit_id, left, right = self.fit_and_conditions()
        before = self.counts()
        with self.assertRaisesRegex(CoverageInputError, 'left threshold'):
            report(self.archive, fit_id, left, right, -1, 0)
        self.assertEqual(self.counts(), before)

    def test_unknown_or_incompatible_bindings_leave_no_report(self):
        _, fit_id, left, right = self.fit_and_conditions()
        incompatible = self.register('different unit', [(1, 0, 0)], unit='cm/s')
        before = self.counts()
        for arguments, reason in (
            (('fit:999', left, right, 0, 0), 'fit source'),
            ((fit_id, 999, right, 0, 0), 'condition source'),
            ((fit_id, left, 999, 0, 0), 'condition source'),
            ((fit_id, incompatible, right, 0, 0), 'left condition unit'),
            ((fit_id, left, incompatible, 0, 0), 'right condition unit'),
            ((fit_id, left, right, 0, '1/0'), 'right threshold'),
        ):
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(CoverageInputError, reason):
                    report(self.archive, *arguments)
                self.assertEqual(self.counts(), before)

    def test_reused_revision_keeps_position_and_threshold(self):
        for center in ((0, 0, 0), OFFSET):
            with self.subTest(center=center):
                _, fit_id, left, _ = self.fit_and_conditions(center, unique=True)
                for right_minimum, expected in ((1, True), (2, False)):
                    report_id, passed = report(self.archive, fit_id, left, left, 1, right_minimum)
                    self.assertIs(passed, expected)
                    view = read_result(self.archive, 'report', report_id)
                    self.assertEqual((view['left_rev'], view['right_rev']), (left, left))
                    self.assertEqual((view['lo_left'], view['lo_right']), ('1/1', f'{right_minimum}/1'))
                    self.assertIs(view['passed'], expected)

    def test_each_condition_uses_its_own_row_count(self):
        _, fit_id, left, _ = self.fit_and_conditions(OFFSET, unique=True)
        two_rows = self.register('alternating response', [shifted(OFFSET, (2, 0, 0)), OFFSET])
        self.assertEqual(self._verdicts(fit_id, two_rows, left, [(2, 1), (2, '101/100')]), [True, False])
