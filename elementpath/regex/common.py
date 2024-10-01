#
# Copyright (c), 2016-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from importlib import import_module
from itertools import chain
from sys import maxunicode
from typing import Dict, List, Union

from unicodedata import unidata_version

from elementpath.helpers import unicode_block_key
from .codepoints import CodePoint
from .unicode_subsets import RegexError, UnicodeSubset

###
#  Unicode data version info
_unicode_categories_version = unidata_version
_unicode_blocks_version = unidata_version


def unicode_categories_version() -> str:
    """Returns the Unicode data version of the installed categories."""
    return _unicode_categories_version


def unicode_blocks_version() -> str:
    """Returns the Unicode data version of the installed blocks."""
    return _unicode_blocks_version


###
# API for installing and accessing Unicode data categories and blocks.
# Installed blocks and categories are built lazily when requested.
#
_unicode_categories: Dict[str, Union[List[CodePoint], UnicodeSubset]]
_unicode_blocks: Dict[str, Union[str, UnicodeSubset]]


def install_unicode_categories(module_name: str) -> None:
    """Install the Unicode categories taking data from the raw categories module provided."""
    global _unicode_categories_version
    global _unicode_categories

    module = import_module(module_name)
    raw_categories = module.RAW_UNICODE_CATEGORIES.copy()
    _unicode_categories_version = module.MIN_UNICODE_VERSION

    max_version = tuple(int(x) for x in unidata_version.split('.'))
    module_min_version = tuple(int(x) for x in module.MIN_UNICODE_VERSION.split('.'))
    if max_version < module_min_version:
        raise ValueError("Can't install Unicode categories because the minimum version "
                         "provided by the module is too high for this Python release")

    for name, diff_categories in filter(lambda x: x[0].startswith('DIFF_CATEGORIES_VER_'),
                                        module.__dict__.items()):

        diff_version = tuple(int(x) for x in name[20:].split('_'))
        if len(diff_version) != 3 or max_version < diff_version:
            break

        _unicode_categories_version = diff_version

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

    _unicode_categories = raw_categories


def install_unicode_blocks(module_name: str) -> None:
    """Install the Unicode blocks taking data from the raw blocks module provided."""
    global _unicode_blocks_version
    global _unicode_blocks

    module = import_module(module_name)
    raw_blocks = module.RAW_UNICODE_BLOCKS.copy()
    _unicode_blocks_version = module.MIN_UNICODE_VERSION

    max_version = tuple(int(x) for x in unidata_version.split('.'))
    module_min_version = tuple(int(x) for x in module.MIN_UNICODE_VERSION.split('.'))
    if max_version < module_min_version:
        raise ValueError("Can't install Unicode blocks because the minimum version "
                         "provided by the module is too high for this Python release")

    for name, diff_blocks in filter(lambda x: x[0].startswith('DIFF_BLOCKS_VER_'),
                                    module.__dict__.items()):

        diff_version = tuple(int(x) for x in name[16:].split('_'))
        if len(diff_version) != 3 or max_version < diff_version:
            break

        raw_blocks.update(diff_blocks)
        _unicode_blocks_version = diff_version

    _unicode_blocks = {unicode_block_key(k): v for k, v in raw_blocks.items()}


def get_unicode_subset(name: str) -> UnicodeSubset:
    """Retrieve a Unicode subset by name, raising a RegexError if it cannot be retrieved."""
    if name[:2] == 'Is':
        try:
            return unicode_block(name[2:])
        except KeyError:
            raise RegexError(f"{name!r} doesn't match any Unicode block")
    else:
        try:
            return unicode_category(name)
        except KeyError:
            raise RegexError(f"{name!r} doesn't match any Unicode category")


def unicode_category(name: str) -> UnicodeSubset:
    """
    Returns the Unicode category subset addressed by the provided name, raising a
    KeyError if it's not found.
    """
    subset = _unicode_categories[name]
    if not isinstance(subset, UnicodeSubset):
        subset = _unicode_categories[name] = UnicodeSubset(subset)
    return subset


def unicode_block(name: str) -> UnicodeSubset:
    """
    Returns the Unicode block subset addressed by the provided name, raising a
    KeyError if it's not found. The lookup is done without considering the
    casing, spaces, hyphens and underscores.
    """
    key = unicode_block_key(name)
    try:
        subset = _unicode_blocks[key]
    except KeyError:
        if key != 'NOBLOCK':
            raise

        # Define the special block "No_Block", that contains all the other codepoints not
        # belonging to a defined block (https://www.unicode.org/Public/UNIDATA/Blocks.txt)
        no_block = UnicodeSubset([(0, maxunicode + 1)])
        for v in _unicode_blocks.values():
            no_block -= v
        _unicode_blocks['NOBLOCK'] = no_block
        return no_block

    else:
        if not isinstance(subset, UnicodeSubset):
            subset = _unicode_blocks[key] = UnicodeSubset(subset)
        return subset


# Install Unicode categories and blocks from predefined modules
install_unicode_categories('elementpath.regex.unicode_categories')
install_unicode_blocks('elementpath.regex.unicode_blocks')


I_SHORTCUT_REPLACE = (
    ":A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
    "\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

C_SHORTCUT_REPLACE = (
    "-.0-9:A-Z_a-z\u00B7\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u037D\u037F-\u1FFF\u200C-"
    "\u200D\u203F\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

S_SHORTCUT_SET = UnicodeSubset(' \n\t\r')
D_SHORTCUT_SET = UnicodeSubset()
D_SHORTCUT_SET._codepoints = unicode_category('Nd').codepoints
I_SHORTCUT_SET = UnicodeSubset(I_SHORTCUT_REPLACE)
C_SHORTCUT_SET = UnicodeSubset(C_SHORTCUT_REPLACE)
W_SHORTCUT_SET = UnicodeSubset(chain(
    unicode_category('L').codepoints,
    unicode_category('M').codepoints,
    unicode_category('N').codepoints,
    unicode_category('S').codepoints
))

# Single and Multi character escapes
CHARACTER_ESCAPES = {
    # Single-character escapes
    '\\n': '\n',
    '\\r': '\r',
    '\\t': '\t',
    '\\|': '|',
    '\\.': '.',
    '\\-': '-',
    '\\^': '^',
    '\\?': '?',
    '\\*': '*',
    '\\+': '+',
    '\\{': '{',
    '\\}': '}',
    '\\(': '(',
    '\\)': ')',
    '\\[': '[',
    '\\]': ']',
    '\\\\': '\\',

    # Multi-character escapes
    '\\s': S_SHORTCUT_SET,
    '\\S': S_SHORTCUT_SET,
    '\\d': D_SHORTCUT_SET,
    '\\D': D_SHORTCUT_SET,
    '\\i': I_SHORTCUT_SET,
    '\\I': I_SHORTCUT_SET,
    '\\c': C_SHORTCUT_SET,
    '\\C': C_SHORTCUT_SET,
    '\\w': W_SHORTCUT_SET,
    '\\W': W_SHORTCUT_SET,
}
