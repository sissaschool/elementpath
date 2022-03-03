#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
"""
XPath 1.0 implementation - part 3 (functions)
"""
import sys
import math
import decimal
from ..datatypes import Duration, DayTimeDuration, YearMonthDuration, \
    StringProxy, AnyURI, Float10
from ..namespaces import XML_ID, XML_LANG, get_prefixed_name
from ..xpath_nodes import TextNode, is_xpath_node, is_document_node, \
    is_element_node, is_comment_node, is_processing_instruction_node, node_name
from ..xpath_token import XPathFunction

from ._xpath1_operators import XPath1Parser

method = XPath1Parser.method
function = XPath1Parser.function


###
# Kind tests (for matching of node types in XPath 1.0 or sequence types in XPath 2.0)
@method(function('node', nargs=0, label='kind test'))
def select_node_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    for item in context.iter_children_or_self():
        if item is None:
            yield context.root
        elif is_xpath_node(item):
            yield item


@method('node')
def nud_item_sequence_type(self):
    XPathFunction.nud(self)
    if self.parser.next_token.symbol in ('*', '+', '?'):
        self.occurrence = self.parser.next_token.symbol
        self.parser.advance()
    return self


@method(function('processing-instruction', nargs=(0, 1), bp=79, label='kind test'))
def select_pi_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    for item in context.iter_children_or_self():
        if is_processing_instruction_node(item):
            if not self:
                yield item
            else:
                name = self[0].value
                if hasattr(item, 'target'):
                    target = item.target
                else:
                    target = item.text.split()[0] if item.text else ''

                if target == ' '.join(name.strip().split()):
                    yield item


@method('processing-instruction')
def nud_pi_kind_test(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol != ')':
        self.parser.next_token.expected('(name)', '(string)')
        self[0:] = self.parser.expression(5),
    self.parser.advance(')')
    self.value = None
    return self


@method(function('comment', nargs=0, label='kind test'))
def select_comment_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    for item in context.iter_children_or_self():
        if is_comment_node(item):
            yield item


@method(function('text', nargs=0, label='kind test'))
def select_text_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    for item in context.iter_children_or_self():
        if isinstance(item, TextNode):
            yield item


###
# Node set functions
@method(function('last', nargs=0, sequence_types=('xs:integer',)))
def evaluate_last_function(self, context=None):
    if context is None:
        raise self.missing_context()
    return context.size


@method(function('position', nargs=0,
                 sequence_types=('xs:integer',)))
def evaluate_position_function(self, context=None):
    if context is None:
        raise self.missing_context()
    return context.position


@method(function('count', nargs=1, sequence_types=('item()*', 'xs:integer')))
def evaluate_count_function(self, context=None):
    return len([x for x in self[0].select(context)])


@method(function('id', nargs=1, sequence_types=('xs:string*', 'element()*')))
def select_id_function(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        value = self[0].evaluate(context)
        item = context.item
        if item is None:
            item = context.root

        if is_element_node(item) or is_document_node(item):
            yield from filter(lambda e: e.get(XML_ID) == value, item.iter())


@method(function('name', nargs=(0, 1), sequence_types=('node()?', 'xs:string')))
@method(function('local-name', nargs=(0, 1), sequence_types=('node()?', 'xs:string')))
@method(function('namespace-uri', nargs=(0, 1), sequence_types=('node()?', 'xs:anyURI')))
def evaluate_name_related_functions(self, context=None):
    if context is None:
        raise self.missing_context()

    arg = self.get_argument(context, default_to_context=True)
    if arg is None:
        return ''
    elif not is_xpath_node(arg):
        raise self.error('XPTY0004')

    name = node_name(arg)
    if name is None:
        return ''

    symbol = self.symbol
    if symbol == 'name':
        nsmap = getattr(arg, 'nsmap', self.parser.namespaces)
        return get_prefixed_name(name, nsmap)
    elif symbol == 'local-name':
        return name if not name or name[0] != '{' else name.split('}')[1]
    elif self.parser.version == '1.0':
        return '' if not name or name[0] != '{' else name.split('}')[0][1:]
    else:
        return AnyURI('') if not name or name[0] != '{' else AnyURI(name.split('}')[0][1:])


###
# String functions
@method(function('string', nargs=(0, 1), sequence_types=('item()?', 'xs:string')))
def evaluate_string_function(self, context=None):
    if not self:
        if context is None:
            raise self.missing_context()
        return self.string_value(context.item)
    return self.string_value(self.get_argument(context))


@method(function('contains', nargs=2,
                 sequence_types=('xs:string?', 'xs:string?', 'xs:boolean')))
def evaluate_contains_function(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)
    return arg2 in arg1


@method(function('concat', nargs=(2, None),
                 sequence_types=('xs:anyAtomicType?', 'xs:anyAtomicType?', 'xs:string')))
def evaluate_concat_function(self, context=None):
    return ''.join(self.string_value(self.get_argument(context, index=k))
                   for k in range(len(self)))


@method(function('string-length', nargs=(0, 1),
                 sequence_types=('xs:string?', 'xs:integer')))
def evaluate_string_length_function(self, context=None):
    if self:
        return len(self.get_argument(context, default_to_context=True, default='', cls=str))

    try:
        return len(self.string_value(context.item))
    except AttributeError:
        raise self.missing_context() from None


@method(function('normalize-space', nargs=(0, 1),
                 sequence_types=('xs:string?', 'xs:string')))
def evaluate_normalize_space_function(self, context=None):
    if self.parser.version == '1.0' or not self:
        arg = self.string_value(self.get_argument(context, default_to_context=True, default=''))
    else:
        arg = self.get_argument(context, default_to_context=True, default='', cls=str)
    return ' '.join(arg.strip().split())


@method(function('starts-with', nargs=2,
                 sequence_types=('xs:string?', 'xs:string?', 'xs:boolean')))
def evaluate_starts_with_function(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)
    return arg1.startswith(arg2)


@method(function('translate', nargs=3,
                 sequence_types=('xs:string?', 'xs:string', 'xs:string', 'xs:string')))
def evaluate_translate_function(self, context=None):
    arg = self.get_argument(context, default='', cls=str)

    map_string = self.get_argument(context, index=1, cls=str)
    if map_string is None:
        message = "the 2nd argument of fn:translate() cannot be the empty sequence"
        raise self.error('XPTY0004', message)

    trans_string = self.get_argument(context, index=2, cls=str)
    if trans_string is None:
        message = "the 3rd argument of fn:translate() cannot be the empty sequence"
        raise self.error('XPTY0004', message)

    if len(map_string) == len(trans_string):
        return arg.translate(str.maketrans(map_string, trans_string))
    elif len(map_string) > len(trans_string):
        k = len(trans_string)
        return arg.translate(str.maketrans(map_string[:k], trans_string, map_string[k:]))
    else:
        return arg.translate(str.maketrans(map_string, trans_string[:len(map_string)]))


@method(function('substring', nargs=(2, 3),
                 sequence_types=('xs:string?', 'xs:double', 'xs:double', 'xs:string')))
def evaluate_substring_function(self, context=None):
    item = self.get_argument(context, default='', cls=str)
    start = self.get_argument(context, index=1)
    try:
        if math.isnan(start) or math.isinf(start):
            return ''
    except TypeError:
        raise self.error('FORG0006', "the second argument must be xs:numeric") from None
    else:
        start = int(round(start)) - 1

    if len(self) == 2:
        return item[max(start, 0):]
    else:
        length = self.get_argument(context, index=2)
        try:
            if math.isnan(length) or length <= 0:
                return ''
        except TypeError:
            raise self.error('FORG0006', "the third argument must be xs:numeric") from None

        if math.isinf(length):
            return item[max(start, 0):]
        else:
            stop = start + int(round(length))
            return item[slice(max(start, 0), max(stop, 0))]


@method(function('substring-before', nargs=2,
                 sequence_types=('xs:string?', 'xs:string?', 'xs:string')))
@method(function('substring-after', nargs=2,
                 sequence_types=('xs:string?', 'xs:string?', 'xs:string')))
def evaluate_substring_before_or_after_functions(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)

    index = arg1.find(arg2)
    if index < 0:
        return ''
    if self.symbol == 'substring-before':
        return arg1[:index]
    else:
        return arg1[index + len(arg2):]


###
# Boolean functions
@method(function('boolean', nargs=1,
                 sequence_types=('item()*', 'xs:boolean')))
def evaluate_boolean_function(self, context=None):
    return self.boolean_value([x for x in self[0].select(context)])


@method(function('not', nargs=1, sequence_types=('item()*', 'xs:boolean')))
def evaluate_not_function(self, context=None):
    return not self.boolean_value([x for x in self[0].select(context)])


@method(function('true', nargs=0, sequence_types=('xs:boolean',)))
def evaluate_true_function(self, context=None):
    return True


@method(function('false', nargs=0, sequence_types=('xs:boolean',)))
def evaluate_false_function(self, context=None):
    return False


@method(function('lang', nargs=1,
                 sequence_types=('xs:string?', 'xs:boolean')))
def evaluate_lang_function(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not is_element_node(context.item):
        return False
    else:
        try:
            lang = context.item.attrib[XML_LANG].strip()
        except KeyError:
            for elem in context.iter_ancestors():
                try:
                    if XML_LANG in elem.attrib:
                        lang = elem.attrib[XML_LANG]
                        break
                except AttributeError:
                    pass  # is a document node
            else:
                return False

        if '-' in lang:
            lang, _ = lang.split('-')
        return lang.lower() == self[0].evaluate().lower()


###
# Number functions
@method(function('number', nargs=(0, 1), sequence_types=('xs:anyAtomicType?', 'xs:double')))
def evaluate_number_function(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    try:
        return float(self.string_value(arg) if is_xpath_node(arg) else arg)
    except (TypeError, ValueError):
        return float('nan')


@method(function('sum', nargs=(1, 2),
                 sequence_types=('xs:anyAtomicType*', 'xs:anyAtomicType?', 'xs:anyAtomicType?')))
def evaluate_sum_function(self, context=None):
    try:
        values = [float(self.string_value(x)) if is_xpath_node(x) else x
                  for x in self[0].select(context)]
    except (TypeError, ValueError):
        if self.parser.version == '1.0':
            return float('nan')
        raise self.error('FORG0006') from None

    if not values:
        zero = 0 if len(self) == 1 else self.get_argument(context, index=1)
        return [] if zero is None else zero

    if all(isinstance(x, (decimal.Decimal, int)) for x in values):
        return sum(values) if len(values) > 1 else values[0]
    elif all(isinstance(x, DayTimeDuration) for x in values) or \
            all(isinstance(x, YearMonthDuration) for x in values):
        if sys.version_info >= (3, 8):
            return sum(values[1:], start=values[0])
        result = values[0]
        for val in values[1:]:
            result += val
        return result
    elif any(isinstance(x, Duration) for x in values):
        raise self.error('FORG0006', 'invalid sum of duration values')
    elif any(isinstance(x, (StringProxy, AnyURI)) for x in values):
        raise self.error('FORG0006', 'cannot apply fn:sum() to string-based types')
    elif any(isinstance(x, float) and math.isnan(x) for x in values):
        return float('nan')
    elif all(isinstance(x, Float10) for x in values):
        return sum(values)

    try:
        return sum(self.number_value(x) for x in values)
    except TypeError:
        if self.parser.version == '1.0':
            return float('nan')
        raise self.error('FORG0006') from None


@method(function('ceiling', nargs=1, sequence_types=('numeric?', 'numeric?')))
@method(function('floor', nargs=1, sequence_types=('numeric?', 'numeric?')))
def evaluate_ceiling_and_floor_functions(self, context=None):
    arg = self.get_argument(context)
    if arg is None:
        return float('nan') if self.parser.version == '1.0' else []
    elif is_xpath_node(arg) or self.parser.compatibility_mode:
        arg = self.number_value(arg)

    try:
        if math.isnan(arg) or math.isinf(arg):
            return arg

        if self.symbol == 'floor':
            return type(arg)(math.floor(arg))
        else:
            return type(arg)(math.ceil(arg))
    except TypeError as err:
        if isinstance(arg, str):
            raise self.error('XPTY0004', err) from None
        raise self.error('FORG0006', err) from None


@method(function('round', nargs=1, sequence_types=('numeric?', 'numeric?')))
def evaluate_round_function(self, context=None):
    arg = self.get_argument(context)
    if arg is None:
        return float('nan') if self.parser.version == '1.0' else []
    elif is_xpath_node(arg) or self.parser.compatibility_mode:
        arg = self.number_value(arg)

    if isinstance(arg, float) and (math.isnan(arg) or math.isinf(arg)):
        return arg

    try:
        number = decimal.Decimal(arg)
        if number > 0:
            return type(arg)(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_UP'))
        else:
            return type(arg)(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_DOWN'))
    except TypeError as err:
        raise self.error('FORG0006', err) from None
    except decimal.InvalidOperation:
        if isinstance(arg, str):
            raise self.error('XPTY0004') from None
        return round(arg)
    except decimal.DecimalException as err:
        raise self.error('FOCA0002', err) from None

# XPath 1.0 definitions continue into module xpath1_axes
