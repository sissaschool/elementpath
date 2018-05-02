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
This module contains classes and helper functions for defining Pratt parsers.
"""
import re
from decimal import Decimal
from abc import ABCMeta
from collections import MutableSequence
from .exceptions import (
    ElementPathSyntaxError, ElementPathNameError, ElementPathValueError, ElementPathTypeError, ElementPathKeyError
)


SPECIAL_SYMBOL_REGEX = re.compile(r'\s*\(\w+\)\s*')
"""Compiled regular expression for matching special symbols, that are names between round brackets."""


#
# Simple top down parser based on Vaughan Pratt's algorithm (Top Down Operator Precedence).
#
# References:
#
#   https://tdop.github.io/  (Vaughan R. Pratt's "Top Down Operator Precedence" - 1973)
#   http://crockford.com/javascript/tdop/tdop.html  (Douglas Crockford - 2007)
#   http://effbot.org/zone/simple-top-down-parsing.htm (Fredrik Lundh - 2008)
#
# This implementation is based on a base class for defining symbol's related Token
# classes and a base class for parsers. A real parser is built from a derivation of
# the base parser class and the registration of token classes for symbols in parser's
# class symbol table.
#
# A parser can be extended by derivation, copying the reusable token classes and
# defining the additional ones. See the files xpath1_parser.py and xpath2_parser.py
# for a fully implementation example of a real parser.
#

class Token(MutableSequence):
    """
    Token base class for defining a parser based on Pratt's method.

    :cvar symbol: The symbol of the token class.
    :param value: The token value. If not provided defaults to token symbol.
    :cvar lbp: Pratt's left binding power, defaults to 0.
    :cvar rbp: Pratt's right binding power, defaults to 0.
    :cvar label: A label that can be changed to put a custom category to a token \
    class (eg: function), depending on your parsing needs. Its default is 'symbol'.
    """
    symbol = None     # the token identifier, key in the token table.
    pattern = None    # the token regex pattern, for building the tokenizer.
    lbp = 0           # left binding power
    rbp = 0           # right binding power
    label = 'symbol'  # optional label

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
        if SPECIAL_SYMBOL_REGEX.search(symbol) is not None:
            return '%r %s' % (self.value, symbol[1:-1])
        else:
            return '%r %s' % (symbol, self.label)

    def __repr__(self):
        symbol, value = self.symbol, self.value
        if value != symbol:
            return u'%s(symbol=%r, value=%r)' % (self.__class__.__name__, symbol, value)
        else:
            return u'%s(symbol=%r)' % (self.__class__.__name__, symbol)

    def __cmp__(self, other):
        return self.symbol == other.symbol and self.value == other.value

    @property
    def arity(self):
        return len(self)

    @property
    def tree(self):
        symbol, length = self.symbol, len(self)
        if symbol == '(name)':
            return u'(%s)' % self.value
        elif SPECIAL_SYMBOL_REGEX.search(symbol) is not None:
            return u'(%r)' % self.value
        elif symbol == '(':
            return '()' if not self else self[0].tree
        elif not length:
            return u'(%s)' % symbol
        else:
            return u'(%s %s)' % (symbol, ' '.join(item.tree for item in self))

    @property
    def source(self):
        symbol = self.symbol
        if symbol == '(name)':
            return self.value
        elif SPECIAL_SYMBOL_REGEX.search(symbol) is not None:
            return repr(self.value)
        else:
            length = len(self)
            if not length:
                return symbol
            elif length == 1:
                return u'%s %s' % (symbol, self[0].source)
            elif length == 2:
                return u'%s %s %s' % (self[0].source, symbol, self[1].source)
            else:
                return u'%s %s' % (symbol, ' '.join(item.source for item in self))

    def nud(self):
        """Null denotation method"""
        self.wrong_syntax()

    def led(self, left):
        """Left denotation method"""
        self.wrong_syntax()

    def evaluate(self, *args, **kwargs):
        """Evaluation method"""

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
            self.wrong_syntax()

    def unexpected(self, *symbols):
        if not symbols or self.symbol in symbols:
            self.wrong_syntax()

    def wrong_syntax(self):
        if SPECIAL_SYMBOL_REGEX.search(self.symbol) is not None:
            self.parser.wrong_syntax(self.value)
        else:
            self.parser.wrong_syntax(self.symbol)

    def wrong_name(self, message=None):
        raise ElementPathNameError("%s: %s." % (self, message or 'unknown error'))

    def wrong_value(self, message=None):
        raise ElementPathValueError("%s: %s." % (self, message or 'unknown error'))

    def wrong_type(self, message=None):
        raise ElementPathTypeError("%s: %s." % (self, message or 'unknown error'))


class Parser(object):
    symbol_table = {}
    token_base_class = Token
    tokenizer = None
    SYMBOLS = ()

    @classmethod
    def build_tokenizer(cls, name_pattern='[A-Za-z0-9_]+'):
        """
        Builds the parser tokenizer using the symbol related patterns. A tokenizer built with this
        method is suited for programming languages where extra spaces between symbols are skipped.

        :param name_pattern: Pattern to use to match names.
        """
        tokenizer_pattern_template = r"""
            ('[^']*' | "[^"]*" | (?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?) |  # Literals (string and numbers)
            (%s|[%s]) |                                                       # Symbol's patterns
            (%s) |                                                            # Names
            (\S) |                                                            # Unexpected characters
            \s+                                                               # Skip extra spaces
        """

        patterns = [
            s.pattern for s in cls.symbol_table.values()
            if SPECIAL_SYMBOL_REGEX.search(s.pattern) is None
        ]
        string_patterns = []
        character_patterns = []
        for p in (s.strip() for s in patterns):
            length = len(p)
            if length == 1 or length == 2 and p[0] == '\\':
                character_patterns.append(p)
            else:
                string_patterns.append(p)

        pattern = tokenizer_pattern_template % (
            '|'.join(sorted(string_patterns, key=lambda x: -len(x))),
            ''.join(character_patterns),
            name_pattern
        )
        cls.tokenizer = re.compile(pattern, re.VERBOSE)

    def __init__(self):
        if '(end)' not in self.symbol_table or self.tokenizer is None:
            raise ValueError("Incomplete parser class %s registration." % self.__class__.__name__)
        self.token = None
        self.match = None
        self.next_token = None
        self.next_match = None
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
            self.token = None
            self.match = None
            self.next_token = None
            self.next_match = None

    def advance(self, *symbols):
        """
        The function for advance to next token.

        :param symbols: Optional arguments tuple. If not empty one of the provided \
        symbols is expected. If the next token's symbol differs the parser raise a \
        parse error.
        :return: The next token.
        """
        if getattr(self.next_token, 'symbol', None) == '(end)':
            if self.token is None:
                raise ElementPathSyntaxError("source is empty.")
            else:
                raise ElementPathSyntaxError("unexpected end of source after %s." % self.token)
        elif self.next_token is not None:
            self.next_token.expected(*symbols)

        self.token = self.next_token
        self.match = self.next_match
        while True:
            try:
                self.next_match = next(self.tokens)
            except StopIteration:
                self.next_token = self.symbol_table['(end)'](self)
                break
            else:
                literal, symbol, name, unexpected = self.next_match.groups()
                if symbol is not None:
                    symbol = symbol.strip()
                    try:
                        self.next_token = self.symbol_table[symbol](self)
                    except KeyError:
                        raise ElementPathSyntaxError("unknown symbol %r." % symbol)
                    break
                elif literal is not None:
                    if literal[0] in '\'"':
                        self.next_token = self.symbol_table['(string)'](self, literal.strip("'\""))
                    elif 'e' in literal or 'E' in literal:
                        self.next_token = self.symbol_table['(float)'](self, float(literal))
                    elif '.' in literal:
                        self.next_token = self.symbol_table['(decimal)'](self, Decimal(literal))
                    else:
                        self.next_token = self.symbol_table['(integer)'](self, int(literal))
                    break
                elif name is not None:
                    self.next_token = self.symbol_table['(name)'](self, name)
                    break
                elif unexpected is not None:
                    self.wrong_syntax(unexpected)
                elif str(self.next_match.group()).strip():
                    raise RuntimeError(
                        "Unexpected matching %r: not compatible tokenizer." % self.next_match.group()
                    )
        return self.next_token

    def raw_advance(self, *stop_symbols):
        """
        Advances until one of the symbols is found or the end of source is reached, returning
        the raw source string placed before. Useful for raw parsing of comments and references
        enclosed between specific symbols.

        :param stop_symbols: The symbols that have to be found for stopping advance.
        :return: The source string chunk enclosed between the initial position and the first stop symbol.
        """
        if not stop_symbols:
            raise ElementPathValueError("at least a stop symbol required!")
        elif getattr(self.next_token, 'symbol', None) == '(end)':
            if self.token is None:
                raise ElementPathSyntaxError("source is empty.")
            else:
                raise ElementPathSyntaxError("unexpected end of source after %s." % self.token)

        self.token = self.next_token
        self.match = self.next_match
        source_chunk = []
        while True:
            try:
                self.next_match = next(self.tokens)
            except StopIteration:
                self.next_token = self.symbol_table['(end)'](self)
                break
            else:
                symbol = self.next_match.group(2)
                if symbol is not None:
                    symbol = symbol.strip()
                    if symbol not in stop_symbols:
                        source_chunk.append(symbol)
                    else:
                        try:
                            self.next_token = self.symbol_table[symbol](self)
                        except KeyError:
                            raise ElementPathSyntaxError("unknown symbol %r." % symbol)
                        break
                else:
                    source_chunk.append(self.next_match.group())
        return ''.join(source_chunk)

    def expression(self, rbp=0):
        """
        Parse function for expressions. It calls token.nud() and then advance
        until the right binding power is less the left binding power of the next
        token, invoking the led() method on the following token.

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
            return 1, 0
        token_index = self.match.span()[0]
        line = self.source[:token_index].count('\n') + 1
        if line == 1:
            return line, token_index + 1
        else:
            return line, token_index - self.source[:token_index].rindex('\n')

    @property
    def source_first(self):
        if self.match is None:
            return True
        return not bool(self.source[0:self.match.span()[0]].strip())

    @property
    def line_first(self):
        if self.match is None:
            return True
        token_index = self.match.span()[0]
        line_start = self.source[0:token_index].rindex('\n') + 1
        return not bool(self.source[line_start:token_index].strip())

    def wrong_syntax(self, symbol):
        pos = self.position
        token = self.token
        if token is not None and symbol != token.symbol:
            raise ElementPathSyntaxError(
                "unexpected symbol %r after %s at line %d, column %d." % (symbol, token, pos[0], pos[1])
            )
        else:
            raise ElementPathSyntaxError(
                "unexpected symbol %r at line %d, column %d." % (symbol, pos[0], pos[1])
            )

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
        cls.build_tokenizer()

    @classmethod
    def register(cls, symbol, **kwargs):
        """
        Register/update a token class in the symbol table.

        :param symbol: The identifier symbol for the or an existent token class.
        :param kwargs: Optional attributes/methods for the token class.
        :return: A token class.
        """
        def symbol_escape(s):
            s = re.escape(s)
            s.replace(r'\ ', '\s+')

            if s.isalpha():
                s = r'\b%s\b' % s
            elif s[-2:] == r'\(':
                s = '%s\s*%s' % (s[:-2], s[-2:])
            elif s[-4:] == r'\:\:':
                s = '%s\s*%s' % (s[:-4], s[-4:])
            return s

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
            kwargs['symbol'] = symbol
            if 'pattern' not in kwargs:
                pattern = symbol_escape(symbol) if len(symbol) > 1 else re.escape(symbol)
                kwargs['pattern'] = pattern
            token_class = ABCMeta('token', (cls.token_base_class,), kwargs)
            cls.symbol_table[symbol] = token_class
            cls.tokenizer = None

            # noinspection PyCallByClass
            ABCMeta.register(MutableSequence, token_class)
        else:
            for key, value in kwargs.items():
                if key == 'lbp' and value > token_class.lbp:
                    token_class.lbp = value
                elif key == 'rbp' and value > token_class.rbp:
                    token_class.rbp = value
                elif callable(value):
                    setattr(token_class, key, value)

        return token_class

    @classmethod
    def unregister(cls, symbol):
        del cls.symbol_table[symbol.strip()]

    @classmethod
    def alias(cls, symbol, other):
        symbol = symbol.strip()
        try:
            other_class = cls.symbol_table[other]
        except KeyError:
            raise ElementPathKeyError("%r is not a registered symbol for %r." % (other, cls))

        token_class = cls.register(symbol)
        token_class.lbp = other_class.lbp
        token_class.rbp = other_class.rbp
        token_class.nud = other_class.nud
        token_class.led = other_class.led
        token_class.evaluate = other_class.evaluate
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

        def evaluate(self, *args, **kwargs):
            return self.value

        return cls.register(symbol, label='literal', lbp=bp, evaluate=evaluate, nud=nud)

    @classmethod
    def nullary(cls, symbol, bp=0):
        def nud(self):
            return self
        return cls.register(symbol, label='operator', lbp=bp, nud=nud)

    @classmethod
    def prefix(cls, symbol, bp=0):
        def nud(self):
            self[:] = self.parser.expression(rbp=bp),
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, nud=nud)

    @classmethod
    def infix(cls, symbol, bp=0):
        def led(self, left):
            self[:] = left, self.parser.expression(rbp=bp)
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, led=led)

    @classmethod
    def infixr(cls, symbol, bp=0):
        def led(self, left):
            self[:] = left, self.parser.expression(rbp=bp-1)
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp-1, led=led)

    @classmethod
    def postfix(cls, symbol, bp=0):
        def led(self, left):
            self[:] = left,
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, led=led)

    @classmethod
    def method(cls, symbol, bp=0):
        token_class = cls.register(symbol, label='operator', lbp=bp, rbp=bp)

        def bind(func):
            assert callable(getattr(token_class, func.__name__, None)), \
                "The name %r does not match with a callable of %r." % (func.__name__, token_class)
            setattr(token_class, func.__name__, func)
            return func
        return bind
