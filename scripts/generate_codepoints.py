#!/usr/bin/env python
#
# Copyright (c), 2018-2024, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""Codepoints modules generator utility."""

MODULE_HEADER_TEMPLATE = """#
# Copyright (c), 2018-{year}, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or https://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# --- Auto-generated code: don't edit this file ---
#"""

LIST_TEMPLATE = """
{list_name} = [
    {indented_items}
]
"""

DICT_TEMPLATE = """
{dict_name} = {{
    {indented_items}
}}
"""

###
# Unicode versions index: https://www.unicode.org/versions/enumeratedversions.html

UNICODE_DATA_BASE_URL = "https://www.unicode.org/Public/"

UNICODE_VERSIONS = {
    '17.0.0': ('17.0.0/ucd/UnicodeData.txt', '17.0.0/ucd/Blocks.txt'),
    '16.0.0': ('16.0.0/ucd/UnicodeData.txt', '16.0.0/ucd/Blocks.txt'),
    '15.1.0': ('15.1.0/ucd/UnicodeData.txt', '15.1.0/ucd/Blocks.txt'),
    '15.0.0': ('15.0.0/ucd/UnicodeData.txt', '15.0.0/ucd/Blocks.txt'),
    '14.0.0': ('14.0.0/ucd/UnicodeData.txt', '14.0.0/ucd/Blocks.txt'),
    '13.0.0': ('13.0.0/ucd/UnicodeData.txt', '13.0.0/ucd/Blocks.txt'),
    '12.1.0': ('12.1.0/ucd/UnicodeData.txt', '12.1.0/ucd/Blocks.txt'),
    '12.0.0': ('12.0.0/ucd/UnicodeData.txt', '12.0.0/ucd/Blocks.txt'),
    '11.0.0': ('11.0.0/ucd/UnicodeData.txt', '11.0.0/ucd/Blocks.txt'),
    '10.0.0': ('10.0.0/ucd/UnicodeData.txt', '10.0.0/ucd/Blocks.txt'),
    '9.0.0': ('9.0.0/ucd/UnicodeData.txt', '9.0.0/ucd/Blocks.txt'),
    '8.0.0': ('8.0.0/ucd/UnicodeData.txt', '8.0.0/ucd/Blocks.txt'),
    '7.0.0': ('7.0.0/ucd/UnicodeData.txt', '7.0.0/ucd/Blocks.txt'),
    '6.3.0': ('6.3.0/ucd/UnicodeData.txt', '6.3.0/ucd/Blocks.txt'),
    '6.2.0': ('6.2.0/ucd/UnicodeData.txt', '6.2.0/ucd/Blocks.txt'),
    '6.1.0': ('6.1.0/ucd/UnicodeData.txt', '6.1.0/ucd/Blocks.txt'),
    '6.0.0': ('6.0.0/ucd/UnicodeData.txt', '6.0.0/ucd/Blocks.txt'),
    '5.2.0': ('5.2.0/ucd/UnicodeData.txt', '5.2.0/ucd/Blocks.txt'),
    '5.1.0': ('5.1.0/ucd/UnicodeData.txt', '5.1.0/ucd/Blocks.txt'),
    '5.0.0': ('5.0.0/ucd/UnicodeData.txt', '5.0.0/ucd/Blocks.txt'),
    '4.1.0': ('4.1.0/ucd/UnicodeData.txt', '4.1.0/ucd/Blocks.txt'),
    '4.0.1': ('4.0-Update1/UnicodeData-4.0.1.txt', '4.0-Update1/Blocks-4.0.1.txt'),
    '4.0.0': ('4.0-Update/UnicodeData-4.0.0.txt', '4.0-Update/Blocks-4.0.0.txt'),
    '3.2.0': ('3.2-Update/UnicodeData-3.2.0.txt', '3.2-Update/Blocks-3.2.0.txt'),
    '3.1.1': ('3.2-Update/UnicodeData-3.2.0.txt', '3.2-Update/Blocks-3.2.0.txt'),
    '3.1.0': ('3.1-Update/UnicodeData-3.1.0.txt', '3.1-Update/Blocks-4.txt'),
    '3.0.1': ('3.0-Update1/UnicodeData-3.0.1.txt', '3.0-Update/Blocks-3.txt'),
    '3.0.0': ('3.0-Update/UnicodeData-3.0.0.txt', '3.0-Update/Blocks-3.txt'),
    '2.1.9': ('2.1-Update4/UnicodeData-2.1.9.txt', '2.1-Update4/Blocks-2.txt'),
    '2.1.8': ('2.1-Update3/UnicodeData-2.1.8.txt', '2.0-Update/Blocks-1.txt'),
    '2.1.5': ('2.1-Update2/UnicodeData-2.1.5.txt', '2.0-Update/Blocks-1.txt'),
    '2.1.2': ('2.1-Update/UnicodeData-2.1.2.txt', '2.0-Update/Blocks-1.txt'),
    '2.0.0': ('2.0-Update/UnicodeData-2.0.14.txt', '2.0-Update/Blocks-1.txt')
}

UNICODE_CATEGORIES = (
    'C', 'Cc', 'Cf', 'Cs', 'Co', 'Cn',
    'L', 'Lu', 'Ll', 'Lt', 'Lm', 'Lo',
    'M', 'Mn', 'Mc', 'Me',
    'N', 'Nd', 'Nl', 'No',
    'P', 'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po',
    'S', 'Sm', 'Sc', 'Sk', 'So',
    'Z', 'Zs', 'Zl', 'Zp'
)


DEFAULT_CATEGORIES_VERSIONS = ['13.0.0', '14.0.0', '15.0.0', '15.1.0', '16.0.0', '17.0.0']


def version_number(value):
    numbers = value.strip().split('.')
    if len(numbers) != 3 or any(not x.isdigit() for x in numbers) or \
            any(x != str(int(x)) for x in numbers):
        raise ValueError(f"{value!r} is not a version number")
    return value.strip()


def version_info(versions):
    assert isinstance(versions, (tuple, list))
    if not versions:
        return "all versions."
    if len(versions) == 1:
        return f"version {versions[0]}"
    return f"versions {', '.join(versions)}."


def get_unicode_data_url(version):
    try:
        url = UNICODE_VERSIONS[version][0]
    except KeyError:
        url = f'{version}/ucd/UnicodeData.txt'
    return urljoin(UNICODE_DATA_BASE_URL, url)


def get_blocks_url(version):
    try:
        url = UNICODE_VERSIONS[version][1]
    except KeyError:
        url = f'{version}/ucd/Blocks.txt'
    return urljoin(UNICODE_DATA_BASE_URL, url)


def iter_codepoints_with_category(version):
    if version == unidata_version:
        # If requested version matches use Python unicodedata library API
        for cp in range(maxunicode + 1):
            yield cp, category(chr(cp))
        return

    with urlopen(get_unicode_data_url(version)) as res:
        prev_cp = -1

        for line in res.readlines():
            fields = line.split(b';')
            cp = int(fields[0], 16)
            cat = fields[2].decode('utf-8')

            if cp - prev_cp > 1:
                if fields[1].endswith(b', Last>'):
                    # Ranges of codepoints expressed with First and then Last
                    for x in range(prev_cp + 1, cp):
                        yield x, cat
                else:
                    # For default is 'Cn' that means 'Other, not assigned'
                    for x in range(prev_cp + 1, cp):
                        yield x, 'Cn'

            prev_cp = cp
            yield cp, cat

    while cp < maxunicode:
        cp += 1
        yield cp, 'Cn'


def get_unicodedata_categories(version):
    """
    Extracts Unicode categories information from unicodedata library or from normative
    raw data. Each category is represented with an ordered list containing code points
    and code point ranges.

    :return: a dictionary with category names as keys and lists as values.
    """
    categories = {k: [] for k in UNICODE_CATEGORIES}

    major_category = 'C'
    major_start_cp, major_next_cp = 0, 1

    minor_category = 'Cc'
    minor_start_cp, minor_next_cp = 0, 1

    for cp, cat in iter_codepoints_with_category(version):

        if cat[0] != major_category:
            if cp > major_next_cp:
                categories[major_category].append((major_start_cp, cp))
            else:
                categories[major_category].append(major_start_cp)

            major_category = cat[0]
            major_start_cp, major_next_cp = cp, cp + 1

        if cat != minor_category:
            if cp > minor_next_cp:
                categories[minor_category].append((minor_start_cp, cp))
            else:
                categories[minor_category].append(minor_start_cp)

            minor_category = cat
            minor_start_cp, minor_next_cp = cp, cp + 1

    else:
        if major_next_cp == maxunicode + 1:
            categories[major_category].append(major_start_cp)
        else:
            categories[major_category].append((major_start_cp, maxunicode + 1))

        if minor_next_cp == maxunicode + 1:
            categories[minor_category].append(minor_start_cp)
        else:
            categories[minor_category].append((minor_start_cp, maxunicode + 1))

    return categories


def get_unicodedata_blocks(version):
    """
    Extracts Unicode blocks information from normative raw data. Each block is represented
    with as string that expresses a range of codepoints for building an UnicodeSubset().

    :return: a dictionary with block names as keys and strings as values.
    """
    blocks = {}

    with urlopen(get_blocks_url(version)) as res:
        for line in res.readlines():
            if line.startswith((b'#', b'\n', b'\t')):
                continue

            try:
                block_range, block_name = line.decode('utf-8').split('; ')
            except ValueError:
                # old 2.0 format
                block_start, block_end, block_name = line.decode('utf-8').split('; ')
            else:
                block_start, block_end = block_range.split('..')

            block_name = block_name.strip()

            if len(block_start) <= 4:
                block_start = rf"\u{block_start.rjust(4, '0')}"
            else:
                block_start = rf"\U{block_start.rjust(8, '0')}"

            if len(block_end) <= 4:
                block_end = rf"\u{block_end.rjust(4, '0')}"
            else:
                block_end = rf"\U{block_end.rjust(8, '0')}"

            if block_name not in blocks:
                blocks[block_name] = f'{block_start}-{block_end}'
            else:
                blocks[block_name] += f'{block_start}-{block_end}'

        return blocks


def generate_unicode_categories_module(module_path, versions):
    print(f"\nSaving raw Unicode categories to {str(module_path)}")

    with module_path.open('w') as fp:
        print(f"Write module header and generate categories map for version {versions[0]} ...")

        fp.write(MODULE_HEADER_TEMPLATE.format_map({
            'year': datetime.datetime.now().year,
        }))

        categories = get_unicodedata_categories(versions[0])
        categories_repr = pprint.pformat(categories, compact=True)

        fp.write(LIST_TEMPLATE.format_map({
            'list_name': 'UNICODE_VERSIONS',
            'indented_items': '\n   '.join(repr(versions)[1:-1].split('\n'))
        }))

        fp.write(DICT_TEMPLATE.format_map({
            'dict_name': 'UNICODE_CATEGORIES',
            'indented_items': '\n   '.join(categories_repr[1:-1].split('\n'))
        }))

        for ver in versions[1:]:
            print(f"  - Generate diff category map for version {ver} ...")
            base_categories = categories
            categories = get_unicodedata_categories(ver)

            categories_diff = {}
            for k, cps in categories.items():
                cps_base = base_categories[k]
                if cps != cps_base:
                    exclude_cps = [x for x in cps_base if x not in cps]
                    insert_cps = [x for x in cps if x not in cps_base]
                    categories_diff[k] = exclude_cps, insert_cps

            categories_repr = pprint.pformat(categories_diff, compact=True)

            fp.write(DICT_TEMPLATE.format_map({
                'dict_name':  f"DIFF_CATEGORIES_VER_{ver.replace('.', '_')}",
                'indented_items': '\n   '.join(categories_repr[1:-1].split('\n'))
            }))


def generate_unicode_blocks_module(module_path, versions):
    print(f"\nSaving raw Unicode blocks to {str(module_path)}")

    with module_path.open('w') as fp:
        print(f"Write module header and generate blocks map for version {versions[0]} ...")

        fp.write(MODULE_HEADER_TEMPLATE.format_map({
            'year': datetime.datetime.now().year,
        }))

        blocks = get_unicodedata_blocks(versions[0])
        blocks_repr = pprint.pformat(blocks, compact=True, sort_dicts=False)

        fp.write(DICT_TEMPLATE.format_map({
            'dict_name': 'UNICODE_BLOCKS_VER_2_0_0',
            'indented_items': '\n   '.join(
                blocks_repr[1:-1].replace('\\\\', '\\').split('\n')
            )
        }))

        for ver in versions[1:]:
            print(f"  - Generate diff blocks map for version {ver} ...")
            base_blocks = blocks
            blocks = get_unicodedata_blocks(ver)

            blocks_removed = [k for k in base_blocks if k not in blocks]
            blocks_update = {k: v for k, v in blocks.items()
                             if k not in base_blocks or base_blocks[k] != v}

            if blocks_removed:
                removed_repr = pprint.pformat(blocks_removed, compact=True)
                fp.write(LIST_TEMPLATE.format_map({
                    'list_name': f"REMOVED_BLOCKS_VER_{ver.replace('.', '_')}",
                    'indented_items': '\n   '.join(removed_repr[1:-1].split('\n'))
                }))

            if blocks_update:
                update_repr = pprint.pformat(blocks_update, compact=True, sort_dicts=False)
                fp.write(DICT_TEMPLATE.format_map({
                    'dict_name': f"UPDATE_BLOCKS_VER_{ver.replace('.', '_')}",
                    'indented_items': '\n   '.join(
                        update_repr[1:-1].replace('\\\\', '\\').split('\n')
                    )
                }))


if __name__ == '__main__':
    import argparse
    import datetime
    import pathlib
    import pprint
    from sys import maxunicode
    from unicodedata import category, unidata_version
    from urllib.request import urlopen
    from urllib.parse import urljoin

    description = (
        "Generate Unicode codepoints modules. Both modules contain dictionaries "
        "with a compressed representation of the Unicode codepoints, suitable to "
        "be loaded by the elementpath library using UnicodeSubset class. Multiple "
        "versions of Unicode database are represented by additional codepoints in "
        "further dictionaries. For default the generated categories module contains "
        "the data for supported Python releases and pre-releases. For default the "
        "generated blocks module includes all Unicode versions (2.0.0+)."
    )

    parser = argparse.ArgumentParser(
        description=description, usage="%(prog)s [options] dirpath"
    )
    parser.add_argument('-v', '--version', dest='versions', type=version_number,
                        default=[], action='append',
                        help="generates codepoints for specific Unicode version")
    parser.add_argument('dirpath', type=str, help="directory path for generated modules")
    args = parser.parse_args()

    if not args.versions:
        categories_versions = DEFAULT_CATEGORIES_VERSIONS
        blocks_versions = list(reversed(UNICODE_VERSIONS))
    else:
        categories_versions = args.versions = sorted(set(args.versions), reverse=False)
        blocks_versions = list(reversed(args.versions))

    print("+++ Generate Unicode categories and blocks modules +++\n")
    print("Python Unicode data version: {}".format(unidata_version))

    ###
    # Generate Unicode categories module
    print(f"\nGenerate Unicode Categories for {version_info(args.versions)}")

    filename = pathlib.Path(args.dirpath).joinpath('unicode_categories.py')
    if filename.is_file():
        confirm = input("Overwrite existing module %r? [Y/Yes to confirm] " % str(filename))
    else:
        confirm = 'Yes'

    if confirm.strip().upper() not in ('Y', 'YES'):
        print("\nSkip generation of Unicode categories module ...")
    else:
        generate_unicode_categories_module(filename, categories_versions)

    ###
    # Generate Unicode blocks module
    print(f"\nGenerate Unicode Blocks for {version_info(args.versions)}")

    filename = pathlib.Path(args.dirpath).joinpath('unicode_blocks.py')
    if filename.is_file():
        confirm = input("Overwrite existing module %r? [Y/Yes to confirm] " % str(filename))
    else:
        confirm = 'Yes'

    if confirm.strip().upper() not in ('Y', 'YES'):
        print("\nSkip generation of Unicode blocks module ...")
    else:
        generate_unicode_blocks_module(filename, blocks_versions)
