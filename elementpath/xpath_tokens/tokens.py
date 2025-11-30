#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""A collection of additional and special token classes."""
from collections.abc import Iterator
from typing import Literal, cast

import elementpath.aliases as ta

from elementpath.namespaces import XSD_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, XMLNS_NAMESPACE
from elementpath.sequences import XSequence, sequence_classes
from elementpath.datatypes import AnyAtomicType, AnyURI
from elementpath.helpers import collapse_white_spaces
from elementpath.xpath_nodes import AttributeNode, ElementNode

from .base import XPathToken


class ValueToken(XPathToken):
    """
    A dummy token for encapsulating a value.
    """
    symbol = '(value)'
    value: AnyAtomicType

    @property
    def source(self) -> str:
        return str(self.value)

    def evaluate(self, context: ta.ContextType = None) -> AnyAtomicType:
        return self.value

    def select(self, context: ta.ContextType = None) -> Iterator[AnyAtomicType]:
        if isinstance(self.value, sequence_classes):
            yield from self.value
        else:
            yield self.value


###
# Token classes for names
class ProxyToken(XPathToken):
    """
    A token class for resolving collisions between other tokens that have
    the same symbol but are in different namespaces. It also resolves
    collisions of functions with names.
    """
    symbol = '(proxy)'

    def nud(self) -> 'XPathToken':
        if self.parser.next_token.symbol not in ('(', '#'):
            # Not a function call or reference, returns a name.
            return self.as_name()

        lookup_name = f'{{{self.namespace or XPATH_FUNCTIONS_NAMESPACE}}}{self.value}'
        try:
            token = self.parser.symbol_table[lookup_name](self.parser)
        except KeyError:
            if self.namespace == XSD_NAMESPACE:
                msg = f'unknown constructor function {self.symbol!r}'
            else:
                msg = f'unknown function {self.symbol!r}'
            raise self.error('XPST0017', msg) from None
        else:
            if self.parser.next_token.symbol == '#':
                return token

            res = token.nud()
            return res


###
# Name related tokens for matching elements and attributes
class NameToken(XPathToken):
    """The special '(name)' token for matching named nodes."""
    symbol = lookup_name = '(name)'
    label = 'name'
    bp = 10
    value: str

    def nud(self) -> XPathToken:
        if self.parser.next_token.symbol == '::':
            msg = "axis '%s::' not found" % self.value
            if self.parser.compatibility_mode:
                raise self.error('XPST0010', msg)
            raise self.error('XPST0003', msg)
        elif self.parser.next_token.symbol == '(':
            if self.parser.version >= '2.0':
                pass  # XP30+ has led() for '(' operator that can check this
            elif self.namespace == XSD_NAMESPACE:
                raise self.error('XPST0017', 'unknown constructor function {!r}'.format(self.value))
            elif self.namespace or self.value not in self.parser.RESERVED_FUNCTION_NAMES:
                raise self.error('XPST0017', 'unknown function {!r}'.format(self.value))
            else:
                msg = f"{self.value!r} is not allowed as function name"
                raise self.error('XPST0003', msg)

        return self

    def evaluate(self, context: ta.ContextType = None) \
            -> XSequence[AttributeNode | ElementNode]:
        return XSequence(self.select(context))

    def select(self, context: ta.ContextType = None) -> Iterator[AttributeNode | ElementNode]:
        if context is None:
            raise self.missing_context()

        yield from context.iter_matching_nodes(self.value, self.parser.default_namespace)


class PrefixedReferenceToken(XPathToken):
    """Colon symbol for expressing namespace related names."""
    symbol = lookup_name = ':'
    lbp = 95
    rbp = 95
    value: str

    def __init__(self, parser: ta.XPathParserType, value: Literal[':'] = ':') -> None:
        super().__init__(parser, value)

        # Change bind powers if it cannot be a namespace related token
        if self.is_spaced():
            self.lbp = self.rbp = 0
        elif self.parser.token.symbol not in ('*', '(name)', 'array'):
            self.lbp = self.rbp = 0

    def __str__(self) -> str:
        if len(self) < 2:
            return 'unparsed prefixed reference'
        elif self[1].label.endswith('function'):
            return f"{self.value!r} {self[1].label}"
        elif '*' in self.value:
            return f"{self.value!r} prefixed wildcard"
        else:
            return f"{self.value!r} prefixed name"

    @property
    def source(self) -> str:
        if self.occurrence:
            return ':'.join(tk.source for tk in self) + self.occurrence
        else:
            return ':'.join(tk.source for tk in self)

    def led(self, left: XPathToken) -> XPathToken:
        version = self.parser.version
        if self.is_spaced():
            if version <= '3.0':
                raise self.wrong_syntax("a QName cannot contains spaces before or after ':'")
            return left

        if version == '1.0':
            left.expected('(name)')
        elif version <= '3.0':
            left.expected('(name)', '*')
        elif left.symbol not in ('(name)', '*'):
            return left

        if not self.parser.next_token.label.endswith('function'):
            self.parser.expected_next('(name)', '*')

        if isinstance(left, NameToken):
            try:
                namespace = self.parser.namespaces[left.value]
            except KeyError:
                self.parser.advance()  # Assure there isn't a following incomplete comment
                self[:] = left, self.parser.token
                msg = "prefix {!r} is not declared".format(left.value)
                # raise self.error('FONS0004', msg) from None  FIXME?? XP30+??
                raise self.error('XPST0081', msg) from None
            else:
                self.parser.next_token.bind_namespace(namespace)
        elif self.parser.next_token.symbol != '(name)':
            raise self.wrong_syntax()
        else:
            self.parser.next_token.bind_namespace('*')

        self[:] = left, self.parser.expression(95)

        self.name = self[1].name
        if self[1].label.endswith('function'):
            self.value = f'{self[0].value}:{self[1].symbol}'
        else:
            self.value = f'{self[0].value}:{self[1].value}'
        return self

    def evaluate(self, context: ta.ContextType = None) -> ta.ValueType:
        if self[1].label.endswith('function'):
            return self[1].evaluate(context)
        return XSequence([x for x in self.select(context)])

    def select(self, context: ta.ContextType = None) -> Iterator[ta.ItemType]:
        if self[1].label.endswith('function'):
            value = self[1].evaluate(context)
            if isinstance(value, sequence_classes):
                yield from value
            elif value is not None:
                yield value
            return

        if context is None:
            raise self.missing_context()

        yield from context.iter_matching_nodes(self.name)


class ExpandedNameToken(XPathToken):
    """Braced expanded name symbol for expressing namespace related names."""

    symbol = lookup_name = '{'
    label = 'expanded name'
    bp = lbp = rbp = 95
    value: str

    def nud(self) -> XPathToken:
        if self.parser.strict and self.symbol == '{':
            raise self.wrong_syntax("not allowed symbol if parser has strict=True")

        self.parser.next_token.unexpected('{')
        if self.parser.next_token.symbol == '}':
            namespace = ''
        else:
            value = self.parser.next_token.value
            assert isinstance(value, str)
            namespace = value + self.parser.advance_until('}')
            namespace = collapse_white_spaces(namespace)

        try:
            AnyURI(namespace)
        except ValueError as err:
            msg = f"invalid URI in an EQName: {str(err)}"
            raise self.error('XQST0046', msg) from None

        if namespace == XMLNS_NAMESPACE:
            msg = f"cannot use the URI {XMLNS_NAMESPACE!r}!r in an EQName"
            raise self.error('XQST0070', msg)

        self.parser.advance()
        if not self.parser.next_token.label.endswith('function'):
            self.parser.expected_next('(name)', '*')
        self.parser.next_token.bind_namespace(namespace)

        cls: type[XPathToken] = self.parser.symbol_table['(string)']
        self[:] = cls(self.parser, namespace), self.parser.expression(90)

        if self[0].value:
            self.name = self[1].name = self.value = f'{{{self[0].value}}}{self[1].value}'
        elif self[1].value == '*':
            self.name = self[1].name = self.value = '{}*'
        else:
            self.name = self[1].name = self.value = cast(str, self[1].value)
        return self

    def evaluate(self, context: ta.ContextType = None) -> ta.ValueType:
        if self[1].label.endswith('function'):
            return self[1].evaluate(context)
        return XSequence([x for x in self.select(context)])

    def select(self, context: ta.ContextType = None) -> Iterator[ta.ItemType]:
        if self[1].label.endswith('function'):
            result = self[1].evaluate(context)
            if isinstance(result, sequence_classes):
                yield from result
            else:
                yield result
            return
        elif context is None:
            raise self.missing_context()

        if isinstance(self.value, str):
            yield from context.iter_matching_nodes(self.name)
