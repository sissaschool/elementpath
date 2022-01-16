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
"""
XPath 3.0 implementation - part 3 (functions)
"""
import decimal
import os
import re
import codecs
import math
import xml.etree.ElementTree as ElementTree
from copy import copy
from urllib.parse import urlsplit

from ..exceptions import ElementPathError
from ..helpers import XML_NEWLINES_PATTERN, is_xml_codepoint
from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, \
    XSLT_XQUERY_SERIALIZATION_NAMESPACE, split_expanded_name
from ..xpath_nodes import etree_iter_paths, is_xpath_node, is_element_node, \
    is_document_node, is_etree_element, is_schema_node, node_document_uri, \
    node_nilled, node_name, TypedElement, TextNode, AttributeNode, \
    TypedAttribute, NamespaceNode, is_processing_instruction_node
from ..xpath_token import XPathFunction
from ..xpath_context import XPathSchemaContext
from ..datatypes import xsd10_atomic_types, NumericProxy, QName, Date10, \
    DateTime10, Time, AnyURI, UntypedAtomic
from ..regex import translate_pattern, RegexError

from .xpath30_operators import XPath30Parser
from .xpath30_formats import UNICODE_DIGIT_PATTERN, DECIMAL_DIGIT_PATTERN, \
    MODIFIER_PATTERN, DECIMAL_FORMATS, int_to_roman, int_to_alphabetic, format_digits, \
    int_to_words, parse_datetime_picture, parse_datetime_marker, ordinal_suffix

# XSLT and XQuery Serialization parameters
SERIALIZATION_PARAMS = '{%s}serialization-parameters' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_OMIT_XML_DECLARATION = '{%s}omit-xml-declaration' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_USE_CHARACTER_MAPS = '{%s}use-character-maps' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_CHARACTER_MAP = '{%s}character-map' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_METHOD = '{%s}method' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_INDENT = '{%s}indent' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_VERSION = '{%s}version' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_CDATA = '{%s}cdata-section-elements' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_NO_INDENT = '{%s}suppress-indentation' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_STANDALONE = '{%s}standalone' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_ITEM_SEPARATOR = '{%s}item-separator' % XSLT_XQUERY_SERIALIZATION_NAMESPACE

DECL_PARAM_PATTERN = re.compile(r'([^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*)=')

register = XPath30Parser.register
method = XPath30Parser.method
function = XPath30Parser.function


###
# 'inline function' expression or 'function test'
@method(register('function', bp=90, label='anonymous function', bases=(XPathFunction,)))
def nud_anonymous_function(self):
    if self.parser.next_token.symbol != '(':
        self.label = 'inline function'
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    self.parser.advance('(')
    self.sequence_types = []

    if self.parser.next_token.symbol in ('$', ')'):
        self.label = 'inline function'
        while self.parser.next_token.symbol != ')':
            self.parser.next_token.expected('$')
            param = self.parser.expression(5)
            self.append(param)
            if self.parser.next_token.symbol == 'as':
                self.parser.advance('as')
                token = self.parser.expression(5)
                sequence_type = token.source
                if not self.parser.is_sequence_type(sequence_type):
                    raise token.error('XPST0003', "a sequence type expected")

                next_symbol = self.parser.next_token.symbol
                if sequence_type != 'empty-sequence()' and next_symbol in ('?', '*', '+'):
                    self.parser.advance()
                    sequence_type += next_symbol
                self.sequence_types.append(sequence_type)

            else:
                self.sequence_types.append('item()*')

            self.parser.next_token.expected(')', ',')
            if self.parser.next_token.symbol == ',':
                self.parser.advance()
                self.parser.next_token.unexpected(')')

        self.parser.advance(')')

    elif self.parser.next_token.symbol == '*':
        self.label = 'function test'
        self.append(self.parser.advance('*'))
        self.sequence_types.append('*')
        self.parser.advance(')')
        return self

    else:
        self.label = 'function test'
        token = self.parser.expression(5)
        sequence_type = token.source
        if not self.parser.is_sequence_type(sequence_type):
            raise token.error('XPST0003', "a sequence type expected")
        self.sequence_types.append(sequence_type)
        self.parser.advance(')')
        self.append(token)

    # Add function return sequence type
    if self.parser.next_token.symbol != 'as':
        self.sequence_types.append('item()*')
    else:
        self.parser.advance('as')
        if self.parser.next_token.label not in ('kind test', 'sequence type'):
            self.parser.expected_name('(name)', ':')
        token = self.parser.expression(rbp=90)

        next_symbol = self.parser.next_token.symbol
        if token.symbol != 'empty-sequence' and next_symbol in {'?', '*', '+'}:
            self.parser.symbol_table[next_symbol](self.parser),  # Add nullary token
            self.parser.advance()
            sequence_type = token.source + next_symbol
        else:
            sequence_type = token.source

        if not self.parser.is_sequence_type(sequence_type):
            raise token.error('XPST0003', "a sequence type expected")
        self.sequence_types.append(sequence_type)

    if self.label == 'inline function':
        self.parser.advance('{')
        self.body = self.parser.expression()
        self.parser.advance('}')

    return self


@method('function')
def evaluate_anonymous_function(self, context=None):
    if context is None:
        raise self.missing_context()

    if self.label == 'function test':
        if isinstance(context.item, XPathFunction):
            return context.item
        else:
            return None
    else:
        return self


###
# Mathematical functions
@method(function('pi', label='math function', nargs=0, sequence_types=('xs:double',)))
def evaluate_pi_function(self, context=None):
    return math.pi


@method(function('exp', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_exp_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.exp(arg)


@method(function('exp10', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_exp10_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float(10 ** arg)


@method(function('log', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_log_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log(arg)


@method(function('log10', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_log10_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log10(arg)


@method(function('pow', label='math function', nargs=2,
                 sequence_types=('xs:double?', 'numeric', 'xs:double?')))
def evaluate_pow_function(self, context=None):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    if x is not None:
        if not x and y < 0:
            return math.copysign(float('inf'), x) if (y % 2) == 1 else float('inf')

        try:
            return float(x ** y)
        except TypeError:
            return float('nan')


@method(function('sqrt', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_sqrt_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < 0:
            return float('nan')
        return math.sqrt(arg)


@method(function('sin', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_sin_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.sin(arg)


@method(function('cos', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_cos_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.cos(arg)


@method(function('tan', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_tan_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.tan(arg)


@method(function('asin', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_asin_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.asin(arg)


@method(function('acos', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_acos_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.acos(arg)


@method(function('atan', label='math function', nargs=1,
                 sequence_types=('xs:double?', 'xs:double?')))
def evaluate_atan_function(self, context=None):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.atan(arg)


@method(function('atan2', label='math function', nargs=2,
                 sequence_types=('xs:double', 'xs:double', 'xs:double')))
def evaluate_atan2_function(self, context=None):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    return math.atan2(x, y)


###
# Formatting functions
@method(function('format-integer', nargs=(2, 3),
                 sequence_types=('xs:integer?', 'xs:string', 'xs:string?', 'xs:string')))
def evaluate_format_integer_function(self, context=None):
    value = self.get_argument(context, cls=NumericProxy)
    picture = self.get_argument(context, index=1, required=True, cls=str)
    lang = self.get_argument(context, index=2, cls=str)
    if value is None:
        return ''

    if ';' not in picture:
        fmt_token, fmt_modifier = picture, ''
    else:
        fmt_token, fmt_modifier = picture.rsplit(';', 1)

    if MODIFIER_PATTERN.match(fmt_modifier) is None:
        raise self.error('FODF1310')

    if not fmt_token:
        raise self.error('FODF1310')
    elif fmt_token in {'A', 'a', 'i', 'I', 'w', 'W', 'Ww'}:
        if fmt_token == 'a':
            result = int_to_alphabetic(value, lang)
        elif fmt_token == 'A':
            result = int_to_alphabetic(value, lang).upper()
        elif fmt_token == 'i':
            result = int_to_roman(value).lower()
        elif fmt_token == 'I':
            result = int_to_roman(value)
        elif fmt_token == 'w':
            return int_to_words(value, lang, fmt_modifier)
        elif fmt_token == 'W':
            return int_to_words(value, lang, fmt_modifier).upper()
        else:
            return int_to_words(value, lang, fmt_modifier).title()

    else:
        if UNICODE_DIGIT_PATTERN.search(fmt_token) is None:
            base_char = '1'
            for base_char in fmt_token:
                if base_char.isalpha():
                    break
            result = int_to_alphabetic(value, base_char)

        elif DECIMAL_DIGIT_PATTERN.match(fmt_token) is None:
            msg = 'picture argument has an invalid primary format token'
            raise self.error('FODF1310', msg)
        else:
            digits = UNICODE_DIGIT_PATTERN.findall(fmt_token)
            cp = ord(digits[0])
            if any((ord(ch) - cp) > 10 for ch in digits[1:]):
                msg = "picture argument mixes digits from different digit families"
                raise self.error('FODF1310', msg)
            elif fmt_token[0].isdigit():
                if '#' in fmt_token:
                    msg = 'picture argument has an invalid primary format token'
                    raise self.error('FODF1310', msg)
            elif fmt_token[0] != '#':
                raise self.error('FODF1310', "invalid grouping in picture argument")

            if digits[0].isdigit():
                cp = ord(digits[0])
                while chr(cp - 1).isdigit():
                    cp -= 1
                digits_family = ''.join(chr(cp + k) for k in range(10))
            else:
                raise ValueError()

            if value < 0:
                result = '-' + format_digits(str(abs(value)), fmt_token, digits_family)
            else:
                result = format_digits(str(abs(value)), fmt_token, digits_family)

    if fmt_modifier.startswith('o'):
        return f'{result}{ordinal_suffix(value)}'
    return result


@method(function('format-number', nargs=(2, 3),
                 sequence_types=('numeric?', 'xs:string', 'xs:string?', 'xs:string')))
def evaluate_format_number_function(self, context=None):
    value = self.get_argument(context, cls=NumericProxy)
    picture = self.get_argument(context, index=1, required=True, cls=str)
    decimal_format_name = self.get_argument(context, index=2, cls=str)
    if value is None:
        return ''

    try:
        decimal_format = DECIMAL_FORMATS[decimal_format_name]
    except KeyError:
        decimal_format = DECIMAL_FORMATS[None]

    pattern_separator = decimal_format['pattern-separator']
    sub_pictures = picture.split(pattern_separator)
    if len(sub_pictures) > 2:
        breakpoint()

    decimal_separator = decimal_format['decimal-separator']
    if any(p.count(decimal_separator) > 1 for p in sub_pictures):
        raise self.error('FODF1310')

    percent_sign = decimal_format['percent']
    per_mille_sign = decimal_format['per-mille']
    if any(p.count(percent_sign) + p.count(per_mille_sign) > 1 for p in sub_pictures):
        raise self.error('FODF1310')

    mandatory_digit = decimal_format['zero-digit']
    optional_digit = decimal_format['digit']
    digits_family = ''.join(chr(cp + ord(mandatory_digit)) for cp in range(10))
    if any(optional_digit not in p and all(x not in p for x in digits_family) for p in sub_pictures):
        raise self.error('FODF1310')

    grouping_separator = decimal_format['grouping-separator']
    adjacent_pattern = re.compile(r'[\\%s\\%s]{2}' % (grouping_separator, decimal_separator))
    if any(adjacent_pattern.search(p) for p in sub_pictures):
        raise self.error('FODF1310')

    if math.isnan(value):
        return decimal_format['NaN']

    if isinstance(value, float):
        value = decimal.Decimal.from_float(value)
    elif not isinstance(value, decimal.Decimal):
        value = decimal.Decimal(value)

    if value >= 0:
        fmt_tokens = sub_pictures[0].split(decimal_separator)
        prefix = ''
        chunks = str(value).split(decimal_separator)
    else:
        fmt_tokens = sub_pictures[-1].split(decimal_separator)
        if len(sub_pictures) == 1:
            prefix = decimal_format['minus-sign']
        else:
            prefix = ''
        chunks = str(abs(value)).split(decimal_separator)

    if not fmt_tokens[-1]:
        suffix = ''
    elif fmt_tokens[-1][-1] == percent_sign or fmt_tokens[-1][-1] == per_mille_sign:
        suffix = fmt_tokens[-1][-1]
        fmt_tokens[-1] = fmt_tokens[-1][:-1]
    else:
        suffix = ''

    if math.isnan(value) or abs(value) > 10 ** 28:
        return prefix + decimal_format['infinity'] + suffix

    result = format_digits(chunks[0], fmt_tokens[0], digits_family)
    if len(fmt_tokens) > 1:
        if len(chunks) == 1:
            chunks.append('0')
        result += '.' + format_digits(chunks[1], fmt_tokens[1], digits_family)

    result = result.lstrip(',')
    if decimal_separator in result:
        result = result.lstrip('0')
            
    return prefix + result + suffix


@method(function('format-dateTime', nargs=(2, 5),
                 sequence_types=('xs:dateTime?', 'xs:string', 'xs:string?',
                                 'xs:string?', 'xs:string?', 'xs:string?')))
def evaluate_format_datetime_function(self, context=None):
    value = self.get_argument(context, cls=DateTime10)
    picture = self.get_argument(context, index=1, required=True, cls=str)
    if len(self) not in [2, 5]:
        raise self.error('XPST0017')
    language = self.get_argument(context, index=2, cls=str)
    calendar = self.get_argument(context, index=3, cls=str)
    place = self.get_argument(context, index=4, cls=str)

    if value is None:
        return ''

    try:
        literals, markers = parse_datetime_picture(picture)
    except ElementPathError as err:
        err.token = self
        raise

    if calendar not in {None, 'AD', 'ISO', 'OS'}:
        raise self.error('FOFD1340', f'Invalid calendar argument {calendar!r}')

    # print(value, picture, literals, markers, calendar)
    # breakpoint()

    result = []
    for k in range(len(markers)):
        result.append(literals[k])
        try:
            result.append(parse_datetime_marker(markers[k], value))
        except ElementPathError as err:
            err.token = self
            raise

    result.append(literals[-1])
    return ''.join(result)


@method(function('format-date', nargs=(2, 5),
                 sequence_types=('xs:date?', 'xs:string', 'xs:string?',
                                 'xs:string?', 'xs:string?', 'xs:string?')))
def evaluate_format_date_function(self, context=None):
    value = self.get_argument(context, cls=Date10)
    picture = self.get_argument(context, index=1, required=True, cls=str)
    if len(self) not in [2, 5]:
        raise self.error('XPST0017')
    language = self.get_argument(context, index=2, cls=str)
    calendar = self.get_argument(context, index=3, cls=str)
    place = self.get_argument(context, index=4, cls=str)

    if value is None:
        return ''

    try:
        literals, markers = parse_datetime_picture(picture)
    except ElementPathError as err:
        err.token = self
        raise

    for mrk in markers:
        if mrk[1] in 'HhPmsf':
            msg = 'Invalid date formatting component {!r}'.format(mrk)
            raise self.error('FOFD1350', msg)

    if calendar not in {None, 'AD', 'ISO', 'OS'} and (context is None or calendar != context.default_calendar):
        raise self.error('FOFD1340', f'Invalid calendar argument {calendar!r}')

    print(value, picture, literals, markers)

    result = []
    for k in range(len(markers)):
        result.append(literals[k])
        try:
            result.append(parse_datetime_marker(markers[k], value, lang=language))
        except ElementPathError as err:
            err.token = self
            raise

    result.append(literals[-1])
    return ''.join(result)


@method(function('format-time', nargs=(2, 5),
                 sequence_types=('xs:time?', 'xs:string', 'xs:string?',
                                 'xs:string?', 'xs:string?', 'xs:string?')))
def evaluate_format_time_function(self, context=None):
    value = self.get_argument(context, cls=Time)
    picture = self.get_argument(context, index=1, required=True, cls=str)
    if len(self) not in [2, 5]:
        raise self.error('XPST0017')
    language = self.get_argument(context, index=2, cls=str)
    calendar = self.get_argument(context, index=3, cls=str)
    place = self.get_argument(context, index=4, cls=str)

    if value is None:
        return ''

    try:
        literals, markers = parse_datetime_picture(picture)
    except ElementPathError as err:
        err.token = self
        raise

    for mrk in markers:
        if mrk[1] in 'YMDdFWwCE':
            msg = 'Invalid time formatting component {!r}'.format(mrk)
            raise self.error('FOFD1350', msg)

    if calendar not in {None, 'AD', 'ISO', 'OS'} and calendar != self.parser.default_calendar:
        raise self.error('FOFD1340', f'Invalid calendar argument {calendar!r}')

    print(value, picture, literals, markers)

    result = []
    for k in range(len(markers)):
        result.append(literals[k])
        try:
            result.append(parse_datetime_marker(markers[k], value))
        except ElementPathError as err:
            err.token = self
            raise

    result.append(literals[-1])
    return ''.join(result)


###
# String functions that use regular expressions
@method(function('analyze-string', nargs=(2, 3),
                 sequence_types=('xs:string?', 'xs:string', 'xs:string',
                                 'element(fn:analyze-string-result)')))
def evaluate_analyze_string_function(self, context=None):
    input_string = self.get_argument(context, default='', cls=str)
    pattern = self.get_argument(context, 1, required=True, cls=str)
    flags = 0
    if len(self) > 2:
        for c in self.get_argument(context, 2, required=True, cls=str):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        python_pattern = translate_pattern(pattern, flags, self.parser.xsd_version)
        compiled_pattern = re.compile(python_pattern, flags=flags)
    except (re.error, RegexError) as err:
        msg = "Invalid regular expression: {}"
        raise self.error('FORX0002', msg.format(str(err))) from None
    except OverflowError as err:
        raise self.error('FORX0002', err) from None

    if compiled_pattern.match('') is not None:
        raise self.error('FORX0003', "pattern matches a zero-length string")

    level = 0
    escaped = False
    char_class = False
    group_levels = [0]
    for s in compiled_pattern.pattern:
        if escaped:
            escaped = False
        elif s == '\\':
            escaped = True
        elif char_class:
            if s == ']':
                char_class = False
        elif s == '[':
            char_class = True
        elif s == '(':
            group_levels.append(level)
            level += 1
        elif s == ')':
            level -= 1

    etree = ElementTree if context is None else context.etree
    lines = ['<analyze-string-result xmlns="{}">'.format(XPATH_FUNCTIONS_NAMESPACE)]
    k = 0

    while k < len(input_string):
        match = compiled_pattern.search(input_string, k)
        if match is None:
            lines.append('<non-match>{}</non-match>'.format(input_string[k:]))
            break
        elif not match.groups():
            start, stop = match.span()
            if start > k:
                lines.append('<non-match>{}</non-match>'.format(input_string[k:start]))
            lines.append('<match>{}</match>'.format(input_string[start:stop]))
            k = stop
        else:
            start, stop = match.span()
            if start > k:
                lines.append('<non-match>{}</non-match>'.format(input_string[k:start]))
                k = start

            match_items = []
            group_tmpl = '<group nr="{}">{}'
            empty_group_tmpl = '<group nr="{}"/>'
            unclosed_groups = 0

            for idx in range(1, compiled_pattern.groups + 1):
                start, stop = match.span(idx)
                if start < 0:
                    continue
                elif start > k:
                    if unclosed_groups:
                        for _ in range(unclosed_groups):
                            match_items.append('</group>')
                        unclosed_groups = 0

                    match_items.append(input_string[k:start])

                if start == stop:
                    if group_levels[idx] <= group_levels[idx - 1]:
                        for _ in range(unclosed_groups):
                            match_items.append('</group>')
                        unclosed_groups = 0
                    match_items.append(empty_group_tmpl.format(idx))
                    k = stop
                elif idx == compiled_pattern.groups:
                    k = stop
                    match_items.append(group_tmpl.format(idx, input_string[start:k]))
                    match_items.append('</group>')
                else:
                    next_start = match.span(idx + 1)[0]
                    if next_start < 0 or stop < next_start or stop == next_start \
                            and group_levels[idx + 1] <= group_levels[idx]:
                        k = stop
                        match_items.append(group_tmpl.format(idx, input_string[start:k]))
                        match_items.append('</group>')
                    else:
                        k = next_start
                        match_items.append(group_tmpl.format(idx, input_string[start:k]))
                        unclosed_groups += 1

            for _ in range(unclosed_groups):
                match_items.append('</group>')
            lines.append('<match>{}</match>'.format(''.join(match_items)))

    lines.append('</analyze-string-result>')
    return etree.XML(''.join(lines))


###
# Functions and operators on nodes
@method(function('path', nargs=(0, 1), sequence_types=('node()?', 'xs:string?')))
def evaluate_path_function(self, context=None):
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return None
    elif not self:
        if context.item is None:
            return '/'
        item = context.item
    else:
        item = self.get_argument(context)
        if item is None:
            return None

    if is_document_node(item):
        return '/'
    elif isinstance(item, TypedElement):
        elem = item.elem
    elif is_etree_element(item):
        if is_processing_instruction_node(item):
            name = node_name(item)
            return f'/processing-instruction({name})[{context.position}]'
        elem = item
    else:
        elem = self._elem

    try:
        root = context.root.getroot()
    except AttributeError:
        root = context.root
        path = 'Q{%s}root()' % XPATH_FUNCTIONS_NAMESPACE
    else:
        path = '/%s' % root.tag

    for e, path in etree_iter_paths(root, path):
        if e is elem:
            return path


@method(function('has-children', nargs=(0, 1), sequence_types=('node()?', 'xs:boolean')))
def evaluate_has_children_function(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        if context.item is None:
            return is_document_node(context.root)

        item = context.item
        if not is_xpath_node(item):
            raise self.error('XPTY0004', 'context item must be a node')
    else:
        item = self.get_argument(context)
        if item is None:
            return False
        elif not is_xpath_node(item):
            raise self.error('XPTY0004', 'argument must be a node')

    return is_document_node(item) or \
        is_element_node(item) and not callable(item.tag) and \
        (len(item) > 0 or item.text is not None) or \
        isinstance(item, TypedElement) and (len(item.elem) > 0 or item.elem.text is not None)


@method(function('innermost', nargs=1, sequence_types=('node()*', 'node()*')))
def select_innermost_function(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    nodes = [e for e in self[0].select(context)]
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    ancestors = {x for context.item in nodes for x in context.iter_ancestors(axis='ancestor')}
    results = {x for x in nodes if x not in ancestors}
    yield from context.iter_results(results, namespaces=self.parser.other_namespaces)


@method(function('outermost', nargs=1, sequence_types=('node()*', 'node()*')))
def select_outermost_function(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    nodes = {e for e in self[0].select(context)}
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    results = set()
    for item in nodes:
        context.item = item
        ancestors = {x for x in context.iter_ancestors(axis='ancestor')}
        if any(x in nodes for x in ancestors):
            continue
        results.add(item)
    yield from context.iter_results(results, namespaces=self.parser.other_namespaces)


##
# Functions and operators on sequences
@method(function('head', nargs=1, sequence_types=('item()*', 'item()?')))
def evaluate_head_function(self, context=None):
    for item in self[0].select(context):
        return item


@method(function('tail', nargs=1, sequence_types=('item()*', 'item()?')))
def select_tail_function(self, context=None):
    for k, item in enumerate(self[0].select(context)):
        if k:
            yield item


@method(function('generate-id', nargs=(0, 1), sequence_types=('node()?', 'xs:string')))
def evaluate_generate_id_function(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    if arg is None:
        return ''
    elif not is_xpath_node(arg):
        if self:
            raise self.error('XPTY0004', "argument is not a node")
        raise self.error('XPTY0004', "context item is not a node")
    else:
        return 'ID-{}'.format(id(arg))


@method(function('uri-collection', nargs=(0, 1),
                 sequence_types=('xs:string?', 'xs:anyURI*')))
def evaluate_uri_collection_function(self, context=None):
    uri = self.get_argument(context)
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self or uri is None:
        if context.default_resource_collection is None:
            raise self.error('FODC0002', 'no default resource collection has been defined')
        resource_collection = context.default_resource_collection
    else:
        uri = self.get_absolute_uri(uri)
        try:
            resource_collection = context.resource_collections[uri]
        except (KeyError, TypeError):
            url_parts = urlsplit(uri)
            if url_parts.scheme in ('', 'file') and \
                    not url_parts.path.startswith(':') and url_parts.path.endswith('/'):
                raise self.error('FODC0003', 'collection URI is a directory')
            raise self.error('FODC0002', '{!r} collection not found'.format(uri)) from None

    if not self.parser.match_sequence_type(resource_collection, 'xs:anyURI*'):
        raise self.wrong_sequence_type("Type does not match sequence type xs:anyURI*")

    return resource_collection


@method(function('unparsed-text', nargs=(1, 2),
                 sequence_types=('xs:string?', 'xs:string', 'xs:string?')))
@method(function('unparsed-text-lines', nargs=(1, 2),
                 sequence_types=('xs:string?', 'xs:string', 'xs:string*')))
def evaluate_unparsed_text_functions(self, context=None):
    from urllib.request import urlopen  # optional because it consumes ~4.3 MiB
    from urllib.error import URLError

    href = self.get_argument(context, cls=str)
    if href is None:
        return
    elif urlsplit(href).fragment:
        raise self.error('FOUT1170')

    if len(self) > 1:
        encoding = self.get_argument(context, index=1, required=True, cls=str)
    else:
        encoding = 'UTF-8'

    try:
        uri = self.get_absolute_uri(href)
    except ValueError:
        raise self.error('FOUT1170') from None

    try:
        codecs.lookup(encoding)
    except LookupError:
        raise self.error('FOUT1190') from None

    try:
        with urlopen(uri) as rp:
            obj = rp.read()
    except (ValueError, URLError) as err:
        message = str(err)
        if 'No such file' in message or \
                'unknown url type' in message or 'HTTP Error 404' in message:
            raise self.error('FOUT1170') from None
        raise self.error('FOUT1190') from None

    try:
        text = codecs.decode(obj, encoding)
    except UnicodeDecodeError:
        if len(self) > 1:
            raise self.error('FOUT1190') from None

        try:
            text = codecs.decode(obj, 'UTF-16')
        except UnicodeDecodeError:
            raise self.error('FOUT1190') from None

    if not all(is_xml_codepoint(ord(s)) for s in text):
        raise self.error('FOUT1190')

    text = text.lstrip('\ufeff')

    if self.symbol == 'unparsed-text-lines':
        lines = XML_NEWLINES_PATTERN.split(text)
        return lines[:-1] if lines[-1] == '' else lines

    return text


@method(function('unparsed-text-available', nargs=(1, 2),
                 sequence_types=('xs:string?', 'xs:string', 'xs:boolean')))
def evaluate_unparsed_text_available_function(self, context=None):
    from urllib.request import urlopen  # optional because it consumes ~4.3 MiB
    from urllib.error import URLError

    href = self.get_argument(context, cls=str)
    if href is None:
        return False
    elif urlsplit(href).fragment:
        return False

    if len(self) > 1:
        encoding = self.get_argument(context, index=1, required=True, cls=str)
    else:
        encoding = 'UTF-8'

    try:
        uri = self.get_absolute_uri(href)
        codecs.lookup(encoding)
        with urlopen(uri) as rp:
            obj = rp.read()
    except (ValueError, URLError, LookupError):
        return False

    try:
        return all(is_xml_codepoint(ord(s)) for s in codecs.decode(obj, encoding))
    except UnicodeDecodeError:
        if len(self) > 1:
            return False

        try:
            return all(is_xml_codepoint(ord(s)) for s in codecs.decode(obj, 'UTF-16'))
        except UnicodeDecodeError:
            return False


@method(function('environment-variable', nargs=1,
                 sequence_types=('xs:string', 'xs:string?')))
def evaluate_environment_variable_function(self, context=None):
    name = self.get_argument(context, required=True, cls=str)
    if context is None:
        raise self.missing_context()
    elif not context.allow_environment:
        return
    else:
        return os.environ.get(name)


@method(function('available-environment-variables', nargs=0,
                 sequence_types=('xs:string*',)))
def evaluate_available_environment_variables_function(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not context.allow_environment:
        return
    else:
        return list(os.environ)


###
# Parsing and serializing
@method(function('parse-xml', nargs=1,
                 sequence_types=('xs:string?', 'document-node(element(*))?')))
def evaluate_parse_xml_function(self, context=None):
    # TODO: resolve relative entity references with static base URI
    arg = self.get_argument(context, cls=str)
    if arg is None:
        return []

    etree = ElementTree if context is None else context.etree
    if self.symbol == 'parse-xml-fragment':
        # Wrap argument in a fake document because an
        # XML document can have only one root element
        if not arg.startswith('<?xml '):
            xml_declaration = None
        else:
            xml_declaration, _, arg = arg[6:].partition('?>')
            xml_params = DECL_PARAM_PATTERN.findall(xml_declaration)
            if 'encoding' not in xml_params:
                raise self.error('FODC0006', "'encoding' argument is mandatory")

            for param in xml_params:
                if param not in {'version', 'encoding'}:
                    msg = f'unexpected parameter {param!r} in XML declaration'
                    raise self.error('FODC0006', msg)

        if not arg.lstrip().startswith('<'):
            arg = f'<document>{arg}</document>'
        if arg.lstrip().startswith('<!DOCTYPE'):
            raise self.error('FODC0006', "<!DOCTYPE is not allowed")

    try:
        root = etree.XML(arg)
    except etree.ParseError:
        raise self.error('FODC0006')
    else:
        return etree.ElementTree(root)


@method(function('parse-xml-fragment', nargs=1,
                 sequence_types=('xs:string?', 'document-node()?')))
def evaluate_parse_xml_fragment_function(self, context=None):
    arg = self.get_argument(context, cls=str)
    if arg is None:
        return []

    etree = ElementTree if context is None else context.etree

    # Wrap argument in a fake document because an
    # XML document can have only one root element
    if not arg.startswith('<?xml '):
        xml_declaration = None
    else:
        xml_declaration, _, arg = arg[6:].partition('?>')
        xml_params = DECL_PARAM_PATTERN.findall(xml_declaration)
        if 'encoding' not in xml_params:
            raise self.error('FODC0006', "'encoding' argument is mandatory")

        for param in xml_params:
            if param not in {'version', 'encoding'}:
                msg = f'unexpected parameter {param!r} in XML declaration'
                raise self.error('FODC0006', msg)

    if arg.lstrip().startswith('<!DOCTYPE'):
        raise self.error('FODC0006', "<!DOCTYPE is not allowed")

    try:
        root = etree.XML(arg)
    except etree.ParseError:
        try:
            return etree.XML(f'<document>{arg}</document>')
        except etree.ParseError:
            raise self.error('FODC0006') from None
    else:
        return etree.ElementTree(root)


@method(function('serialize', nargs=(1, 2), sequence_types=(
        'item()*', 'element(output:serialization-parameters)?', 'xs:string')))
def evaluate_serialize_function(self, context=None):
    # TODO full implementation of serialization with
    #  https://www.w3.org/TR/xpath-functions-30/#xslt-xquery-serialization-30

    params = self.get_argument(context, index=1) if len(self) == 2 else None
    if params is None:
        tmpl = '<output:serialization-parameters xmlns:output="{}"/>'
        params = ElementTree.XML(tmpl.format(XSLT_XQUERY_SERIALIZATION_NAMESPACE))
    elif not is_etree_element(params):
        pass
    elif params.tag != SERIALIZATION_PARAMS:
        raise self.error('XPTY0004', 'output:serialization-parameters tag expected')

    if context is None:
        etree = ElementTree
    else:
        etree = context.etree
        if context.namespaces:
            for pfx, uri in context.namespaces.items():
                etree.register_namespace(pfx, uri)
        else:
            for pfx, uri in self.parser.namespaces.items():
                etree.register_namespace(pfx, uri)

    item_separator = ' '
    kwargs = {}
    character_map = {}
    if len(params):
        if len(params) > len({e.tag for e in params}):
            raise self.error('SEPM0019')

        for child in params:
            if child.tag == SER_PARAM_OMIT_XML_DECLARATION:
                value = child.get('value')
                if value not in {'yes', 'no'} or len(child.attrib) > 1:
                    raise self.error('SEPM0017')
                elif value == 'no':
                    kwargs['xml_declaration'] = True

            elif child.tag == SER_PARAM_USE_CHARACTER_MAPS:
                if len(child.attrib):
                    raise self.error('SEPM0017')

                for e in child:
                    if e.tag != SER_PARAM_CHARACTER_MAP:
                        raise self.error('SEPM0017')

                    try:
                        character = e.attrib['character']
                        if character in character_map:
                            msg = 'duplicate character {!r} in character map'
                            raise self.error('SEPM0018', msg.format(character))
                        elif len(character) != 1:
                            msg = 'invalid character {!r} in character map'
                            raise self.error('SEPM0017', msg.format(character))

                        character_map[character] = e.attrib['map-string']
                    except KeyError as key:
                        msg = "missing {} in character map"
                        raise self.error('SEPM0017', msg.format(key)) from None
                    else:
                        if len(e.attrib) > 2:
                            msg = "invalid attribute in character map"
                            raise self.error('SEPM0017', msg)

            elif child.tag == SER_PARAM_METHOD:
                value = child.get('value')
                if value not in {'html', 'xml', 'xhtml', 'text'} or len(child.attrib) > 1:
                    raise self.error('SEPM0017')
                kwargs['method'] = value if value != 'xhtml' else 'html'

            elif child.tag == SER_PARAM_INDENT:
                value = child.get('value')
                if value not in {'yes', 'no'} or len(child.attrib) > 1:
                    raise self.error('SEPM0017')

            elif child.tag == SER_PARAM_ITEM_SEPARATOR:
                try:
                    item_separator = child.attrib['value']
                except KeyError:
                    raise self.error('SEPM0017') from None

            # TODO params
            elif child.tag == SER_PARAM_CDATA:
                pass
            elif child.tag == SER_PARAM_NO_INDENT:
                pass
            elif child.tag == SER_PARAM_STANDALONE:
                pass

            elif child.tag.startswith(f'{{{XSLT_XQUERY_SERIALIZATION_NAMESPACE}'):
                raise self.error('SEPM0017')

    chunks = []
    for item in self[0].select(context):
        if is_document_node(item):
            item = item.getroot()
        elif isinstance(item, TypedElement):
            item = item.elem
        elif isinstance(item, (AttributeNode, TypedAttribute, NamespaceNode)):
            raise self.error('SENR0001')
        elif isinstance(item, TextNode):
            chunks.append(item.value)
            continue
        elif isinstance(item, bool):
            chunks.append('true' if item else 'false')
            continue
        elif not is_etree_element(item):
            chunks.append(str(item))
            continue
        elif hasattr(item, 'xsd_version') or is_schema_node(item):
            continue  # XSD schema or schema node

        try:
            chunks.append(etree.tostring(item, encoding='utf-8', **kwargs).decode('utf-8'))
        except TypeError:
            chunks.append(etree.tostring(item, encoding='utf-8').decode('utf-8'))

    if not character_map:
        return item_separator.join(chunks)

    result = item_separator.join(chunks)
    for character, map_string in character_map.items():
        result = result.replace(character, map_string)
    return result


###
# Higher-order functions

@method(function('function-lookup', nargs=2,
                 sequence_types=('xs:QName', 'xs:integer', 'function(*)?')))
def evaluate_function_lookup_function(self, context=None):
    qname = self.get_argument(context, cls=QName, required=True)
    arity = self.get_argument(context, index=1, cls=int, required=True)
    try:
        return self.parser.symbol_table[qname.local_name](self.parser, nargs=arity)
    except (KeyError, TypeError):
        return []


@method(function('function-name', nargs=1, sequence_types=('function(*)', 'xs:QName?')))
def evaluate_function_name_function(self, context=None):
    if isinstance(self[0], XPathFunction):
        func = self[0]
    else:
        func = self.get_argument(context)

    if not isinstance(func, XPathFunction):
        raise self.error('XPTY0004', "argument is not a function")

    name = func.name
    return [] if name is None else name


@method(function('function-arity', nargs=1, sequence_types=('function(*)', 'xs:integer')))
def evaluate_function_arity_function(self, context=None):
    if isinstance(self[0], XPathFunction):
        return self[0].arity

    func = self.get_argument(context, cls=XPathFunction)
    return func.arity


@method(function('for-each', nargs=2,
                 sequence_types=('item()*', 'function(item()) as item()*', 'item()*')))
def select_for_each_function(self, context=None):
    func = self[1][1] if self[1].symbol == ':' else self[1]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=1, cls=XPathFunction, required=True)

    for item in self[0].select(copy(context)):
        result = func(context, argument_list=[item])
        if isinstance(result, list):
            yield from result
        else:
            yield result


@method(function('filter', nargs=2,
                 sequence_types=('item()*', 'function(item()) as xs:boolean', 'item()*')))
def select_filter_function(self, context=None):
    func = self[1][1] if self[1].symbol == ':' else self[1]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=1, cls=XPathFunction)

    if func.nargs == 0:
        raise self.error('XPTY0004', f'invalid number of arguments {func.nargs}')

    for item in self[0].select(copy(context)):
        cond = func(context, argument_list=[item])
        if not isinstance(cond, bool):
            raise self.error('XPTY0004', 'a single boolean value required')
        if cond:
            yield item


@method(function('fold-left', nargs=3,
                 sequence_types=('item()*', 'item()*',
                                 'function(item()*, item()) as item()*', 'item()*')))
def select_fold_left_function(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)
    zero = self.get_argument(context, index=1)

    result = zero
    for item in self[0].select(copy(context)):
        result = func(context, argument_list=[result, item])

    if isinstance(result, list):
        yield from result
    else:
        yield result


@method(function('fold-right', nargs=3,
                 sequence_types=('item()*', 'item()*',
                                 'function(item()*, item()) as item()*', 'item()*')))
def select_fold_right_function(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)
    zero = self.get_argument(context, index=1)

    result = zero
    sequence = [x for x in self[0].select(copy(context))]

    for item in reversed(sequence):
        result = func(context, argument_list=[item, result])

    if isinstance(result, list):
        yield from result
    else:
        yield result


@method(function('for-each-pair', nargs=3,
                 sequence_types=('item()*', 'item()*',
                                 'function(item(), item()) as item()*', 'item()*')))
def select_for_each_pair_function(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)

    if not isinstance(func, XPathFunction):
        raise self.error('XPTY0004', "invalid type for 3rd argument {!r}".format(func))
    elif func.arity != 2:
        raise self.error('XPTY0004', "function arity of 3rd argument must be 2")

    for item1, item2 in zip(self[0].select(copy(context)), self[1].select(copy(context))):
        result = func(context, argument_list=[item1, item2])
        if isinstance(result, list):
            yield from result
        else:
            yield result


@method(function('namespace-node', nargs=0, label='kind test'))
def select_namespace_node_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()
    elif isinstance(context.item, NamespaceNode):
        yield context.item


###
# Redefined or extended functions
XPath30Parser.unregister('data')
XPath30Parser.unregister('document-uri')
XPath30Parser.unregister('nilled')
XPath30Parser.unregister('node-name')
XPath30Parser.unregister('string-join')
XPath30Parser.unregister('round')


@method(function('data', nargs=(0, 1), sequence_types=('item()*', 'xs:anyAtomicType*')))
def select_data_function(self, context=None):
    if not self:
        items = [self.get_argument(context, default_to_context=True)]
    else:
        items = self[0].select(context)

    for item in items:
        value = self.data_value(item)
        if value is None:
            raise self.error('FOTY0012', "argument node does not have a typed value")
        else:
            yield value


@method(function('document-uri', nargs=(0, 1), sequence_types=('node()?', 'xs:anyURI?')))
def evaluate_document_uri_function(self, context=None):
    if context is None:
        raise self.missing_context()

    arg = self.get_argument(context, default_to_context=True)
    if arg is None or not is_document_node(arg):
        return

    uri = node_document_uri(arg)
    if uri is not None:
        return AnyURI(uri)
    elif is_document_node(context.root):
        try:
            for uri, doc in context.documents.items():
                if doc is context.root:
                    return AnyURI(uri)
        except AttributeError:
            pass


@method(function('nilled', nargs=(0, 1), sequence_types=('node()?', 'xs:boolean?')))
def evaluate_nilled_function(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    if arg is None:
        return
    elif not is_xpath_node(arg):
        raise self.error('XPTY0004', 'an XPath node required')
    return node_nilled(arg)


@method(function('node-name', nargs=(0, 1), sequence_types=('node()?', 'xs:QName?')))
def evaluate_node_name_function(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    if arg is None:
        return
    elif not is_xpath_node(arg):
        raise self.error('XPTY0004', 'an XPath node required')

    name = node_name(arg)
    if name is None:
        return
    elif name.startswith('{'):
        # name is a QName in extended format
        namespace, local_name = split_expanded_name(name)
        for pfx, uri in self.parser.namespaces.items():
            if uri == namespace:
                return QName(uri, '{}:{}'.format(pfx, local_name))
        raise self.error('FONS0004', 'no prefix found for namespace {}'.format(namespace))
    else:
        # name is a local name
        return QName(self.parser.namespaces.get('', ''), name)


@method(function('string-join', nargs=(1, 2),
                 sequence_types=('xs:string*', 'xs:string', 'xs:string')))
def evaluate_string_join_function(self, context=None):
    items = [self.string_value(s) for s in self[0].select(context)]
    return self.get_argument(context, 1, default='', cls=str).join(items)


@method(function('round', nargs=(1, 2),
                 sequence_types=('numeric?', 'xs:integer', 'numeric?')))
def evaluate_round_function(self, context=None):
    arg = self.get_argument(context)
    if arg is None:
        return []
    elif is_xpath_node(arg) or self.parser.compatibility_mode:
        arg = self.number_value(arg)

    if isinstance(arg, float) and (math.isnan(arg) or math.isinf(arg)):
        return arg

    precision = self.get_argument(context, index=1, default=0, cls=int)
    try:
        if precision < 0:
            return type(arg)(round(arg, precision))

        number = decimal.Decimal(arg)
        exponent = decimal.Decimal('1') / 10 ** precision
        if number > 0:
            return type(arg)(number.quantize(exponent, rounding='ROUND_HALF_UP'))
        else:
            return type(arg)(number.quantize(exponent, rounding='ROUND_HALF_DOWN'))
    except TypeError as err:
        raise self.error('FORG0006', err) from None
    except decimal.InvalidOperation:
        if isinstance(arg, str):
            raise self.error('XPTY0004') from None
        return round(arg)
    except decimal.DecimalException as err:
        raise self.error('FOCA0002', err) from None


#
# XSD list-based constructors

@XPath30Parser.constructor('NMTOKENS', sequence_types=('xs:NMTOKEN*',))
def cast_string_based_types(self, value):
    cast_func = xsd10_atomic_types['NMTOKEN']
    if isinstance(value, UntypedAtomic):
        values = value.value.split() or [value.value]
    else:
        values = value.split() or [value]

    try:
        return [cast_func(x) for x in values]
    except ValueError as err:
        raise self.error('FORG0001', err)


@XPath30Parser.constructor('IDREFS', sequence_types=('xs:IDREF*',))
def cast_string_based_types(self, value):
    cast_func = xsd10_atomic_types['IDREF']
    if isinstance(value, UntypedAtomic):
        values = value.value.split() or [value.value]
    else:
        values = value.split() or [value]

    try:
        return [cast_func(x) for x in values]
    except ValueError as err:
        raise self.error('FORG0001', err)


@XPath30Parser.constructor('ENTITIES', sequence_types=('xs:ENTITY*',))
def cast_string_based_types(self, value):
    cast_func = xsd10_atomic_types['ENTITY']
    if isinstance(value, UntypedAtomic):
        values = value.value.split() or [value.value]
    else:
        values = value.split() or [value]

    try:
        return [cast_func(x) for x in values]
    except ValueError as err:
        raise self.error('FORG0001', err)

