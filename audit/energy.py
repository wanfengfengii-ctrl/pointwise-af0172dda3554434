from train.center import center_rows
from train.linear import dot
from train.scatter import mean_outer_products


def compute_energy_form(rows, center, basis):
    coordinates = tuple(
        tuple(dot(row, column) for column in basis)
        for row in center_rows(rows, center)
    )
    return mean_outer_products(coordinates)
