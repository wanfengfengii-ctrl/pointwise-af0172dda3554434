from measure.rationals import parse_rational
from train.linear import principal_minors


class LargestValueError(ValueError):
    pass


def verify_largest(scatter, largest):
    try:
        value = parse_rational(largest)
    except ValueError as exc:
        raise LargestValueError(f'invalid largest eigenvalue declaration: {exc}') from exc

    shifted = tuple(
        tuple((value if i == j else 0) - entry for j, entry in enumerate(row))
        for i, row in enumerate(scatter)
    )
    # Singularity supplies an eigenvector. Positive semidefiniteness bounds the entire spectrum.
    minors = principal_minors(shifted)
    if minors[-1] != 0 or any(minor < 0 for minor in minors):
        raise LargestValueError('declared value is not the largest training eigenvalue')
    return value, shifted
