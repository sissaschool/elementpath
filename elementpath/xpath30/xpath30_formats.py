#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
import re
from typing import Optional

from ..exceptions import xpath_error
from ..regex import translate_pattern

from .translation_maps import ALPHABET_CHARACTERS, ROMAN_NUMERALS_MAP, \
    NUM_TO_MONTH_MAPS, NUM_TO_WEEKDAY_MAPS, NUM_TO_WORD_MAPS


PICTURE_PATTERN = re.compile(r'(?<!\[)\[(?!\[)[^]]+]')
UNICODE_DIGIT_PATTERN = re.compile(r'\d')
DECIMAL_DIGIT_PATTERN = re.compile(translate_pattern(r'^((\p{Nd}|#|[^\p{N}\p{L}])+?)$'))
WIDTH_PATTERN = re.compile(r'^([0-9]+|\*)(-([0-9]+|\*))?$')
MODIFIER_PATTERN = re.compile(r'^([co](\(.+\))?)?[at]?$')


DECIMAL_FORMATS = {
    None: {
        'decimal-separator': '.',
        'grouping-separator': ',',
        'exponent-separator': 'e',
        'infinity': 'Infinity',
        'minus-sign': '-',
        'NaN': 'NaN',
        'percent': '%',
        'per-mille': '‰',
        'zero-digit': '0',
        'digit': '#',
        'pattern-separator': ';',
    }
}


def int_to_roman(num):
    """
    Convert an integer to Roman ordinal.
    """
    def roman_num(value):
        if not value:
            yield '0'
            return
        elif value < 0:
            yield '-'
            value = abs(value)

        for base, roman in ROMAN_NUMERALS_MAP.items():
            if value:
                yield roman * (value // base)
                value %= base

    return ''.join(x for x in roman_num(num))


def int_to_alphabetic(num, reference=None):
    if not reference or len(reference) > 1:
        try:
            alphabet = ALPHABET_CHARACTERS[reference]
        except KeyError:
            msg = "formatting for language {!r} is not supported"
            raise NotImplementedError(msg.format(reference))
    else:
        for alphabet in ALPHABET_CHARACTERS.values():
            if reference in alphabet:
                break
        else:
            raise NotImplementedError("formatting for {!r} is not supported".format(reference))

    base = len(alphabet)

    if not num:
        return '0'

    chars = []
    negative = num < 0

    num = abs(num) - 1
    while num >= 0:
        chars.append(alphabet[num % base])
        num = (num // base) - 1

    if negative:
        chars.append('-')
    return ''.join(reversed(chars))


def int_to_month(num: int, lang: Optional[str] = None) -> str:
    if lang is None:
        lang = 'en'

    try:
        months_map = NUM_TO_MONTH_MAPS[lang]
    except KeyError:
        months_map = NUM_TO_MONTH_MAPS['en']

    return months_map[num]


def int_to_weekday(num: int, lang: Optional[str] = None) -> str:
    if lang is None:
        lang = 'en'

    try:
        weekday_map = NUM_TO_WEEKDAY_MAPS[lang]
    except KeyError:
        weekday_map = NUM_TO_WEEKDAY_MAPS['en']

    return weekday_map[num]


def format_digits(digits: str, fmt: str, digits_family: str = '0123456789') -> str:
    result = []
    iter_num_digits = reversed(digits)
    num_digit = next(iter_num_digits)

    for fmt_char in reversed(fmt):
        if fmt_char.isdigit() or fmt_char == '#':
            if num_digit is not None:
                result.append(digits_family[ord(num_digit) - 48])
                num_digit = next(iter_num_digits, None)
            elif fmt_char != '#':
                result.append(digits_family[0])
        elif not result or not result[-1].isdigit():
            raise xpath_error('FODF1310', "invalid grouping in picture argument")
        else:
            result.append(fmt_char)

    if num_digit is not None:
        separator = {x for x in fmt if not x.isdigit() and x != '#'}
        if len(separator) != 1:
            repeat = None
        else:
            separator = separator.pop()
            chunks = fmt.split(separator)
            repeat = len(chunks[-1])
            if all(len(item) == repeat for item in chunks[1:-1]):
                repeat += 1
            else:
                repeat = None

        if repeat is None:
            while num_digit is not None:
                result.append(digits_family[ord(num_digit) - 48])
                num_digit = next(iter_num_digits, None)
        else:
            while num_digit is not None:
                if ((len(result) + 1) % repeat) == 0:
                    result.append(separator)
                result.append(digits_family[ord(num_digit) - 48])
                num_digit = next(iter_num_digits, None)

    return ''.join(reversed(result))


def ordinal_suffix(value: int) -> str:
    value = abs(value) % 100
    if 3 < value < 20:
        return 'th'

    value %= 10
    if value == 1:
        return 'st'
    elif value == 2:
        return 'nd'
    elif value == 3:
        return 'rd'
    else:
        return 'th'


def to_ordinal_en(num_as_words: str) -> str:
    if num_as_words.endswith('one'):
        return num_as_words[:-3] + 'first'
    elif num_as_words.endswith('two'):
        return num_as_words[:-3] + 'second'
    elif num_as_words.endswith('three'):
        return num_as_words[:-5] + 'third'
    elif num_as_words.endswith('eight'):
        return num_as_words + 'h'
    elif num_as_words.endswith('nine'):
        return num_as_words[:-1] + 'th'
    elif num_as_words.endswith('y'):
        return num_as_words[:-1] + 'ieth'
    elif num_as_words.endswith('e'):
        return num_as_words[:-2] + 'fth'
    else:
        return num_as_words + 'th'


def to_ordinal_it(num_as_words: str, fmt_modifier: str) -> str:
    if '%spellout-ordinal-feminine' in fmt_modifier:
        suffix = 'a'
    elif fmt_modifier.startswith('o(-'):
        suffix = fmt_modifier[3:-1]
    else:
        suffix = ''

    ordinal_map = {
        'zero': '',
        'uno': 'primo',
        'due': 'secondo',
        'tre': 'terzo',
        'quattro': 'quarto',
        'cinque': 'quinto',
        'sei': 'sesto',
        'sette': 'settimo',
        'otto': 'ottavo',
        'nove': 'nono',
        'dieci': 'decimo',
    }

    try:
        value = ordinal_map[num_as_words]
    except KeyError:
        if num_as_words[-1] in 'eo':
            value = num_as_words[:-1] + 'esimo'
        else:
            value = num_as_words + 'esimo'

    if value and suffix:
        return value[:-1] + suffix
    return value


def int_to_words(num, lang=None, fmt_modifier=''):

    def word_num(value):
        try:
            yield num_map[value]
        except KeyError:
            for base, word in num_map.items():
                if base >= 1:
                    floor = value // base
                    if not floor:
                        continue
                    elif base >= 100:
                        yield from word_num(floor)
                        yield ' '

                    yield word
                    value %= base
                    if not value:
                        break
                    elif base < 100:
                        yield '-'
                    elif base == 100:
                        yield ' and '
                    else:
                        yield ' '

    try:
        num_map = NUM_TO_WORD_MAPS[lang]
    except KeyError:
        lang = 'en'
        num_map = NUM_TO_WORD_MAPS[lang]

    if num < 0:
        result = '-' + ''.join(x for x in word_num(abs(num)))
    else:
        result = ''.join(x for x in word_num(num))

    if not fmt_modifier.startswith('o'):
        return result

    if lang == 'en':
        return to_ordinal_en(result)
    elif lang == 'it':
        return to_ordinal_it(result, fmt_modifier)
    else:
        return result


def parse_datetime_picture(picture):
    """
    Analyze a picture argument of XPath 3.0+ formatting functions.

    :param picture: the picture string.
    :return: a couple of lists containing the literal parts and markers.
    """
    literals = PICTURE_PATTERN.split(picture)
    for lit in literals:
        if '[' in lit.replace('[[', ''):
            raise xpath_error('FOFD1340', "Invalid character '[' in picture literal")
        elif ']' in lit.replace(']]', ''):
            raise xpath_error('FOFD1340', "Invalid character ']' in picture literal")

    markers = [x.group().replace(' ', '') for x in PICTURE_PATTERN.finditer(picture)]
    assert len(markers) == (len(literals) - 1)

    msg_tmpl = 'Invalid formatting component {!r}'
    for value in markers:
        if value[1] not in 'YMDdFWwHhPmsfZzCE':
            raise xpath_error('FOFD1340', msg_tmpl.format(value))

        if ',' not in value:
            presentation = value[2:-1]
        else:
            presentation, width = value[2:-1].rsplit(',', maxsplit=1)

            if WIDTH_PATTERN.match(width) is None:
                raise xpath_error('FOFD1340', f'Invalid width modifier {value!r}')
            elif '-' not in width:
                if '*' not in width and not int(width):
                    raise xpath_error('FOFD1340', f'Invalid width modifier {value!r}')
            elif '*' not in width:
                min_value, max_value = map(int, width.split('-'))
                if min_value < 1 or max_value < min_value:
                    raise xpath_error('FOFD1340', msg_tmpl.format(value))
            else:
                min_value, max_value = width.split('-')
                if min_value != '*' and not int(min_value):
                    raise xpath_error('FOFD1340', f'Invalid width modifier {value!r}')
                if max_value != '*' and not int(max_value):
                    raise xpath_error('FOFD1340', f'Invalid width modifier {value!r}')

        if len(presentation) > 1 and presentation[-1] in 'atco':
            presentation = presentation[:-1]

        if not presentation or presentation in {'i', 'I', 'w', 'W', 'Ww', 'n', 'N', 'Nn', 'Z'}:
            pass
        elif DECIMAL_DIGIT_PATTERN.match(presentation) is None:
            raise xpath_error('FOFD1340', msg_tmpl.format(value))
        else:
            # Check digits set uniformity
            cp = None
            for ch in reversed(presentation):
                if not ch.isdigit():
                    continue
                elif cp is None:
                    cp = ord(ch)
                elif abs(ord(ch) - cp) > 10:
                    raise xpath_error('FOFD1340', msg_tmpl.format(value))

    return literals, markers


def parse_datetime_marker(marker, dt, lang=None):
    component = marker[1]
    fmt_token = marker[2:-1]

    if ',' not in fmt_token:
        presentation, width = fmt_token, ''
    else:
        presentation, width = fmt_token.rsplit(',', maxsplit=1)

    if not presentation:
        if component in 'Hhf':
            presentation = '1'
        elif component in 'ms':
            presentation = '01'
        elif component in 'Zz':
            presentation = '01:01'
        else:
            presentation = 'n'

    digits = sum(c.isdigit() for c in presentation)
    opt_digits = presentation.count('#')
    if not width or width == '*':
        if digits > 1:
            min_width, max_width = digits, digits + opt_digits
        else:
            min_width, max_width = 0, None
    else:
        min_width, max_width = parse_width(width)
        if digits > 1:
            min_width = max(min_width, digits)
            if max_width:
                max_width = max(max_width, digits + opt_digits)

    zero_cp = 0
    if component == 'Y':
        value = str(dt.year)
    elif component == 'M':
        if presentation.lower().startswith('n') and lang is not None:
            value = int_to_month(dt.month, lang)
        else:
            value = str(dt.month)
    elif component == 'D':
        value = str(dt.day)
    elif component == 'H':
        value = str(dt.hour)
    elif component == 'h':
        if dt.hour == 0:
            value = '12'
        elif dt.hour > 12:
            value = str(dt.hour % 12)
        else:
            value = str(dt.hour)
    elif component == 'P':
        value = 'a.m.' if dt.hour < 12 else 'p.m.'
    elif component == 'm':
        value = str(dt.minute)
    elif component == 's':
        value = str(dt.second)
    elif component == 'f':
        value = str('{:06}'.format(dt.microsecond))
    elif component == 'z':
        value = str(dt.tzinfo or '+00:00')
        fmt_chunk = 'GMT'
        min_width += 3
        max_width += 3
        if value == 'Z':
            value = '+00:00'
    elif component == 'Z':
        value = str(dt.tzinfo or '+00:00')
        if value == 'Z':
            value = '+00:00'
    elif component == 'W':
        value = str(dt.isocalendar()[2])
    elif component == 'w':
        import calendar
        month_cal = calendar.monthcalendar(dt.year, dt.month)
        if dt.day in month_cal[0]:
            value = '1' if month_cal[0][3] else '5'
        elif month_cal[0][3]:
            value = str((dt.day - month_cal[0][6]) // 7 + 1)
        else:
            value = str((dt.day - month_cal[0][6]) // 7)
    elif component == 'F':
        if presentation.lower().startswith('n') and lang is not None:
            value = int_to_weekday(dt.isocalendar().weekday, lang)
        else:
            value = str(dt.isocalendar().weekday)
    else:
        print(f"MISSING: {component!r}")
        # breakpoint()

    if presentation == 'n':
        fmt_chunk = value.lower()
    elif presentation == 'N':
        fmt_chunk = value.upper()
    elif presentation == 'Nn':
        fmt_chunk = value.title()
    elif presentation == 'I':
        fmt_chunk = int_to_roman(int(value))
    elif presentation == 'i':
        fmt_chunk = int_to_roman(int(value)).lower()
    elif presentation.startswith('Ww'):
        fmt_chunk = int_to_words(int(value), lang, presentation[2:]).title()
    elif presentation.startswith('w'):
        fmt_chunk = int_to_words(int(value), lang, presentation[1:])
    elif presentation.startswith('W'):
        fmt_chunk = int_to_words(int(value), lang, presentation[1:]).upper()
    else:
        k = 0
        pch = None
        fmt_chunk = []
        if presentation[-1] in 'co':
            fmt_modifier = presentation[-1]
            presentation = presentation[:-1]
        else:
            fmt_modifier = ''

        for ch in value:
            try:
                pch = presentation[k]
            except IndexError:
                if pch != '#' and not pch.isdigit():
                    break
            else:
                k += 1

            while pch != '#' and not pch.isdigit():
                fmt_chunk.append(pch)
                min_width += 1
                if max_width:
                    max_width += 1
                try:
                    pch = presentation[k]
                except IndexError:
                    break
                else:
                    k += 1
            else:
                if ch == '-' or ch == '+':
                    fmt_chunk.append(ch)
                    min_width += 1
                    if max_width:
                        max_width += 1
                    k -= 1
                    continue

                if ch != '#' and not ch.isdigit():
                    continue
                elif not zero_cp:
                    if pch == '#':
                        zero_cp = ord('0')
                        # raise xpath_error('FOFD1340', f'Invalid formatting component {presentation!r}')
                    else:
                        zero_cp = ord(pch) - int(pch)
                fmt_chunk.append(chr(zero_cp + int(ch)))

        fmt_chunk = ''.join(fmt_chunk)
        if fmt_modifier == 'o':
            try:
                fmt_chunk += ordinal_suffix(int(fmt_chunk))
            except ValueError:
                pass
            else:
                min_width += 2
                if max_width:
                    max_width += 2

    zero_ch = '0' if not zero_cp else chr(zero_cp)
    if len(fmt_chunk) < min_width and component not in 'PzZ':
        fmt_chunk = zero_ch * (min_width - len(fmt_chunk)) + fmt_chunk
    if max_width:
        fmt_chunk = fmt_chunk[:max_width]
    if min_width or component == 'f':
        try:
            nz_last = max(k for k in range(len(fmt_chunk)) if fmt_chunk[k] != zero_ch)
        except ValueError:
            nz_last = 0

        fmt_chunk = fmt_chunk[:max(min_width, nz_last + 1)]
    return fmt_chunk


def parse_width(width):
    if WIDTH_PATTERN.match(width) is None:
        raise xpath_error('FOFD1340', f'Invalid width modifier {width!r}')
    elif '-' not in width:
        if width == '*':
            return 0, None
        min_width = int(width)
        if not min_width:
            raise xpath_error('FOFD1340', f'Invalid width modifier {width!r}')
        return min_width, None
    elif '*' not in width:
        min_width, max_width = map(int, width.split('-'))
        if not min_width or max_width < min_width:
            raise xpath_error('FOFD1340', f'Invalid width modifier {width!r}')
        return min_width, max_width
    else:
        min_width, max_width = width.split('-')
        if min_width == '*':
            min_width = 0
        else:
            min_width = int(min_width)
            if not min_width:
                raise xpath_error('FOFD1340', f'Invalid width modifier {width!r}')

        if max_width == '*':
            return min_width, None
        else:
            max_width = int(max_width)
            if not max_width:
                raise xpath_error('FOFD1340', f'Invalid width modifier {width!r}')
            return min_width, max_width
