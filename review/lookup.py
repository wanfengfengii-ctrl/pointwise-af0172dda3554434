import sqlite3

from publish.fit_records import load_fit
from publish.report_records import load_report


class ResultReadError(LookupError):
    pass


def lookup_result(archive, kind, result_id):
    try:
        if kind == 'fit':
            return load_fit(archive, result_id), None
        if kind == 'report':
            report = load_report(archive, result_id)
            return load_fit(archive, report.fit_id), report
    except (LookupError, TypeError, ValueError, sqlite3.Error) as exc:
        raise ResultReadError(f'cannot read {kind} result: {exc}') from exc
    raise ResultReadError(f'unknown result kind {kind!r}')
