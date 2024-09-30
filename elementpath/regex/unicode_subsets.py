#
# Copyright (c), 2016-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
This module defines Unicode character categories and blocks.
"""
import importlib
from sys import maxunicode
from typing import cast, Dict, List, Union, Optional
from unicodedata import unidata_version

from elementpath._typing import Iterable, Iterator, MutableSet
from elementpath.helpers import unicode_block_key
from .codepoints import CodePoint, code_point_order, code_point_repr, \
    iter_code_points, get_code_point_range

CodePointsArgType = Union[str, 'UnicodeSubset', List[CodePoint], Iterable[CodePoint]]

UNICODE_VERSION_INFO = tuple(int(x) for x in unidata_version.split('.'))


class RegexError(Exception):
    """
    Error in a regular expression or in a character class specification.
    This exception is derived from `Exception` base class and is raised
    only by the regex subpackage.
    """


def iterparse_character_subset(s: str, expand_ranges: bool = False) -> Iterator[CodePoint]:
    """
    Parses a regex character subset, generating a sequence of code points
    and code points ranges. An unescaped hyphen (-) that is not at the
    start or at the end is interpreted as range specifier.

    :param s: a string representing the character subset.
    :param expand_ranges: if set to `True` then expands character ranges.
    :return: yields integers or couples of integers.
    """
    escaped = False
    on_range = False
    char = ''
    length = len(s)
    subset_index_iterator = iter(range(len(s)))
    for k in subset_index_iterator:
        if k == 0:
            char = s[0]
            if char == '\\':
                escaped = True
            elif char in r'[]' and length > 1:
                raise RegexError("bad character %r at position 0" % char)
            elif expand_ranges:
                yield ord(char)
            elif length <= 2 or s[1] != '-':
                yield ord(char)
        elif s[k] == '-':
            if escaped or (k == length - 1):
                char = s[k]
                yield ord(char)
                escaped = False
            elif on_range:
                char = s[k]
                yield ord(char)
                on_range = False
            else:
                # Parse character range
                on_range = True
                k = next(subset_index_iterator)
                end_char = s[k]
                if end_char == '\\' and (k < length - 1):
                    if s[k + 1] in r'-|.^?*+{}()[]':
                        k = next(subset_index_iterator)
                        end_char = s[k]
                    elif s[k + 1] in r'sSdDiIcCwWpP':
                        msg = "bad character range '%s-\\%s' at position %d: %r"
                        raise RegexError(msg % (char, s[k + 1], k - 2, s))

                if ord(char) > ord(end_char):
                    msg = "bad character range '%s-%s' at position %d: %r"
                    raise RegexError(msg % (char, end_char, k - 2, s))
                elif expand_ranges:
                    yield from range(ord(char) + 1, ord(end_char) + 1)
                else:
                    yield ord(char), ord(end_char) + 1

        elif s[k] in r'|.^?*+{}()':
            if escaped:
                escaped = False
            on_range = False
            char = s[k]
            yield ord(char)
        elif s[k] in r'[]':
            if not escaped and length > 1:
                raise RegexError("bad character %r at position %d" % (s[k], k))
            escaped = on_range = False
            char = s[k]
            if k >= length - 2 or s[k + 1] != '-':
                yield ord(char)
        elif s[k] == '\\':
            if escaped:
                escaped = on_range = False
                char = '\\'
                yield ord(char)
            else:
                escaped = True
        else:
            if escaped:
                escaped = False
                yield ord('\\')
            on_range = False
            char = s[k]
            if k >= length - 2 or s[k + 1] != '-':
                yield ord(char)
    if escaped:
        yield ord('\\')


class UnicodeSubset(MutableSet[CodePoint]):
    """
    Represents a subset of Unicode code points, implemented with an ordered list of
    integer values and ranges. Codepoints can be added or discarded using sequences
    of integer values and ranges or with strings equivalent to regex character set.

    :param codepoints: a sequence of integer values and ranges, another UnicodeSubset \
    instance ora a string equivalent of a regex character set.
    """
    __slots__ = '_codepoints',
    _codepoints: List[CodePoint]

    def __init__(self, codepoints: Optional[CodePointsArgType] = None) -> None:
        if not codepoints:
            self._codepoints = list()
        elif isinstance(codepoints, list):
            self._codepoints = sorted(codepoints, key=code_point_order)
        elif isinstance(codepoints, UnicodeSubset):
            self._codepoints = codepoints.codepoints.copy()
        else:
            self._codepoints = list()
            self.update(codepoints)

    @classmethod
    def from_raw(cls, raw_data: List[CodePoint]) -> 'UnicodeSubset':
        subset = cls()
        subset._codepoints = raw_data.copy()
        return subset

    @property
    def codepoints(self) -> List[CodePoint]:
        return self._codepoints

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self) -> str:
        return ''.join(code_point_repr(cp) for cp in self._codepoints)

    def copy(self) -> 'UnicodeSubset':
        return self.__copy__()

    def __copy__(self) -> 'UnicodeSubset':
        subset = self.__class__()
        subset._codepoints = self._codepoints.copy()
        return subset

    def __reversed__(self) -> Iterator[int]:
        for item in reversed(self._codepoints):
            if isinstance(item, int):
                yield item
            else:
                yield from reversed(range(item[0], item[1]))

    def complement(self) -> Iterator[CodePoint]:
        last_cp = 0
        for cp in self._codepoints:
            if isinstance(cp, int):
                cp = cp, cp + 1

            diff = cp[0] - last_cp
            if diff > 2:
                yield last_cp, cp[0]
            elif diff == 2:
                yield last_cp
                yield last_cp + 1
            elif diff == 1:
                yield last_cp
            elif diff:
                raise ValueError("unordered code points found in {!r}".format(self))
            last_cp = cp[1]

        if last_cp < maxunicode:
            yield last_cp, maxunicode + 1
        elif last_cp == maxunicode:
            yield maxunicode

    def iter_characters(self) -> Iterator[str]:
        return map(chr, self.__iter__())

    #
    # MutableSet's abstract methods implementation
    def __contains__(self, value: object) -> bool:
        if not isinstance(value, int):
            try:
                value = ord(value)  # type: ignore[arg-type]
            except TypeError:
                return False

        for cp in self._codepoints:
            if not isinstance(cp, int):
                if cp[0] > value:
                    return False
                elif cp[1] <= value:
                    continue
                else:
                    return True
            elif cp > value:
                return False
            elif cp == value:
                return True
        return False

    def __iter__(self) -> Iterator[int]:
        for cp in self._codepoints:
            if isinstance(cp, int):
                yield cp
            else:
                yield from range(*cp)

    def __len__(self) -> int:
        k = 0
        for _ in self:
            k += 1
        return k

    def update(self, *others: Union[str, Iterable[CodePoint]]) -> None:
        for value in others:
            if isinstance(value, str):
                for cp in iter_code_points(iterparse_character_subset(value), reverse=True):
                    self.add(cp)
            else:
                for cp in iter_code_points(value, reverse=True):
                    self.add(cp)

    def add(self, value: CodePoint) -> None:
        try:
            start_value, end_value = get_code_point_range(value)  # type: ignore[misc]
        except TypeError:
            raise ValueError("{!r} is not a Unicode code point value/range".format(value))

        code_points = self._codepoints
        last_index = len(code_points) - 1
        for k, cp in enumerate(code_points):
            if isinstance(cp, int):
                cp = cp, cp + 1

            if end_value < cp[0]:
                code_points.insert(k, value)
            elif start_value > cp[1]:
                continue
            elif end_value > cp[1]:
                if k == last_index:
                    code_points[k] = min(cp[0], start_value), end_value
                else:
                    next_cp = code_points[k + 1]
                    higher_bound = next_cp if isinstance(next_cp, int) else next_cp[0]
                    if end_value <= higher_bound:
                        code_points[k] = min(cp[0], start_value), end_value
                    else:
                        code_points[k] = min(cp[0], start_value), higher_bound
                        start_value = higher_bound
                        continue
            elif start_value < cp[0]:
                code_points[k] = start_value, cp[1]
            break
        else:
            self._codepoints.append(value)

    def difference(self, other: 'UnicodeSubset') -> 'UnicodeSubset':
        subset = self.__copy__()
        subset.difference_update(other)
        return subset

    def difference_update(self, *others: Union[str, Iterable[CodePoint]]) -> None:
        for value in others:
            if isinstance(value, str):
                for cp in iter_code_points(iterparse_character_subset(value), reverse=True):
                    self.discard(cp)
            else:
                for cp in iter_code_points(value, reverse=True):
                    self.discard(cp)

    def discard(self, value: CodePoint) -> None:
        try:
            start_cp, end_cp = get_code_point_range(value)  # type: ignore[misc]
        except TypeError:
            raise ValueError("{!r} is not a Unicode code point value/range".format(value))

        code_points = self._codepoints
        for k in reversed(range(len(code_points))):
            cp = code_points[k]
            if isinstance(cp, int):
                cp = cp, cp + 1

            if start_cp >= cp[1]:
                break
            elif end_cp >= cp[1]:
                if start_cp <= cp[0]:
                    del code_points[k]
                elif start_cp - cp[0] > 1:
                    code_points[k] = cp[0], start_cp
                else:
                    code_points[k] = cp[0]
            elif end_cp > cp[0]:
                if start_cp <= cp[0]:
                    if cp[1] - end_cp > 1:
                        code_points[k] = end_cp, cp[1]
                    else:
                        code_points[k] = cp[1] - 1
                else:
                    if cp[1] - end_cp > 1:
                        code_points.insert(k + 1, (end_cp, cp[1]))
                    else:
                        code_points.insert(k + 1, cp[1] - 1)
                    if start_cp - cp[0] > 1:
                        code_points[k] = cp[0], start_cp
                    else:
                        code_points[k] = cp[0]

    #
    # MutableSet's mixin methods override
    def clear(self) -> None:
        del self._codepoints[:]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Iterable):
            return NotImplemented
        elif isinstance(other, UnicodeSubset):
            return self._codepoints == other._codepoints
        else:
            return self._codepoints == other

    def __ior__(self, other: object) -> 'UnicodeSubset':
        if not isinstance(other, Iterable):
            return NotImplemented
        elif isinstance(other, UnicodeSubset):
            other = reversed(other._codepoints)
        elif isinstance(other, str):
            other = reversed(UnicodeSubset(other)._codepoints)
        else:
            other = iter_code_points(other, reverse=True)

        for cp in other:
            self.add(cp)
        return self

    def __or__(self, other: object) -> 'UnicodeSubset':
        obj = self.__copy__()
        return obj.__ior__(other)

    def __isub__(self, other: object) -> 'UnicodeSubset':
        if not isinstance(other, Iterable):
            return NotImplemented
        elif isinstance(other, UnicodeSubset):
            other = reversed(other._codepoints)
        elif isinstance(other, str):
            other = reversed(UnicodeSubset(other)._codepoints)
        else:
            other = iter_code_points(other, reverse=True)

        for cp in other:
            self.discard(cp)
        return self

    def __sub__(self, other: object) -> 'UnicodeSubset':
        obj = self.__copy__()
        return obj.__isub__(other)

    __rsub__ = __sub__

    def __iand__(self, other: object) -> 'UnicodeSubset':
        if not isinstance(other, Iterable):
            return NotImplemented

        for value in (self - other):
            self.discard(value)
        return self

    def __and__(self, other: object) -> 'UnicodeSubset':
        obj = self.__copy__()
        return obj.__iand__(other)

    def __ixor__(self, other: object) -> 'UnicodeSubset':
        if other is self:
            self.clear()
            return self
        elif not isinstance(other, Iterable):
            return NotImplemented
        elif not isinstance(other, UnicodeSubset):
            other = UnicodeSubset(cast(Union[str, Iterable[CodePoint]], other))

        for value in other:
            if value in self:
                self.discard(value)
            else:
                self.add(value)
        return self

    def __xor__(self, other: object) -> 'UnicodeSubset':
        obj = self.__copy__()
        return obj.__ixor__(other)


###
# Build Unicode data structures from raw data modules
#
UNICODE_CATEGORIES: Dict[str, UnicodeSubset]
UNICODE_BLOCKS: Dict[str, UnicodeSubset]


def install_unicode_categories(module_name: str) -> None:
    module = importlib.import_module(module_name)
    raw_categories = module.RAW_UNICODE_CATEGORIES.copy()

    for name, diff_categories in filter(lambda x: x[0].startswith('DIFF_CATEGORIES_VER_'),
                                        module.__dict__.items()):
        diff_version_info = tuple(int(x) for x in name[20:].split('_'))
        if len(diff_version_info) != 3 or UNICODE_VERSION_INFO < diff_version_info:
            break

        for k, (exclude_cps, insert_cps) in diff_categories.items():
            values = []
            additional = iter(insert_cps)
            cpa = next(additional, None)
            cpa_int = cpa[0] if isinstance(cpa, tuple) else cpa

            for cp in raw_categories[k]:
                if cp in exclude_cps:
                    continue

                cp_int = cp[0] if isinstance(cp, tuple) else cp
                while cpa_int is not None and cpa_int <= cp_int:
                    values.append(cpa)
                    cpa = next(additional, None)
                    cpa_int = cpa[0] if isinstance(cpa, tuple) else cpa
                else:
                    values.append(cp)
            else:
                if cpa is not None:
                    values.append(cpa)
                    values.extend(additional)

            raw_categories[k] = values

    global UNICODE_CATEGORIES
    UNICODE_CATEGORIES = {
        k: UnicodeSubset.from_raw(cast(List[CodePoint], v)) for k, v in raw_categories.items()
    }


def install_unicode_blocks(module_name: str) -> None:
    module = importlib.import_module(module_name)
    raw_blocks = module.RAW_UNICODE_BLOCKS.copy()

    for name, diff_blocks in filter(lambda x: x[0].startswith('DIFF_BLOCKS_VER_'),
                                    module.__dict__.items()):
        diff_version_info = tuple(int(x) for x in name[16:].split('_'))
        if len(diff_version_info) != 3 or UNICODE_VERSION_INFO < diff_version_info:
            break

        raw_blocks.update(diff_blocks)

    global UNICODE_BLOCKS
    UNICODE_BLOCKS = {
        unicode_block_key(k): UnicodeSubset(v) for k, v in raw_blocks.items()
    }

    # Define the special block "No_Block", that contains all the other codepoints not
    # belonging to a defined block (https://www.unicode.org/Public/UNIDATA/Blocks.txt)
    no_block = UnicodeSubset([(0, maxunicode + 1)])
    for v in UNICODE_BLOCKS.values():
        no_block -= v
    UNICODE_BLOCKS['NOBLOCK'] = no_block


install_unicode_categories('elementpath.regex.unicode_categories')
install_unicode_blocks('elementpath.regex.unicode_blocks')


def unicode_subset(name: str) -> UnicodeSubset:
    if name.startswith('Is'):
        try:
            return UNICODE_BLOCKS[unicode_block_key(name[2:])]
        except KeyError:
            raise RegexError(f"{name!r} doesn't match any Unicode block")
    else:
        try:
            return UNICODE_CATEGORIES[name]
        except KeyError:
            raise RegexError(f"{name!r} doesn't match any Unicode category")
