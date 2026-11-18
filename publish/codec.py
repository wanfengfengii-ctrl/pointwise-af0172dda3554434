from measure.rationals import format_rational, parse_rational


def encode_vector(vector):
    return [format_rational(value) for value in vector]


def _decode_vector(vector):
    return tuple(parse_rational(value) for value in vector)


def encode_fit_payload(unit, center, largest, basis):
    return {
        'unit': unit,
        'center': encode_vector(center),
        'largest': format_rational(largest),
        'basis': [encode_vector(column) for column in basis],
    }


def decode_fit_payload(payload):
    return {
        'unit': payload['unit'],
        'center': _decode_vector(payload['center']),
        'largest': parse_rational(payload['largest']),
        'basis': tuple(_decode_vector(column) for column in payload['basis']),
    }


def encode_report_payload(lo_left, lo_right, passed):
    return {
        'lo_left': format_rational(lo_left),
        'lo_right': format_rational(lo_right),
        'passed': passed,
    }


def decode_report_payload(payload):
    passed = payload['passed']
    if type(passed) is not bool:
        raise ValueError('stored coverage verdict must be boolean')
    return {
        'lo_left': parse_rational(payload['lo_left']),
        'lo_right': parse_rational(payload['lo_right']),
        'passed': passed,
    }
