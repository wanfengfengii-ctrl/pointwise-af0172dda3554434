import re
from fractions import Fraction


_INTEGER = r'[+-]?[0-9]+'
_RATIO = re.compile(rf'({_INTEGER})/({_INTEGER})')
_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')


def parse_rational(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Fraction(value)
    if isinstance(value, str):
        text = value.strip()
        ratio = _RATIO.fullmatch(text)
        if ratio:
            try:
                return Fraction(int(ratio[1]), int(ratio[2]))
            except ZeroDivisionError as exc:
                raise ValueError('a rational denominator must be nonzero') from exc
        if _DECIMAL.fullmatch(text):
            return Fraction(text)
    raise ValueError('expected an integer, fraction, or finite decimal')


def format_rational(value: Fraction) -> str:
    return f'{value.numerator}/{value.denominator}'
