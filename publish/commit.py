from publish.fit_records import insert_fit
from publish.links import record_fit_link, record_report_links, result_key
from publish.report_records import insert_report
from publish.store import write_transaction


class PublicationError(RuntimeError):
    pass


def publish_fit(archive, train_rev, unit, center, largest, basis, *, before_commit=None) -> str:
    try:
        with write_transaction(archive):
            key = insert_fit(archive, unit, center, largest, basis)
            record_fit_link(archive, key, train_rev)
            if before_commit is not None:
                before_commit()
    except Exception as exc:
        raise PublicationError('fit publication failed') from exc
    return f'fit:{key}'


def publish_report(archive, fit_id, left_rev, right_rev, lo_left, lo_right, passed,
                   *, before_commit=None) -> str:
    try:
        with write_transaction(archive):
            key = insert_report(archive, lo_left, lo_right, passed)
            record_report_links(archive, key, result_key(fit_id, 'fit'), left_rev, right_rev)
            if before_commit is not None:
                before_commit()
    except Exception as exc:
        raise PublicationError('report publication failed') from exc
    return f'report:{key}'
