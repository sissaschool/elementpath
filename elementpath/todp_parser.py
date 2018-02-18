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
This module contains an classes and helper functions for defining Pratt parsers.
"""
import re
from decimal import Decimal
from abc import ABCMeta
from collections import MutableSequence
from .exceptions import ElementPathSyntaxError, ElementPathValueError, ElementPathTypeError


def create_tokenizer(symbols):
    """
    Create a simple tokenizer for a sequence of symbols. Extra spaces are skipped.

    :param symbols: A sequence of strings representing the symbols. Blank and empty \
    symbols are discarded.
    :return: A regex compiled pattern.
    """
    tokenizer_pattern_template = r"""
        ('[^']*' | "[^"]*" | \d+(?:\.\d?)? | \.\d+) |   # Literals (strings or numbers)
        (%s|[%s]) |                                     # Symbols
        ((?:{[^}]+\})?[^/\[\]()@=|\s]+) |               # References and other names   
        \s+                                             # Skip extra spaces
    """

    def symbol_escape(s):
        s = re.escape(s)
        if s[-2:] == r'\(':
            s = '%s\s*%s' % (s[:-2], s[-2:])
        elif s[-4:] == r'\:\:':
            s = '%s\s*%s' % (s[:-4], s[-4:])
        else:
            s.replace(r'\ ', '\s+')
        return s

    symbols = sorted([s2 for s2 in (s1.strip() for s1 in symbols) if s2], key=lambda x: -len(x))
    fence = len([i for i in symbols if len(i) > 1])
    return re.compile(
        tokenizer_pattern_template % (
            '|'.join(map(symbol_escape, symbols[:fence])),
            ''.join(map(re.escape, symbols[fence:]))
        ),
        re.VERBOSE
    )


#
# Simple top down parser based on Vaughan Pratt's algorithm (Top Down Operator Precedence).
#
# References:
#
#   https://tdop.github.io/  (Vaughan R. Pratt's "Top Down Operator Precedence" - 1973)
#   http://crockford.com/javascript/tdop/tdop.html  (Douglas Crockford - 2007)
#   http://effbot.org/zone/simple-top-down-parsing.htm (Fredrik Lundh - 2008)
#
class Token(MutableSequence):
    """
    Token base class for defining a parser based on Pratt's method.

    :cvar symbol: The symbol of the token class.
    :param value: The token value. If not provided defaults to token symbol.
    """
    symbol = None  # the token identifier, key in the token table.
    lbp = 0        # left binding power
    rbp = 0        # right binding power

    def __init__(self, parser, value=None):
        self.parser = parser
        self.value = value if value is not None else self.symbol
        self._operands = []

    def __getitem__(self, i):
        return self._operands[i]

    def __setitem__(self, i, item):
        self._operands[i] = item

    def __delitem__(self, i):
        del self._operands[i]

    def __len__(self):
        return len(self._operands)

    def insert(self, i, item):
        self._operands.insert(i, item)

    def __str__(self):
        symbol = self.symbol
        if len(symbol) <= 3:
            return '%r operator' % symbol
        elif symbol.endswith('('):
            return '%s(%s)' % (symbol[:-1], ', '.join(repr(t.value) for t in self))
        elif self.symbol.startswith('(') and self.symbol.endswith(')'):
            return '%r %s' % (self.value, self.symbol[1:-1])
        else:
            return '%r operator' % symbol

    def __repr__(self):
        if self.value != self.symbol:
            return u'%s(value=%r)' % (self.__class__.__name__, self.value)
        else:
            return u'%s()' % self.__class__.__name__

    def __cmp__(self, other):
        return self.symbol == other.symbol and self.value == other.value

    @property
    def arity(self):
        return len(self)

    @property
    def tree(self):
        if self:
            return u'(%s %s)' % (self.value, ' '.join(item.tree for item in self))
        else:
            return u'(%s)' % self.value

    def nud(self):
        """Null denotation method"""
        self.wrong_symbol()

    def led(self, left):
        """Left denotation method"""
        self.wrong_symbol()

    def eval(self, *args, **kwargs):
        """Evaluation method"""
        return self.value

    def iter(self):
        for t in self[:1]:
            for token in t.iter():
                yield token
        yield self
        for t in self[1:]:
            for token in t.iter():
                yield token

    def expected(self, *symbols):
        if symbols and self.symbol not in symbols:
            self.wrong_symbol()

    def unexpected(self, *symbols):
        if not symbols or self.symbol in symbols:
            self.wrong_symbol()

    def wrong_symbol(self):
        if self.symbol in {'(end)', '(ref)', '(string)', '(decimal)', '(integer)'}:
            value = self.value
        else:
            value = self.symbol
        pos = self.parser.position
        token = self.parser.token
        if self is not token and token is not None:
            raise ElementPathSyntaxError(
                "unexpected token %r after %s at line %d, column %d." % (value, token, pos[0], pos[1])
            )
        else:
            raise ElementPathSyntaxError(
                "unexpected token %r at line %d, column %d." % (value, pos[0], pos[1])
            )

    def wrong_syntax(self, message):
        raise ElementPathSyntaxError("%s: %s." % (self, message or 'unknown error'))

    def wrong_value(self, message):
        raise ElementPathValueError("%s: %s." % (self, message or 'unknown error'))

    def wrong_type(self, message):
        raise ElementPathTypeError("%s: %s." % (self, message or 'unknown error'))


class Parser(object):
    symbol_table = {}
    token_base_class = Token
    tokenizer = None
    SYMBOLS = ()

    def __init__(self):
        if '(end)' not in self.symbol_table or self.tokenizer is None:
            raise ValueError("Incomplete parser class %s registration." % self.__class__.__name__)
        self.token = None
        self.next_token = None
        self.match = None
        self.tokens = iter(())
        self.source = ''

    def parse(self, source):
        try:
            self.source = source
            self.tokens = iter(self.tokenizer.finditer(source))
            self.advance()
            root_token = self.expression()
            if self.next_token.symbol != '(end)':
                self.next_token.unexpected()
            return root_token
        finally:
            self.tokens = iter(())
            self.next_token = None

    def advance(self, *symbols):
        if getattr(self.next_token, 'symbol', None) == '(end)':
            pos = self.position
            raise ElementPathSyntaxError(
                "Unexpected end of source after %s: line %d, column %d." % (self.token, pos[0], pos[1]-1)
            )
        elif self.next_token is not None:
            self.next_token.expected(*symbols)

        self.token = self.next_token
        while True:
            try:
                self.match = next(self.tokens)
            except StopIteration:
                self.next_token = self.symbol_table['(end)'](self)
                break
            else:
                literal, operator, ref = self.match.groups()
                if operator is not None:
                    try:
                        self.next_token = self.symbol_table[operator.replace(' ', '')](self)
                    except KeyError:
                        raise ElementPathSyntaxError("unknown operator %r." % operator)
                    break
                elif literal is not None:
                    if literal[0] in '\'"':
                        self.next_token = self.symbol_table['(string)'](self, literal.strip("'\""))
                    elif '.' in literal:
                        self.next_token = self.symbol_table['(decimal)'](self, Decimal(literal))
                    else:
                        self.next_token = self.symbol_table['(integer)'](self, int(literal))
                    break
                elif ref is not None:
                    self.next_token = self.symbol_table['(ref)'](self, ref)
                    break
                elif str(self.match.group()).strip():
                    raise ElementPathSyntaxError("unexpected token: %r" % self.match)

        return self.next_token

    def expression(self, rbp=0):
        """
        Recursive expression parser for expressions. Calls token.nud() and then
        advance until the right binding power is less the left binding power of
        the next token, invoking the led() method on the following token.

        :param rbp: right binding power for the expression.
        :return: left token.
        """
        token = self.next_token
        self.advance()
        left = token.nud()
        while rbp < self.next_token.lbp:
            token = self.next_token
            self.advance()
            left = token.led(left)
        return left

    @property
    def position(self):
        if self.match is None:
            return (1, 0)
        column = self.match.span()[0]
        line = self.source[:column].count('\n') + 1
        if line == 1:
            return (line, column + 1)
        else:
            return (line, column - self.source[:column].rindex('\n'))

    @classmethod
    def begin(cls):
        """
        Begin the symbol registration. Helper functions are bound to global names.
        """
        cls.tokenizer = None
        globals().update({
            'register': cls.register,
            'literal': cls.literal,
            'prefix': cls.prefix,
            'infix': cls.infix,
            'infixr': cls.infixr,
            'method': cls.method,
        })

    @classmethod
    def end(cls):
        """
        End the symbol registration. Registers the special (end) symbol and sets the tokenizer.
        """
        cls.register('(end)')
        cls.tokenizer = create_tokenizer(
            s for s in cls.symbol_table
            if s.strip() not in {'(end)', '(ref)', '(string)', '(decimal)', '(integer)'}
        )

    @classmethod
    def register(cls, symbol, **kwargs):
        """
        Register/update a token class in the symbol table.

        :param symbol: The identifier symbol for the or an existent token class.
        :param kwargs: Optional attributes/methods for the token class.
        :return: A token class.
        """
        try:
            try:
                symbol = symbol.strip()
            except AttributeError:
                assert issubclass(symbol, cls.token_base_class), \
                    "A %r subclass requested, not %r." % (cls.token_base_class, symbol)
                symbol, token_class = symbol.symbol, symbol
                if symbol not in cls.symbol_table:
                    cls.symbol_table[symbol] = token_class
                else:
                    assert cls.symbol_table[symbol] is token_class, \
                        "The registered instance for %r is not %r." % (symbol, token_class)
            else:
                token_class = cls.symbol_table[symbol]

        except KeyError:
            name = '%s_%s' % (symbol, cls.token_base_class.__name__)
            kwargs['symbol'] = symbol
            token_class = ABCMeta(name, (cls.token_base_class,), kwargs)
            cls.symbol_table[symbol] = token_class
            cls.tokenizer = None
            ABCMeta.register(MutableSequence, token_class)
        else:
            for key, value in kwargs.items():
                if key == 'lbp' and value > token_class.lbp:
                    token_class.lbp = value
                elif callable(value):
                    setattr(token_class, key, value)

        return token_class

    @classmethod
    def unregistered(cls):
        if cls.SYMBOLS:
            return [s for s in cls.SYMBOLS if s not in cls.symbol_table]

    @classmethod
    def symbol(cls, s):
        return cls.register(s)

    @classmethod
    def literal(cls, symbol, bp=0):
        def nud(self):
            return self
        return cls.register(symbol, lbp=bp, nud=nud)

    @classmethod
    def prefix(cls, symbol, bp=0):
        def nud(self):
            self[0:] = self.parser.expression(rbp=bp),
            return self
        return cls.register(symbol, lbp=bp, rbp=bp, nud=nud)

    @classmethod
    def infix(cls, symbol, bp=0):
        def led(self, left):
            self[0:1] = left, self.parser.expression(rbp=bp)
            return self
        return cls.register(symbol, lbp=bp, rbp=bp, led=led)

    @classmethod
    def infixr(cls, symbol, bp=0):
        def led(self, left):
            self[0:1] = left, self.parser.expression(rbp=bp-1)
            return self
        return cls.register(symbol, lbp=bp, rbp=bp-1, led=led)

    @classmethod
    def method(cls, symbol, bp=0):
        token_class = cls.register(symbol, lbp=bp, rbp=bp)

        def bind(func):
            assert callable(getattr(token_class, func.__name__, None)), \
                "The name %r does not match with a callable of %r." % (func.__name__, token_class)
            setattr(token_class, func.__name__, func)
            return func
        return bind
