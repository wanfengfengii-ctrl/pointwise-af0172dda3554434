from measure.catalog import UnknownRevision, load_revision
from publish.commit import publish_fit
from train.center import compute_center
from train.linear import nullspace
from train.scatter import compute_scatter
from train.spectrum import LargestValueError, verify_largest


class FitInputError(ValueError):
    pass


def fit(archive, train_rev, largest, *, before_commit=None) -> str:
    try:
        batch = load_revision(archive, train_rev)
    except UnknownRevision as exc:
        raise FitInputError(f'training source: {exc}') from exc

    center = compute_center(batch.rows)
    scatter = compute_scatter(batch.rows, center)
    try:
        value, shifted = verify_largest(scatter, largest)
    except LargestValueError as exc:
        raise FitInputError(str(exc)) from exc

    basis = nullspace(shifted)
    if len(basis) not in (1, 2):
        raise FitInputError('the largest eigenspace must have dimension one or two')
    return publish_fit(archive, train_rev, batch.unit, center, value, basis,
                       before_commit=before_commit)
