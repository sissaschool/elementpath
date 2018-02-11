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
from .exceptions import ElementPathSyntaxError


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
        if self:
            return u'(%s %s)' % (self.value, ' '.join(str(item) for item in self))
        else:
            return u'(%s)' % self.value

    def __repr__(self):
        return u'%s(value=%r)' % (self.__class__.__name__, self.value)

    def __cmp__(self, other):
        return self.symbol == other.symbol and self.value == other.value

    @property
    def arity(self):
        return len(self)

    def nud(self):
        """Null denotation method"""
        raise ElementPathSyntaxError("Undefined operator for %r." % self.symbol)

    def led(self, left):
        """Left denotation method"""
        raise ElementPathSyntaxError("Undefined operator for %r." % self.symbol)

    def eval(self):
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

    def expected(self, symbol):
        if self.symbol != symbol:
            raise ElementPathSyntaxError("Expected %r token, found %r." % (symbol, str(self.value)))

    def unexpected(self, symbol=None):
        if not symbol or self.symbol == symbol:
            raise ElementPathSyntaxError("Unexpected %r token." % str(self.value))


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

    def parse(self, source):
        try:
            self.tokens = iter(self.tokenizer.finditer(source))
            self.advance()
            root_token = self.expression()
            if self.next_token.symbol != '(end)':
                self.next_token.unexpected()
            return root_token
        finally:
            self.tokens = iter(())
            self.next_token = None

    def advance(self, symbol=None):
        if getattr(self.next_token, 'symbol', None) == '(end)':
            raise ElementPathSyntaxError(
                "Unexpected end of source at position %d, after %r." % (self.match.span()[1], self.token.symbol)
            )

        self.token = self.next_token
        if symbol and symbol not in (self.next_token.symbol, self.next_token.value):
            self.next_token.expected(symbol)

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
            name = '_%s_%s' % (symbol, cls.token_base_class.__name__)
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
