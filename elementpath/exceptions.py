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
from __future__ import unicode_literals
from .compat import PY3

XQT_ERRORS_NAMESPACE = "http://www.w3.org/2005/xqt-errors"


class ElementPathError(Exception):
    """
    Base exception class for elementpath package.

    :param message: the message related to the error.
    :param token: an optional token instance related with the error.
    :param code: an optional error code.
    """

    def __init__(self, message, token=None, code=None):
        super(ElementPathError, self).__init__(message)
        self.message = message
        self.token = token
        self.code = code

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


class ElementPathMissingContextError(ElementPathError):
    pass


class ElementPathCastError(ElementPathError):
    pass


def xpath_error(code, message=None, token=None, prefix='err'):
    """
    Returns an XPath error instance related with a code. An XPath/XQuery/XSLT error code is an
    alphanumeric token starting with four uppercase letters and ending with four digits.

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
        return ElementPathValueError(message or 'Parser not bound to a schema', token, pcode)
    elif code == 'XPDY0002':
        return ElementPathMissingContextError(message or 'Dynamic context required for evaluate', token, pcode)
    elif code == 'XPTY0004':
        return ElementPathTypeError(message or 'Type is not appropriate for the context', token, pcode)
    elif code == 'XPST0005':
        return ElementPathValueError(message or 'A not empty sequence required', token, pcode)
    elif code == 'XPST0008':
        return ElementPathNameError(message or 'Name not found', token, pcode)
    elif code == 'XPST0010':
        return ElementPathNameError(message or 'Axis not found', token, pcode)
    elif code == 'XPST0017':
        return ElementPathValueError(message or 'Wrong number of arguments', token, pcode)
    elif code == 'XPTY0018':
        return ElementPathTypeError(message or 'Step result contains both nodes and atomic values', token, pcode)
    elif code == 'XPTY0019':
        return ElementPathTypeError(message or 'Intermediate step contains an atomic value', token, pcode)
    elif code == 'XPTY0020':
        return ElementPathTypeError(message or 'Context item is not a node', token, pcode)
    elif code == 'XPDY0050':
        return ElementPathTypeError(message or 'Type does not match sequence type', token, pcode)
    elif code == 'XPST0051':
        return ElementPathNameError(message or 'Unknown atomic type', token, pcode)
    elif code == 'XPST0080':
        return ElementPathNameError(message or 'Target type cannot be xs:NOTATION or xs:anyAtomicType', token, pcode)
    elif code == 'XPST0081':
        return ElementPathNameError(message or 'Unknown namespace', token, pcode)

    # XPath data types and function errors
    elif code == 'FOER0000':
        return ElementPathError(message or 'Unidentified error', token, pcode)
    elif code == 'FOAR0001':
        return ElementPathValueError(message or 'Division by zero', token, pcode)
    elif code == 'FOAR0002':
        return ElementPathValueError(message or 'Numeric operation overflow/underflow', token, pcode)
    elif code == 'FOCA0001':
        return ElementPathValueError(message or 'Input value too large for decimal', token, pcode)
    elif code == 'FOCA0002':
        return ElementPathValueError(message or 'Invalid lexical value', token, pcode)
    elif code == 'FOCA0003':
        return ElementPathValueError(message or 'Input value too large for integer', token, pcode)
    elif code == 'FOCA0005':
        return ElementPathValueError(message or 'NaN supplied as float/double value', token, pcode)
    elif code == 'FOCA0006':
        return ElementPathValueError(
            message or 'String to be cast to decimal has too many digits of precision', token, pcode
        )
    elif code == 'FOCH0001':
        return ElementPathValueError(message or 'Code point not valid', token, pcode)
    elif code == 'FOCH0002':
        return ElementPathValueError(message or 'Unsupported collation', token, pcode)
    elif code == 'FOCH0003':
        return ElementPathValueError(message or 'Unsupported normalization form', token, pcode)
    elif code == 'FOCH0004':
        return ElementPathValueError(message or 'Collation does not support collation units', token, pcode)
    elif code == 'FODC0001':
        return ElementPathValueError(message or 'No context document', token, pcode)
    elif code == 'FODC0002':
        return ElementPathValueError(message or 'Error retrieving resource', token, pcode)
    elif code == 'FODC0003':
        return ElementPathValueError(message or 'Function stability not defined', token, pcode)
    elif code == 'FODC0004':
        return ElementPathValueError(message or 'Invalid argument to fn:collection', token, pcode)
    elif code == 'FODC0005':
        return ElementPathValueError(message or 'Invalid argument to fn:doc or fn:doc-available', token, pcode)
    elif code == 'FODT0001':
        return ElementPathValueError(message or 'Overflow/underflow in date/time operation', token, pcode)
    elif code == 'FODT0002':
        return ElementPathValueError(message or 'Overflow/underflow in duration operation', token, pcode)
    elif code == 'FODT0003':
        return ElementPathValueError(message or 'Invalid timezone value', token, pcode)
    elif code == 'FONS0004':
        return ElementPathKeyError(message or 'No namespace found for prefix', token, pcode)
    elif code == 'FONS0005':
        return ElementPathValueError(message or 'Base-uri not defined in the static context', token, pcode)
    elif code == 'FORG0001':
        return ElementPathValueError(message or 'Invalid value for cast/constructor', token, pcode)
    elif code == 'FORG0002':
        return ElementPathValueError(message or 'Invalid argument to fn:resolve-uri()', token, pcode)
    elif code == 'FORG0003':
        return ElementPathValueError(
            message or 'fn:zero-or-one called with a sequence containing more than one item', token, pcode
        )
    elif code == 'FORG0004':
        return ElementPathValueError(
            message or 'fn:one-or-more called with a sequence containing no items', token, pcode
        )
    elif code == 'FORG0005':
        return ElementPathValueError(
            message or 'fn:exactly-one called with a sequence containing zero or more than one item', token, pcode
        )
    elif code == 'FORG0006':
        return ElementPathTypeError(message or 'Invalid argument type', token, pcode)
    elif code == 'FORG0008':
        return ElementPathValueError(
            message or 'The two arguments to fn:dateTime have inconsistent timezones', token, pcode
        )
    elif code == 'FORG0009':
        return ElementPathValueError(
            message or 'Error in resolving a relative URI against a base URI in fn:resolve-uri', token, pcode
        )
    elif code == 'FORX0001':
        return ElementPathValueError(message or 'Invalid regular expression flags', token, pcode)
    elif code == 'FORX0002':
        return ElementPathValueError(message or 'Invalid regular expression', token, pcode)
    elif code == 'FORX0003':
        return ElementPathValueError(message or 'Regular expression matches zero-length string', token, pcode)
    elif code == 'FORX0004':
        return ElementPathValueError(message or 'Invalid replacement string', token, pcode)
    elif code == 'FOTY0012':
        return ElementPathValueError(message or 'Argument node does not have a typed value', token, pcode)
    elif code == '':
        return ElementPathValueError(message or '', token, pcode)

    else:
        raise ElementPathValueError('Unknown XPath error code %r.' % code)
