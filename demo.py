import argparse
import json
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from audit.decision import report
from measure.catalog import load_revision
from measure.rationals import format_rational
from measure.revisions import register_batch
from publish.commit import PublicationError
from publish.store import initialize_archive, open_archive
from review.handoff import read_result
from train.freeze import FitInputError, fit


SAMPLES = Path(__file__).resolve().parent / 'samples'


def _load_sample(name):
    return json.loads((SAMPLES / name).read_text(encoding='utf-8'))


def _register(archive, batch, *, parent=None):
    return register_batch(archive, batch['name'], batch['unit'], batch['columns'], batch['rows'],
                          parent_rev=parent)


def _check(actual, expected, label):
    if actual != expected:
        raise AssertionError(f'{label}: expected {expected!r}, got {actual!r}')


def _snapshot(archive, fit_id, report_ids):
    frozen = read_result(archive, 'fit', fit_id)
    reports = [read_result(archive, 'report', report_id) for report_id in report_ids]
    return frozen, reports


def _report_counts(archive):
    return archive.execute('SELECT (SELECT count(*) FROM reports), (SELECT count(*) FROM report_links)').fetchone()


def _release_examples(archive, data, expected, revisions):
    training, left, right = (revisions[slot] for slot in ('training', 'left', 'right'))
    frozen_id = fit(archive, training, data['largest'])
    try:
        fit(archive, training, data['invalid_largest'])
    except FitInputError:
        _check(archive.execute('SELECT count(*) FROM fits').fetchone()[0], 1, 'invalid fit count')
    else:
        raise AssertionError('inaccurate highest-value declaration was accepted')

    published = [report(archive, frozen_id, left, right, *pair) for pair in data['thresholds']]
    report_ids = [report_id for report_id, _ in published]
    verdicts = [passed for _, passed in published]
    _check(verdicts, expected['coverage'], 'common-axis verdicts')
    snapshot = _snapshot(archive, frozen_id, report_ids)
    fit_view, report_views = snapshot
    _check({key: fit_view[key] for key in expected['fit']}, expected['fit'], 'frozen fit')
    _check(fit_view['train_rev'], training, 'fit source')
    for view, (minimum_left, minimum_right), passed in zip(
            report_views, data['thresholds'], expected['coverage'], strict=True):
        _check([view['fit_id'], view['train_rev'], view['left_rev'], view['right_rev']],
               [frozen_id, training, left, right], 'report sources')
        _check([view['lo_left'], view['lo_right'], view['passed']],
               [minimum_left, minimum_right, passed], 'readable report payload')
    return frozen_id, report_ids, verdicts, snapshot


def _interrupt_report(archive, frozen_id, revisions, thresholds):
    before = _report_counts(archive)
    staged = []

    def interrupt():
        staged.append(_report_counts(archive))
        raise RuntimeError('simulated interruption before commit')

    try:
        report(archive, frozen_id, revisions['left'], revisions['right'], *thresholds,
               before_commit=interrupt)
    except PublicationError:
        _check(staged, [tuple(count + 1 for count in before)], 'staged report and link')
        _check(_report_counts(archive), before, 'report rollback')
    else:
        raise AssertionError('interrupted publication succeeded')
    return before


def _read_corrected_sources(archive, old_revisions, new_revisions):
    sources = {slot: load_revision(archive, revision) for slot, revision in new_revisions.items()}
    for slot, source in sources.items():
        _check(source.parent_rev, old_revisions[slot], f'{slot} correction parent')
    return {slot: [format_rational(value) for value in source.rows[0]]
            for slot, source in sources.items()}


def _emit(case_id, inputs, expected, actual, downstream_expected, downstream_actual, paths, oracle):
    evidence = {
        'case_id': case_id,
        'input': inputs,
        'expected': expected,
        'actual': actual,
        'downstream_expected': downstream_expected,
        'downstream_actual': downstream_actual,
        'code_paths': paths,
        'oracle': oracle,
    }
    print('POINTWISE_SCENARIO ' + json.dumps(evidence, ensure_ascii=False, sort_keys=True))


def run_demo():
    data = _load_sample('day.json')
    expected = _load_sample('expected.json')
    with TemporaryDirectory() as directory:
        path = Path(directory) / 'demo.sqlite3'
        with closing(open_archive(path)) as archive:
            initialize_archive(archive)
            revisions = {slot: _register(archive, batch) for slot, batch in data['batches'].items()}
            frozen_id, report_ids, verdicts, snapshot = _release_examples(archive, data, expected, revisions)
            counts = _interrupt_report(archive, frozen_id, revisions, data['thresholds'][0])
            corrected = {
                slot: _register(archive, data['batches'][slot] | changes, parent=revisions[slot])
                for slot, changes in data['corrections'].items()
            }
        for _ in range(2):
            with closing(open_archive(path)) as archive:
                initialize_archive(archive)
                _check(_report_counts(archive), counts, 'durable rollback')
                reread = _snapshot(archive, frozen_id, report_ids)
                _check(reread, snapshot, 'fixed handoff after reopening')
                corrected_first_rows = _read_corrected_sources(archive, revisions, corrected)
                _check(corrected_first_rows, expected['corrected_first_rows'], 'durable corrections')
        with closing(open_archive(path)) as archive:
            initialize_archive(archive)
            retry_id, passed = report(archive, frozen_id, revisions['left'], revisions['right'],
                                      *data['thresholds'][0])
            _check(passed, expected['coverage'][0], 'retry verdict')
            _check(read_result(archive, 'report', retry_id)['passed'], passed, 'durable retry')

    frozen, report_views = reread
    _emit('v6.translated_cases', {'batches': data['batches'], 'largest': data['largest'],
                                  'thresholds': data['thresholds']},
          expected['coverage'], verdicts, expected['coverage'], [view['passed'] for view in report_views],
          ['train/freeze.py', 'audit/energy.py', 'audit/criterion.py', 'audit/decision.py',
           'review/report_view.py'],
          'The two unit-axis energies add to one. A diagonal reaches both halves exactly.')
    original_sources = [revisions[slot] for slot in ('training', 'left', 'right')]
    _emit('v9.archive_reopen', {'source_ids': original_sources, 'corrections': data['corrections']},
          original_sources, [frozen['train_rev'], report_views[0]['left_rev'], report_views[0]['right_rev']],
          expected['corrected_first_rows'], corrected_first_rows,
          ['measure/catalog.py', 'publish/store.py', 'publish/links.py', 'review/handoff.py'],
          'Compare the published parents with the IDs originally passed in and the new rows with the inputs.')


def main():
    parser = argparse.ArgumentParser(description='Three-axis vibration review archive')
    commands = parser.add_subparsers(dest='command', required=True)
    initialize = commands.add_parser('init', help='initialize a local archive')
    initialize.add_argument('archive', type=Path)
    commands.add_parser('demo', help='run the sample day in an isolated archive')
    options = parser.parse_args()
    if options.command == 'init':
        with closing(open_archive(options.archive)) as archive:
            initialize_archive(archive)
    else:
        run_demo()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
