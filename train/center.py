from fractions import Fraction


def compute_center(rows):
    count = len(rows)
    return tuple(sum(column, Fraction(0)) / count for column in zip(*rows, strict=True))


def center_rows(rows, center):
    return tuple(
        tuple(value - origin for value, origin in zip(row, center, strict=True))
        for row in rows
    )
