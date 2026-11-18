from publish.codec import encode_report_payload, encode_vector
from publish.fit_records import FitRecord
from publish.report_records import ReportRecord


def build_report_view(report: ReportRecord, fit: FitRecord) -> dict:
    return {
        'kind': 'report',
        'report_id': report.report_id,
        'fit_id': fit.fit_id,
        'train_rev': fit.train_rev,
        'left_rev': report.left_rev,
        'right_rev': report.right_rev,
        'unit': fit.unit,
        'energy_unit': f'({fit.unit})^2',
        'center': encode_vector(fit.center),
        'energy': 'mean_squared_projection_about_training_center',
        **encode_report_payload(report.lo_left, report.lo_right, report.passed),
    }
