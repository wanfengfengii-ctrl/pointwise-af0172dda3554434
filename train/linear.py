from fractions import Fraction
from itertools import combinations


def dot(left, right):
    return sum((a * b for a, b in zip(left, right, strict=True)), Fraction(0))


def _determinant(matrix):
    if len(matrix) == 1:
        return matrix[0][0]
    total = Fraction(0)
    for column, value in enumerate(matrix[0]):
        minor = tuple(row[:column] + row[column + 1:] for row in matrix[1:])
        term = value * _determinant(minor)
        total += -term if column % 2 else term
    return total


def principal_minors(matrix):
    """Return nonempty principal minors ordered by size, with the full determinant last."""
    indices = range(len(matrix))
    return tuple(
        _determinant(tuple(tuple(matrix[i][j] for j in chosen) for i in chosen))
        for size in range(1, len(matrix) + 1)
        for chosen in combinations(indices, size)
    )


def nullspace(matrix):
    """Return a rational column basis using the first available pivot and fixed column order."""
    working = [list(map(Fraction, row)) for row in matrix]
    width = len(working[0])
    pivot_columns = []
    for column in range(width):
        target = len(pivot_columns)
        pivot = next((i for i in range(target, len(working)) if working[i][column]), None)
        if pivot is None:
            continue
        working[target], working[pivot] = working[pivot], working[target]
        scale = working[target][column]
        working[target] = [value / scale for value in working[target]]
        for index, row in enumerate(working):
            if index == target or row[column] == 0:
                continue
            scale = row[column]
            working[index] = [a - scale * b for a, b in zip(row, working[target], strict=True)]
        pivot_columns.append(column)

    basis = []
    for free in range(width):
        if free in pivot_columns:
            continue
        vector = [Fraction(0)] * width
        vector[free] = Fraction(1)
        for row, pivot in enumerate(pivot_columns):
            vector[pivot] = -working[row][free]
        basis.append(tuple(vector))
    return tuple(basis)
