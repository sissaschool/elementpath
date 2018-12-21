# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPath 2.0 implementation - part 3 (XSD constructors and multi-role tokens)
"""
import decimal
import codecs

from .compat import unicode_type, urlparse, URLError, string_base_type
from .exceptions import ElementPathMissingContextError
from .xpath_helpers import is_attribute_node, boolean_value, string_value
from .datatypes import DateTime, Date, Time, GregorianDay, GregorianMonth, GregorianMonthDay, \
    GregorianYear, GregorianYearMonth, UntypedAtomic, Duration, YearMonthDuration, DayTimeDuration
from .xpath2_functions import XPath2Parser, WHITESPACES_RE_PATTERN, QNAME_PATTERN, \
    NMTOKEN_PATTERN, NAME_PATTERN, NCNAME_PATTERN, HEX_BINARY_PATTERN, \
    NOT_BASE64_BINARY_PATTERN, LANGUAGE_CODE_PATTERN, WRONG_ESCAPE_PATTERN


def collapse_white_spaces(s):
    return WHITESPACES_RE_PATTERN.sub(' ', s).strip()


register = XPath2Parser.register
unregister = XPath2Parser.unregister
method = XPath2Parser.method
constructor = XPath2Parser.constructor


###
# XSD constructor functions
@method(constructor('normalizedString'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    return [] if item is None else str(item).replace('\t', ' ').replace('\n', ' ')


@method(constructor('token'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    return [] if item is None else collapse_white_spaces(item)


@method(constructor('language'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    else:
        match = LANGUAGE_CODE_PATTERN.match(collapse_white_spaces(item))
        if match is None:
            raise self.error('FOCA0002', "%r is not a language code" % item)
        return match.group()


@method(constructor('NMTOKEN'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    else:
        match = NMTOKEN_PATTERN.match(collapse_white_spaces(item))
        if match is None:
            raise self.error('FOCA0002', "%r is not an xs:NMTOKEN value" % item)
        return match.group()


@method(constructor('Name'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    else:
        match = NAME_PATTERN.match(collapse_white_spaces(item))
        if match is None:
            raise self.error('FOCA0002', "%r is not an xs:Name value" % item)
        return match.group()


@method(constructor('NCName'))
@method(constructor('ID'))
@method(constructor('IDREF'))
@method(constructor('ENTITY'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    else:
        match = NCNAME_PATTERN.match(collapse_white_spaces(item))
        if match is None:
            raise self.error('FOCA0002', "%r is not an xs:%s value" % (item, self.symbol))
        return match.group()


@method(constructor('anyURI'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    uri = collapse_white_spaces(item)
    try:
        urlparse(uri)
    except URLError:
        raise self.error('FOCA0002', "%r is not an xs:anyURI value" % item)
    if uri.count('#') > 1:
        raise self.error('FOCA0002', "%r is not an xs:anyURI value (too many # characters)" % item)
    elif WRONG_ESCAPE_PATTERN.search(uri):
        raise self.error('FOCA0002', "%r is not an xs:anyURI value (wrong escaping)" % item)
    return uri


@method(constructor('decimal'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return [] if item is None else decimal.Decimal(item)
    except (ValueError, decimal.DecimalException) as err:
        raise self.error("FORG0001", str(err))


@method(constructor('integer'))
def evaluate(self, context=None):
    return self.integer(context)


@method(constructor('nonNegativeInteger'))
def evaluate(self, context=None):
    return self.integer(context, 0)


@method(constructor('positiveInteger'))
def evaluate(self, context=None):
    return self.integer(context, 1)


@method(constructor('nonPositiveInteger'))
def evaluate(self, context=None):
    return self.integer(context, higher_bound=1)


@method(constructor('negativeInteger'))
def evaluate(self, context=None):
    return self.integer(context, higher_bound=0)


@method(constructor('long'))
def evaluate(self, context=None):
    return self.integer(context, -2**127, 2**127)


@method(constructor('int'))
def evaluate(self, context=None):
    return self.integer(context, -2**63, 2**63)


@method(constructor('short'))
def evaluate(self, context=None):
    return self.integer(context, -2**15, 2**15)


@method(constructor('byte'))
def evaluate(self, context=None):
    return self.integer(context, -2**7, 2**7)


@method(constructor('unsignedLong'))
def evaluate(self, context=None):
    return self.integer(context, 0, 2**128)


@method(constructor('unsignedInt'))
def evaluate(self, context=None):
    return self.integer(context, 0, 2**64)


@method(constructor('unsignedShort'))
def evaluate(self, context=None):
    return self.integer(context, 0, 2**16)


@method(constructor('unsignedByte'))
def evaluate(self, context=None):
    return self.integer(context, 0, 2**8)


@method(constructor('double'))
@method(constructor('float'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return [] if item is None else float(item)
    except ValueError as err:
        raise self.error("FORG0001", str(err))


@method(constructor('dateTime'))
def evaluate(self, context=None):
    return self.datetime(context, DateTime)


@method(constructor('date'))
def evaluate(self, context=None):
    return self.datetime(context, Date)


@method(constructor('gDay'))
def evaluate(self, context=None):
    return self.datetime(context, GregorianDay)


@method(constructor('gMonth'))
def evaluate(self, context=None):
    return self.datetime(context, GregorianMonth)


@method(constructor('gMonthDay'))
def evaluate(self, context=None):
    return self.datetime(context, GregorianMonthDay)


@method(constructor('gYear'))
def evaluate(self, context=None):
    return self.datetime(context, GregorianYear)


@method(constructor('gYearMonth'))
def evaluate(self, context=None):
    return self.datetime(context, GregorianYearMonth)


@method(constructor('time'))
def evaluate(self, context=None):
    return self.datetime(context, Time)


@method(constructor('duration'))
def evaluate(self, context=None):
    return self.duration(context, Duration)


@method(constructor('yearMonthDuration'))
def evaluate(self, context=None):
    return self.duration(context, YearMonthDuration)


@method(constructor('dayTimeDuration'))
def evaluate(self, context=None):
    return self.duration(context, DayTimeDuration)


@method(constructor('base64Binary'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, UntypedAtomic):
        return codecs.encode(unicode_type(item), 'base64')
    elif not isinstance(item, (bytes, unicode_type)):
        raise self.error('FORG0006', 'the argument has an invalid type %r' % type(item))
    elif not isinstance(item, bytes) or self[0].label == 'literal':
        return codecs.encode(item.encode('ascii'), 'base64')
    elif HEX_BINARY_PATTERN.search(item.decode('utf-8')):
        value = codecs.decode(item, 'hex') if str is not bytes else item
        return codecs.encode(value, 'base64')
    elif NOT_BASE64_BINARY_PATTERN.search(item.decode('utf-8')):
        return codecs.encode(item, 'base64')
    else:
        return item


@method(constructor('hexBinary'))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, UntypedAtomic):
        return codecs.encode(unicode_type(item), 'hex')
    elif not isinstance(item, (bytes, unicode_type)):
        raise self.error('FORG0006', 'the argument has an invalid type %r' % type(item))
    elif not isinstance(item, bytes) or self[0].label == 'literal':
        return codecs.encode(item.encode('ascii'), 'hex')
    elif HEX_BINARY_PATTERN.search(item.decode('utf-8')):
        return item if isinstance(item, bytes) or str is bytes else codecs.encode(item.encode('ascii'), 'hex')
    else:
        try:
            value = codecs.decode(item, 'base64')
        except ValueError:
            return codecs.encode(item, 'hex')
        else:
            return codecs.encode(value, 'hex')


###
# Multi role-tokens cases
#

# Case 1: In XPath 2.0 the 'attribute' keyword is used both for attribute:: axis and
# attribute() node type function.
#
# First the XPath1 token class has to be removed from the XPath2 symbol table. Then the
# symbol has to be registered usually with the same binding power (bp --> lbp, rbp), a
# multi-value label (using a tuple of values) and a custom pattern. Finally a custom nud
# or led method is required.
unregister('attribute')
register('attribute', lbp=90, rbp=90, label=('function', 'axis'),
         pattern=r'\battribute(?=\s*\:\:|\s*\(\:.*\:\)\s*\:\:|\s*\(|\s*\(\:.*\:\)\()')


@method('attribute')
def nud(self):
    if self.parser.next_token.symbol == '::':
        self.parser.advance('::')
        self.parser.next_token.expected(
            '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
            'attribute', 'schema-attribute', 'element', 'schema-element'
        )
        self[:] = self.parser.expression(rbp=90),
        self.label = 'axis'
    else:
        self.parser.advance('(')
        if self.parser.next_token.symbol != ')':
            self[:] = self.parser.expression(5),
            if self.parser.next_token.symbol == ',':
                self.parser.advance(',')
                self[1:] = self.parser.expression(5),
        self.parser.advance(')')
        self.label = 'function'
    return self


@method('attribute')
def select(self, context=None):
    if context is None:
        return
    elif self.label == 'axis':
        for _ in context.iter_attributes():
            for result in self[0].select(context):
                yield result
    else:
        attribute_name = self[0].evaluate(context) if self else None
        for item in context.iter_attributes():
            if is_attribute_node(item, attribute_name):
                yield context.item[1]


@method('attribute')
def evaluate(self, context=None):
    if context is not None:
        if is_attribute_node(context.item, self[0].evaluate(context) if self else None):
            return context.item[1]


# Case 2: In XPath 2.0 the 'boolean' keyword is used both for boolean() function and
# for boolean() constructor.
unregister('boolean')
register('boolean', lbp=90, rbp=90, label=('function', 'constructor'),
         pattern=r'\bboolean(?=\s*\(|\s*\(\:.*\:\)\()')


@method('boolean')
def nud(self):
    self.parser.advance('(')
    self[0:] = self.parser.expression(5),
    self.parser.advance(')')

    try:
        self.value = self.evaluate()  # Static context evaluation
    except ElementPathMissingContextError:
        self.value = None
    return self


@method('boolean')
def evaluate(self, context=None):
    if self.label == 'function':
        return boolean_value(self[0].get_results(context))

    # xs:boolean constructor
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, bool):
        return item
    elif isinstance(item, (int, float, decimal.Decimal)):
        return bool(item)
    elif isinstance(item, UntypedAtomic):
        item = string_base_type(item)
    elif not isinstance(item, string_base_type):
        raise self.error('FORG0006', 'the argument has an invalid type %r' % type(item))

    if item in ('true', '1'):
        return True
    elif item in ('false', '0'):
        return False
    else:
        raise self.error('FOCA0002', "%r: not a boolean value" % item)


# Case 3: In XPath 2.0 the 'string' keyword is used both for fn:string() and xs:string().
unregister('string')
register('string', lbp=90, rbp=90, label=('function', 'constructor'),
         pattern=r'\bstring(?=\s*\(|\s*\(\:.*\:\)\()')


@method('string')
def nud(self):
    self.parser.advance('(')
    self[0:] = self.parser.expression(5),

    self.parser.advance(')')

    try:
        self.value = self.evaluate()  # Static context evaluation
    except ElementPathMissingContextError:
        self.value = None
    return self


@method('string')
def evaluate(self, context=None):
    if self.label == 'function':
        return string_value(self.get_argument(context))
    else:
        item = self.get_argument(context)
        return [] if item is None else str(item)


# Case 4: In XPath 2.0 the 'QName' keyword is used both for fn:QName() and xs:QName().
# In this case the label is set by the nud method, in dependence of the number of args.
register('QName', lbp=90, rbp=90, label=('function', 'constructor'),
         pattern=r'\bQName(?=\s*\(|\s*\(\:.*\:\)\()')


@method('QName')
def nud(self):
    self.parser.advance('(')
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol == ',':
        self.label = 'function'
        self.parser.advance(',')
        self[1:] = self.parser.expression(5),
    else:
        self.label = 'constructor'
    self.parser.advance(')')

    try:
        self.value = self.evaluate()  # Static context evaluation
    except ElementPathMissingContextError:
        self.value = None
    return self


@method('QName')
def evaluate(self, context=None):
    if self.label == 'constructor':
        item = self.get_argument(context)
        if item is None:
            return []
        elif not isinstance(item, string_base_type):
            raise self.error('FORG0006', 'the argument has an invalid type %r' % type(item))
        match = QNAME_PATTERN.match(item)
        if match is None:
            raise self.error('FOCA0002', 'the argument must be an xs:QName')

        pfx = match.groupdict()['prefix'] or ''
        if pfx and pfx not in self.parser.namespaces:
            raise self.error('FONS0004', 'No namespace found for prefix %r' % pfx)
        return item

    else:
        uri = self.get_argument(context)
        if uri is None:
            uri = ''
        elif not isinstance(uri, string_base_type):
            raise self.error('FORG0006', '1st argument has an invalid type %r' % type(uri))

        qname = self[1].evaluate(context)
        if not isinstance(qname, string_base_type):
            raise self.error('FORG0006', '2nd argument has an invalid type %r' % type(qname))
        match = QNAME_PATTERN.match(qname)
        if match is None:
            raise self.error('FOCA0002', '2nd argument must be an xs:QName')

        pfx = match.groupdict()['prefix'] or ''
        if not uri:
            if pfx:
                raise self.error('FOCA0002', 'must be a local name when the parameter URI is empty')
        else:
            try:
                if uri != self.parser.namespaces[pfx]:
                    raise self.error('FOCA0002', 'prefix %r is already is used for another namespace' % pfx)
            except KeyError:
                self.parser.namespaces[pfx] = uri
        return qname


XPath2Parser.build_tokenizer()  # XPath 2.0 definitions completed, build the tokenizer.
