# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from __future__ import unicode_literals
import locale
from .compat import PY3


class ElementPathError(Exception):
    """
    Base exception class for elementpath package.

    :param message: the message related to the error.
    :param code: an optional error code.
    :param token: an optional token instance related with the error.
    """
    def __init__(self, message, code=None, token=None):
        super(ElementPathError, self).__init__(message)
        self.message = message
        self.code = code
        self.token = token

    def __str__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        if self.code is None:
            return self.message if self.token is None else '%s: %s.' % (self.token, self.message)
        elif self.token is None:
            return '[%s] %s.' % (self.code, self.message)
        else:
            return '%s: [%s] %s.' % (self.token, self.code, self.message)

    if PY3:
        __str__ = __unicode__


class MissingContextError(ElementPathError):
    """Raised when the dynamic context is required for evaluate the XPath expression."""


class ElementPathNameError(ElementPathError, NameError):
    pass


class ElementPathKeyError(ElementPathError, KeyError):
    pass


class ElementPathSyntaxError(ElementPathError, SyntaxError):
    pass


class ElementPathTypeError(ElementPathError, TypeError):
    pass


class ElementPathValueError(ElementPathError, ValueError):
    pass


class ElementPathLocaleError(ElementPathError, locale.Error):
    pass


def xpath_error(code, message=None, token=None, prefix='err'):
    """
    Returns an XPath error instance related with a code. An XPath/XQuery/XSLT error code
    (ref: https://www.w3.org/2005/xqt-errors/) is an alphanumeric token starting with four
    uppercase letters and ending with four digits.

    :param code: the error code.
    :param message: an optional custom additional message.
    :param token: an optional token instance.
    :param prefix: the namespace prefix to apply to the error code, defaults to 'err'.
    """
    if ':' not in code:
        pcode = '%s:%s' % (prefix, code) if prefix else code
    elif not prefix or not code.startswith(prefix + ':'):
        raise ElementPathValueError('%r is not an XPath error code' % code)
    else:
        pcode = code
        code = code[len(prefix) + 1:]

    # XPath 2.0 parser error (https://www.w3.org/TR/xpath20/#id-errors)
    if code == 'XPST0001':
        return ElementPathValueError(message or 'Parser not bound to a schema', pcode, token)
    elif code == 'XPST0003':
        return ElementPathValueError(message or 'Invalid XPath expression', pcode, token)
    elif code == 'XPDY0002':
        return MissingContextError(message or 'Dynamic context required for evaluate', pcode, token)
    elif code == 'XPTY0004':
        return ElementPathTypeError(message or 'Type is not appropriate for the context', pcode, token)
    elif code == 'XPST0005':
        return ElementPathValueError(message or 'A not empty sequence required', pcode, token)
    elif code == 'XPST0008':
        return ElementPathNameError(message or 'Name not found', pcode, token)
    elif code == 'XPST0010':
        return ElementPathNameError(message or 'Axis not found', pcode, token)
    elif code == 'XPST0017':
        return ElementPathTypeError(message or 'Wrong number of arguments', pcode, token)
    elif code == 'XPTY0018':
        return ElementPathTypeError(message or 'Step result contains both nodes and atomic values', pcode, token)
    elif code == 'XPTY0019':
        return ElementPathTypeError(message or 'Intermediate step contains an atomic value', pcode, token)
    elif code == 'XPTY0020':
        return ElementPathTypeError(message or 'Context item is not a node', pcode, token)
    elif code == 'XPDY0050':
        return ElementPathTypeError(message or 'Type does not match sequence type', pcode, token)
    elif code == 'XPST0051':
        return ElementPathNameError(message or 'Unknown atomic type', pcode, token)
    elif code == 'XPST0080':
        return ElementPathNameError(message or 'Target type cannot be xs:NOTATION or xs:anyAtomicType', pcode, token)
    elif code == 'XPST0081':
        return ElementPathNameError(message or 'Unknown namespace', pcode, token)

    # XPath data types and function errors
    elif code == 'FOER0000':
        return ElementPathError(message or 'Unidentified error', pcode, token)
    elif code == 'FOAR0001':
        return ElementPathValueError(message or 'Division by zero', pcode, token)
    elif code == 'FOAR0002':
        return ElementPathValueError(message or 'Numeric operation overflow/underflow', pcode, token)
    elif code == 'FOCA0001':
        return ElementPathValueError(message or 'Input value too large for decimal', pcode, token)
    elif code == 'FOCA0002':
        return ElementPathValueError(message or 'Invalid lexical value', pcode, token)
    elif code == 'FOCA0003':
        return ElementPathValueError(message or 'Input value too large for integer', pcode, token)
    elif code == 'FOCA0005':
        return ElementPathValueError(message or 'NaN supplied as float/double value', pcode, token)
    elif code == 'FOCA0006':
        return ElementPathValueError(
            message or 'String to be cast to decimal has too many digits of precision', pcode, token
        )
    elif code == 'FOCH0001':
        return ElementPathValueError(message or 'Code point not valid', pcode, token)
    elif code == 'FOCH0002':
        return ElementPathLocaleError(message or 'Unsupported collation', pcode, token)
    elif code == 'FOCH0003':
        return ElementPathValueError(message or 'Unsupported normalization form', pcode, token)
    elif code == 'FOCH0004':
        return ElementPathValueError(message or 'Collation does not support collation units', pcode, token)
    elif code == 'FODC0001':
        return ElementPathValueError(message or 'No context document', pcode, token)
    elif code == 'FODC0002':
        return ElementPathValueError(message or 'Error retrieving resource', pcode, token)
    elif code == 'FODC0003':
        return ElementPathValueError(message or 'Function stability not defined', pcode, token)
    elif code == 'FODC0004':
        return ElementPathValueError(message or 'Invalid argument to fn:collection', pcode, token)
    elif code == 'FODC0005':
        return ElementPathValueError(message or 'Invalid argument to fn:doc or fn:doc-available', pcode, token)
    elif code == 'FODT0001':
        return ElementPathValueError(message or 'Overflow/underflow in date/time operation', pcode, token)
    elif code == 'FODT0002':
        return ElementPathValueError(message or 'Overflow/underflow in duration operation', pcode, token)
    elif code == 'FODT0003':
        return ElementPathValueError(message or 'Invalid timezone value', pcode, token)
    elif code == 'FONS0004':
        return ElementPathKeyError(message or 'No namespace found for prefix', pcode, token)
    elif code == 'FONS0005':
        return ElementPathValueError(message or 'Base-uri not defined in the static context', pcode, token)
    elif code == 'FORG0001':
        return ElementPathValueError(message or 'Invalid value for cast/constructor', pcode, token)
    elif code == 'FORG0002':
        return ElementPathValueError(message or 'Invalid argument to fn:resolve-uri()', pcode, token)
    elif code == 'FORG0003':
        return ElementPathValueError(
            message or 'fn:zero-or-one called with a sequence containing more than one item', pcode, token
        )
    elif code == 'FORG0004':
        return ElementPathValueError(
            message or 'fn:one-or-more called with a sequence containing no items', pcode, token
        )
    elif code == 'FORG0005':
        return ElementPathValueError(
            message or 'fn:exactly-one called with a sequence containing zero or more than one item', pcode, token
        )
    elif code == 'FORG0006':
        return ElementPathTypeError(message or 'Invalid argument type', pcode, token)
    elif code == 'FORG0008':
        return ElementPathValueError(
            message or 'The two arguments to fn:dateTime have inconsistent timezones', pcode, token
        )
    elif code == 'FORG0009':
        return ElementPathValueError(
            message or 'Error in resolving a relative URI against a base URI in fn:resolve-uri', pcode, token
        )
    elif code == 'FORX0001':
        return ElementPathValueError(message or 'Invalid regular expression flags', pcode, token)
    elif code == 'FORX0002':
        return ElementPathValueError(message or 'Invalid regular expression', pcode, token)
    elif code == 'FORX0003':
        return ElementPathValueError(message or 'Regular expression matches zero-length string', pcode, token)
    elif code == 'FORX0004':
        return ElementPathValueError(message or 'Invalid replacement string', pcode, token)
    elif code == 'FOTY0012':
        return ElementPathValueError(message or 'Argument node does not have a typed value', pcode, token)
    else:
        raise ElementPathValueError(message or 'Unknown XPath error code %r.' % code, token=token)
