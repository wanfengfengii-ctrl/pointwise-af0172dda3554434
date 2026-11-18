from fractions import Fraction

from train.center import center_rows


def mean_outer_products(rows):
    count = len(rows)
    width = len(rows[0])
    return tuple(
        tuple(sum((row[i] * row[j] for row in rows), Fraction(0)) / count for j in range(width))
        for i in range(width)
    )


def compute_scatter(rows, center):
    return mean_outer_products(center_rows(rows, center))
