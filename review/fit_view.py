from publish.codec import encode_fit_payload
from publish.fit_records import FitRecord


def build_fit_view(frozen: FitRecord) -> dict:
    return {
        'kind': 'fit',
        'fit_id': frozen.fit_id,
        'train_rev': frozen.train_rev,
        'scatter': 'mean_centered_outer_product',
        **encode_fit_payload(frozen.unit, frozen.center, frozen.largest, frozen.basis),
    }
