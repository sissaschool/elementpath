#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import locale
import threading
from contextlib import AbstractContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Any, Optional, Sequence, Type
from urllib.parse import urlsplit

from .exceptions import xpath_error

if TYPE_CHECKING:
    from .xpath_token import XPathToken

UNICODE_COLLATION_BASE_URI = "http://www.w3.org/2013/collation/UCA"

UNICODE_CODEPOINT_COLLATION = \
    "http://www.w3.org/2005/xpath-functions/collation/codepoint"

HTML_ASCII_CASE_INSENSITIVE_COLLATION = \
    "http://www.w3.org/2005/xpath-functions/collation/html-ascii-case-insensitive"


_locale_collate_lock = threading.Lock()


def get_locale_category(category: int) -> str:
    """
    Gets the current value of a locale category. A replacement
    of locale.getdefaultlocale(), deprecated since Python 3.11.
    """
    _locale = locale.setlocale(category, None)
    if _locale == 'C':
        # locale category does not seem to be configured, so get the user
        # preferred locale and then restore the  previous state
        _locale = locale.setlocale(category, '')
        locale.setlocale(category, 'C')

    return _locale


def unicode_codepoint_compare(s1: str, s2: str) -> int:
    for cp1, cp2 in zip(map(ord, s1), map(ord, s2)):
        if cp1 < cp2:
            return -1
        elif cp1 > cp2:
            return 1

    return 0 if len(s1) == len(s2) else -1 if len(s1) < len(s2) else 1


def same_string(s: str) -> str:
    return s


def case_insensitive_compare(s1: str, s2: str) -> int:
    if s1.casefold() == s2.casefold():
        return 0
    elif s1.casefold() < s2.casefold():
        return -1
    else:
        return 1


def casefold(s: str) -> str:
    return s.casefold()


class CollationManager(AbstractContextManager):
    """
    Context Manager for collations. Provide helper operators as methods.
    """
    fallback: bool = False
    _current_lc_collate: Optional[Sequence[str]] = None

    def __init__(self,
                 collation: Optional[str],
                 token: Optional['XPathToken'] = None) -> None:
        self.collation = collation
        self.token = token
        self.strcoll = locale.strcoll
        self.strxfrm = locale.strxfrm

        if collation is None:
            msg = 'collation cannot be an empty sequence'
            raise xpath_error('XPTY0004', msg, self.token)
        elif collation == UNICODE_CODEPOINT_COLLATION \
                or collation == 'collation/codepoint':
            self.lc_collate = None
            self.strcoll = unicode_codepoint_compare
            self.strxfrm = same_string
        elif collation == HTML_ASCII_CASE_INSENSITIVE_COLLATION:
            self.lc_collate = None
            self.strcoll = case_insensitive_compare
            self.strxfrm = casefold
        elif collation.startswith(UNICODE_COLLATION_BASE_URI):
            self.lc_collate = 'en_US.UTF-8'
            self.fallback = True

            for param in urlsplit(collation).query.split(';'):
                if param.startswith('lang='):
                    self.lc_collate = f'{param[5:]}.UTF-8'
                elif param.startswith('fallback='):
                    if param.endswith('yes'):
                        self.fallback = True
                    elif param.endswith('no'):
                        self.fallback = False
        else:
            self.lc_collate = collation

    def __enter__(self) -> 'CollationManager':
        if self.lc_collate is not None:
            # Only one locale set can be used at a time
            _locale_collate_lock.acquire()
            self._current_lc_collate = locale.getlocale(locale.LC_COLLATE)

            try:
                locale.setlocale(locale.LC_COLLATE, self.lc_collate)
            except locale.Error:
                if not self.fallback:
                    self._current_lc_collate = None
                    _locale_collate_lock.release()

                    msg = f"Unsupported collation {self.collation!r}"
                    raise xpath_error('FOCH0002', msg, self.token) from None

                locale.setlocale(locale.LC_COLLATE, 'en_US.UTF-8')

        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        if self._current_lc_collate is not None:
            locale.setlocale(locale.LC_COLLATE, self._current_lc_collate)
            self._current_lc_collate = None
            _locale_collate_lock.release()

    def eq(self, a: Any, b: Any) -> bool:
        if not isinstance(a, str) or not isinstance(b, str):
            return a == b
        return self.strcoll(a, b) == 0

    def ne(self, a: Any, b: Any) -> bool:
        if not isinstance(a, str) or not isinstance(b, str):
            return a != b
        return self.strcoll(a, b) != 0

    def contains(self, a: str, b: str) -> bool:
        return self.strxfrm(a) in self.strxfrm(b)

    def find(self, a: str, b: str) -> int:
        return self.strxfrm(a).find(self.strxfrm(b))
