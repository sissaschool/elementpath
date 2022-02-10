#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import locale
from typing import Optional, Any
from .tdop import Token


class ElementPathError(Exception):
    """
    Base exception class for elementpath package.

    :param message: the message related to the error.
    :param code: an optional error code.
    :param token: an optional token instance related with the error.
    """
    def __init__(self, message: str,
                 code: Optional[str] = None,
                 token: Optional[Token[Any]] = None) -> None:
        super(ElementPathError, self).__init__(message)
        self.message = message
        self.code = code
        self.token = token

    def __str__(self) -> str:
        if self.token is None or not isinstance(self.token.value, (str, bytes)):
            if not self.code:
                return self.message
            return '[{}] {}'.format(self.code, self.message)
        elif not self.code:
            return '{1} at line {2}, column {3}: {0}'.format(
                self.message, self.token, *self.token.position
            )
        return '{2} at line {3}, column {4}: [{1}] {0}'.format(
            self.message, self.code, self.token, *self.token.position
        )


class MissingContextError(ElementPathError):
    """Raised when the dynamic context is required for evaluate the XPath expression."""


class ElementPathKeyError(ElementPathError, KeyError):
    pass


class ElementPathZeroDivisionError(ElementPathError, ZeroDivisionError):
    pass


class ElementPathNameError(ElementPathError, NameError):
    pass


class ElementPathOverflowError(ElementPathError, OverflowError):
    pass


class ElementPathRuntimeError(ElementPathError, RuntimeError):
    pass


class ElementPathSyntaxError(ElementPathError, SyntaxError):
    pass


class ElementPathTypeError(ElementPathError, TypeError):
    pass


class ElementPathValueError(ElementPathError, ValueError):
    pass


class ElementPathLocaleError(ElementPathError, locale.Error):
    pass


XPATH_ERROR_CODES = {
    # XPath 2.0 parser errors (https://www.w3.org/TR/xpath20/#id-errors)
    'XPST0001': (ElementPathValueError, 'Parser not bound to a schema'),
    'XPST0003': (ElementPathSyntaxError, 'Invalid XPath expression'),
    'XPDY0002': (MissingContextError, 'Dynamic context required for evaluate'),
    'XPTY0004': (ElementPathTypeError, 'Type is not appropriate for the context'),
    'XPST0005': (ElementPathValueError, 'A not empty sequence required'),
    'XPST0008': (ElementPathNameError, 'Name not found'),
    'XPST0010': (ElementPathNameError, 'Axis not found'),
    'XPST0017': (ElementPathTypeError, 'Wrong number of arguments'),
    'XPTY0018': (ElementPathTypeError,
                 'Step result contains both nodes and atomic values'),
    'XPTY0019': (ElementPathTypeError, 'Intermediate step contains an atomic value'),
    'XPTY0020': (ElementPathTypeError, 'Context item is not a node'),
    'XPDY0050': (ElementPathTypeError, 'Type does not match sequence type'),
    'XPST0051': (ElementPathNameError, 'Unknown atomic type'),
    'XPST0080': (ElementPathNameError,
                 'Target type cannot be xs:NOTATION or xs:anyAtomicType'),
    'XPST0081': (ElementPathNameError, 'Unknown namespace'),

    # Data types and functions errors
    'FOER0000': (ElementPathError, 'Unidentified error'),
    'FOAR0001': (ElementPathZeroDivisionError, 'Division by zero'),
    'FOAR0002': (ElementPathOverflowError, 'Numeric operation overflow/underflow'),
    'FOCA0001': (ElementPathValueError, 'Input value too large for decimal'),
    'FOCA0002': (ElementPathValueError, 'Invalid lexical value'),
    'FOCA0003': (ElementPathValueError, 'Input value too large for integer'),
    'FOCA0005': (ElementPathValueError, 'NaN supplied as float/double value'),
    'FOCA0006': (ElementPathValueError,
                 'String to be cast to decimal has too many digits of precision'),
    'FOCH0001': (ElementPathValueError, 'Code point not valid'),
    'FOCH0002': (ElementPathLocaleError, 'Unsupported collation'),
    'FOCH0003': (ElementPathValueError, 'Unsupported normalization form'),
    'FOCH0004': (ElementPathValueError, 'Collation does not support collation units'),
    'FODC0001': (ElementPathValueError, 'No context document'),
    'FODC0002': (ElementPathValueError, 'Error retrieving resource'),
    'FODC0003': (ElementPathValueError, 'Function stability not defined'),
    'FODC0004': (ElementPathValueError, 'Invalid argument to fn:collection'),
    'FODC0005': (ElementPathValueError, 'Invalid argument to fn:doc or fn:doc-available'),
    'FODT0001': (ElementPathOverflowError, 'Overflow/underflow in date/time operation'),
    'FODT0002': (ElementPathOverflowError, 'Overflow/underflow in duration operation'),
    'FODT0003': (ElementPathValueError, 'Invalid timezone value'),
    'FONS0004': (ElementPathKeyError, 'No namespace found for prefix'),
    'FONS0005': (ElementPathValueError, 'Base-uri not defined in the static context'),
    'FORG0001': (ElementPathValueError, 'Invalid value for cast/constructor'),
    'FORG0002': (ElementPathValueError, 'Invalid argument to fn:resolve-uri()'),
    'FORG0003': (ElementPathValueError,
                 'fn:zero-or-one called with a sequence containing more than one item'),
    'FORG0004': (ElementPathValueError,
                 'fn:one-or-more called with a sequence containing no items'),
    'FORG0005': (ElementPathValueError,
                 'fn:exactly-one called with a sequence containing zero or more than one item'),
    'FORG0006': (ElementPathTypeError, 'Invalid argument type'),
    'FORG0008': (ElementPathValueError,
                 'The two arguments to fn:dateTime have inconsistent timezones'),
    'FORG0009': (ElementPathValueError,
                 'Error in resolving a relative URI against a base URI in fn:resolve-uri'),
    'FORX0001': (ElementPathValueError, 'Invalid regular expression flags'),
    'FORX0002': (ElementPathValueError, 'Invalid regular expression'),
    'FORX0003': (ElementPathValueError, 'Regular expression matches zero-length string'),
    'FORX0004': (ElementPathValueError, 'Invalid replacement string'),
    'FOTY0012': (ElementPathValueError, 'Argument node does not have a typed value'),

    # XPath 3.0+ errors
    'XQST0039': (ElementPathTypeError, 'Duplicate parameter name in inline function expression'),
    'XQST0046': (ElementPathTypeError, 'The namespace part of the EQName is not a valid URI'),
    'XQST0052': (ElementPathNameError, 'The name of an in-scope simple schema type required'),
    'XQST0070': (ElementPathNameError, 'Illegal use of a predefined namespace'),
    'FOTY0013': (ElementPathTypeError, 'The argument to fn:data() contains a function item'),
    'FOTY0014': (ElementPathTypeError, 'The argument to fn:string() is a function item'),
    'FOTY0015': (ElementPathTypeError,
                 'An argument to fn:deep-equal() contains a function item'),
    'FODC0006': (ElementPathValueError,
                 'String passed to fn:parse-xml is not a well-formed XML document'),
    'FODC0010': (ElementPathRuntimeError,
                 'The processor does not support serialization'),
    'FOUT1170': (ElementPathValueError, 'Invalid $href argument to fn:unparsed-text()'),
    'FOUT1190': (ElementPathValueError,
                 'Cannot decode resource retrieved by fn:unparsed-text()'),
    'FOUT1200': (ElementPathValueError,
                 'Cannot infer encoding of resource retrieved by fn:unparsed-text()'),
    'FODF1280': (ElementPathValueError, 'Invalid decimal format name'),
    'FODF1310': (ElementPathValueError, 'Invalid decimal format picture string'),
    'FOFD1340': (ElementPathValueError, 'Invalid date/time formatting parameters'),
    'FOFD1350': (ElementPathValueError, 'Invalid date/time formatting component'),

    'XPTY0117': (ElementPathTypeError,
                 'Item type is xs:untypedAtomic and the expected type is namespace-sensitive'),
    'XPDY0130': (ElementPathValueError,
                 'An implementation-defined limit has been exceeded'),
    'XPST0133': (ElementPathValueError,
                 'The namespace URI for EQName is http://www.w3.org/2000/xmlns/'),

    # XSLT and XQuery Serialization errors
    # (the complete list: https://www.w3.org/TR/xslt-xquery-serialization/#id-errors)
    'SENR0001': (ElementPathTypeError, 'item is an attribute node or a namespace node'),
    'SEPM0016': (ElementPathValueError, 'parameter value is invalid for the defined domain'),
    'SEPM0017': (ElementPathValueError, 'error during extraction of serialization parameters'),
    'SEPM0018': (ElementPathValueError, 'use-character-maps serialization parameter in '
                                        'a sequence of length greater than one'),
    'SEPM0019': (ElementPathValueError, 'same serialization parameter appears more than once'),
}


def xpath_error(code: str, message: Optional[str] = None,
                token: Optional[Token[Any]] = None, prefix: str = 'err') -> ElementPathError:
    """
    Returns an XPath error instance related with a code. An XPath/XQuery/XSLT error code
    (ref: http://www.w3.org/2005/xqt-errors) is an alphanumeric token starting with four
    uppercase letters and ending with four digits.

    :param code: the error code.
    :param message: an optional custom additional message.
    :param token: an optional token instance.
    :param prefix: the namespace prefix to apply to the error code, defaults to 'err'.
    """
    if code.startswith('{'):
        try:
            namespace, code = code[1:].split('}')
        except ValueError:
            message = '{!r} is not an xs:QName'.format(code)
            raise ElementPathValueError(message, 'err:XPTY0004', token)
        else:
            if namespace != 'http://www.w3.org/2005/xqt-errors':
                message = 'invalid namespace {!r}'.format(namespace)
                raise ElementPathValueError(message, 'err:XPTY0004', token)
            pcode = '%s:%s' % (prefix, code) if prefix else code
    elif ':' not in code:
        pcode = '%s:%s' % (prefix, code) if prefix else code
    elif not prefix or not code.startswith(prefix + ':'):
        message = '%r is not an XPath error code' % code
        raise ElementPathValueError(message, 'err:XPTY0004', token)
    else:
        pcode = code
        code = code[len(prefix) + 1:]

    try:
        error_class, default_message = XPATH_ERROR_CODES[code]
    except KeyError:
        raise ElementPathValueError(
            message or 'unknown XPath error code %r' % code, 'err:XPTY0004', token
        )
    else:
        return error_class(message or default_message, pcode, token)
