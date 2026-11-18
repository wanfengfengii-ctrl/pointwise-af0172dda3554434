from publish.commit import PublicationError
from review.handoff import read_result
from tests.support import ArchiveCase, OFFSET, X, Y, ZERO, training_rows
from train.freeze import FitInputError, fit


class FitTests(ArchiveCase):
    def test_unique_axis(self):
        train_rev = self.register('training', training_rows(ZERO, X))
        fit_id = fit(self.archive, train_rev, 1)
        view = read_result(self.archive, 'fit', fit_id)
        self.assertEqual(view['center'], ['0/1', '0/1', '0/1'])
        self.assertEqual(view['basis'], [['1/1', '0/1', '0/1']])
        self.assertEqual((view['train_rev'], view['largest']), (train_rev, '1/1'))
        self.assertEqual(view['scatter'], 'mean_centered_outer_product')

    def test_translated_tied_space_keeps_both_axes(self):
        train_rev = self.register('training', training_rows(OFFSET, X, Y))
        fit_id = fit(self.archive, train_rev, '1/2')
        view = read_result(self.archive, 'fit', fit_id)
        self.assertEqual(view['center'], ['2/1', '-3/1', '1/2'])
        self.assertEqual(view['basis'], [['1/1', '0/1', '0/1'], ['0/1', '1/1', '0/1']])
        self.assertEqual((view['train_rev'], view['largest']), (train_rev, '1/2'))

    def test_value_above_spectrum_does_not_publish(self):
        train_rev = self.register('training', training_rows(ZERO, X, Y))
        before = self.counts()
        with self.assertRaisesRegex(FitInputError, 'largest training eigenvalue'):
            fit(self.archive, train_rev, 1)
        self.assertEqual(self.counts(), before)

    def test_real_but_lower_eigenvalue_does_not_publish(self):
        train_rev = self.register('training', training_rows(ZERO, (2, 0, 0), Y))
        before = self.counts()
        with self.assertRaisesRegex(FitInputError, 'largest training eigenvalue'):
            fit(self.archive, train_rev, '1/2')
        self.assertEqual(self.counts(), before)
        fit_id = fit(self.archive, train_rev, 2)
        view = read_result(self.archive, 'fit', fit_id)
        self.assertEqual(view['basis'], [['1/1', '0/1', '0/1']])
        self.assertEqual(view['largest'], '2/1')

    def test_unknown_source_bad_rational_and_unsupported_dimension(self):
        constant = self.register('constant training', [OFFSET, OFFSET])
        train_rev = self.register('training', training_rows(ZERO, X))
        before = self.counts()
        for revision, declaration, reason in (
            (999, 1, 'training source'),
            (train_rev, '1/0', 'declaration'),
            (constant, 0, 'dimension one or two'),
        ):
            with self.subTest(revision=revision, declaration=declaration):
                with self.assertRaisesRegex(FitInputError, reason):
                    fit(self.archive, revision, declaration)
                self.assertEqual(self.counts(), before)

    def test_fit_publication_rolls_back_its_body_and_link(self):
        train_rev = self.register('training', training_rows(ZERO, X))
        before = self.counts()
        staged = []

        def fail_after_write():
            staged.append(self.counts())
            raise RuntimeError('fit write interrupted')

        with self.assertRaisesRegex(PublicationError, 'fit publication failed'):
            fit(self.archive, train_rev, 1, before_commit=fail_after_write)
        self.assertEqual(staged, [(before[0], before[1] + 1, before[2] + 1, before[3], before[4])])
        self.reopen()
        self.assertEqual(self.counts(), before)
        fit_id = fit(self.archive, train_rev, 1)
        self.assertEqual(read_result(self.archive, 'fit', fit_id)['train_rev'], train_rev)
