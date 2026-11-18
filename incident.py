"""Reconcile the tied-axis incident with a new fit and a known valid archived fit.

Run with python3.11 -B -m incident. The training rows are both signed unit
vectors on X and Y. On that plane the left and right energies sum to one.
Two half thresholds are reachable together. Two three-quarter thresholds are not.
"""

from contextlib import closing
from fractions import Fraction

from audit.decision import report
from measure.revisions import register_batch
from publish.commit import publish_fit
from publish.store import initialize_archive, open_archive
from review.handoff import read_result
from train.freeze import fit


def main() -> int:
    axes = ('X', 'Y', 'Z')
    x, y = (1, 0, 0), (0, 1, 0)
    with closing(open_archive(':memory:')) as archive:
        initialize_archive(archive)
        train = register_batch(archive, 'training', 'mm/s', axes, (x, (-1, 0, 0), y, (0, -1, 0)))
        left = register_batch(archive, 'left', 'mm/s', axes, (x,))
        right = register_batch(archive, 'right', 'mm/s', axes, (y,))
        fresh = fit(archive, train, '1/2')
        dimension = len(read_result(archive, 'fit', fresh)['basis'])
        coverage = [report(archive, fresh, left, right, minimum, minimum)[1]
                    for minimum in ('1/2', '3/4')]
        # Fixture for a fit that had already been correctly published.
        archived = publish_fit(archive, train, 'mm/s', (0, 0, 0), Fraction(1, 2), (x, y))
        report_id, _ = report(archive, archived, left, right, '3/4', '3/4')
        archived_coverage = read_result(archive, 'report', report_id)['passed']
    checks = (
        ('new fit dimension', 2, dimension),
        ('new fit coverage', [True, False], coverage),
        ('archived fit coverage', False, archived_coverage),
    )
    for label, expected, actual in checks:
        print(f'{label}: expected {expected!r}, got {actual!r}')
    return int(any(expected != actual for _, expected, actual in checks))


if __name__ == '__main__':
    raise SystemExit(main())
