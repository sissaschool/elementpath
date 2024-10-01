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

MODULE_TEMPLATE = """#
# Copyright (c), 2018-{year}, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or https://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# --- Auto-generated code: don't edit this file ---
#
# {unicode_version_info}
#
MIN_UNICODE_VERSION = {dict_unicode_version!r}

{dict_name} = {{
    {indented_items}
}}
"""

DIFF_DICT_TEMPLATE = """
{dict_name} = {{
    {indented_items}
}}
"""

###
# URLs to Unicode reference web pages
UNICODE_ENUMERATED_VERSIONS_URL = "https://www.unicode.org/versions/enumeratedversions.html"

UNICODE_DATA_URL = "https://www.unicode.org/Public/{}/ucd/UnicodeData.txt"
BLOCKS_DATA_URL = "https://www.unicode.org/Public/{}/ucd/Blocks.txt"

UNICODE_CATEGORIES = (
        'C', 'Cc', 'Cf', 'Cs', 'Co', 'Cn',
        'L', 'Lu', 'Ll', 'Lt', 'Lm', 'Lo',
        'M', 'Mn', 'Mc', 'Me',
        'N', 'Nd', 'Nl', 'No',
        'P', 'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po',
        'S', 'Sm', 'Sc', 'Sk', 'So',
        'Z', 'Zs', 'Zl', 'Zp'
    )

DEFAULT_UNICODE_VERSIONS = ('12.1.0', '13.0.0', '14.0.0', '15.0.0', '15.1.0', '16.0.0')


def version_number(value):
    numbers = value.strip().split('.')
    if len(numbers) != 3 or any(not x.isdigit() for x in numbers) or \
            any(x != str(int(x)) for x in numbers):
        raise ValueError(f"{value!r} is not a version number")
    return value.strip()


def unicode_version_info(versions):
    assert isinstance(versions, (tuple, list))
    if len(versions) == 1:
        return f"Unicode data version {versions[0]}"
    return f"Unicode data for versions {', '.join(versions)}."


def iter_codepoints_with_category(version):
    if version == unidata_version:
        # If requested version matches use Python unicodedata library API
        for cp in range(maxunicode + 1):
            yield cp, category(chr(cp))
        return

    with urlopen(UNICODE_DATA_URL.format(version)) as res:
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
    with urlopen(BLOCKS_DATA_URL.format(version)) as res:
        for line in res.readlines():
            if line.startswith((b'#', b'\n')):
                continue

            block_range, block_name = line.decode('utf-8').split('; ')

            block_name = block_name.strip()

            block_start, block_end = block_range.split('..')
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
        print("Write module header and generate raw categories map ...")
        categories = get_unicodedata_categories(versions[0])
        categories_repr = pprint.pformat(categories, compact=True)

        fp.write(MODULE_TEMPLATE.format_map({
            'year': datetime.datetime.now().year,
            'unicode_version_info': unicode_version_info(versions),
            'dict_unicode_version': versions[0],
            'dict_name': 'RAW_UNICODE_CATEGORIES',
            'indented_items': '\n   '.join(categories_repr[1:-1].split('\n'))
        }))

        for ver in versions[1:]:
            print(f"  - Generate additional category map for version {ver} ...")
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

            fp.write(DIFF_DICT_TEMPLATE.format_map({
                'dict_name':  f"DIFF_CATEGORIES_VER_{ver.replace('.', '_')}",
                'indented_items': '\n   '.join(categories_repr[1:-1].split('\n'))
            }))


def generate_unicode_blocks_module(module_path, versions):
    print(f"\nSaving raw Unicode blocks to {str(module_path)}")

    with module_path.open('w') as fp:
        print("Write module header and generate raw blocks map ...")
        blocks = get_unicodedata_blocks(versions[0])
        blocks_repr = pprint.pformat(blocks, compact=True, sort_dicts=False)

        fp.write(MODULE_TEMPLATE.format_map({
            'year': datetime.datetime.now().year,
            'unicode_version_info': unicode_version_info(versions),
            'dict_unicode_version': versions[0],
            'dict_name': 'RAW_UNICODE_BLOCKS',
            'indented_items': '\n   '.join(
                blocks_repr[1:-1].replace('\\\\', '\\').split('\n')
            )
        }))

        for ver in versions[1:]:
            print(f"  - Generate additional blocks map for version {ver} ...")
            base_blocks = blocks
            blocks = get_unicodedata_blocks(ver)

            blocks_diff = {k: v for k, v in blocks.items()
                           if k not in base_blocks or base_blocks[k] != v}
            blocks_repr = pprint.pformat(blocks_diff, compact=True, sort_dicts=False)

            fp.write(DIFF_DICT_TEMPLATE.format_map({
                'dict_name': f"DIFF_BLOCKS_VER_{ver.replace('.', '_')}",
                'indented_items': '\n   '.join(
                    blocks_repr[1:-1].replace('\\\\', '\\').split('\n')
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

    description = (
        "Generate Unicode codepoints modules. Both modules contain dictionaries "
        "with a compressed representation of the Unicode codepoints, suitable to "
        "be loaded by the elementpath library using UnicodeSubset class. Multiple "
        "versions of Unicode database are represented by additional codepoints in "
        "further dictionaries."
    )

    parser = argparse.ArgumentParser(
        description=description, usage="%(prog)s [options] dirpath"
    )
    parser.add_argument('-v', '--version', dest='versions', type=version_number,
                        default=[], action='append',
                        help="generates codepoints for specific Unicode versions, for default "
                             "are the ones available with supported Python versions.")
    parser.add_argument('dirpath', type=str, help="directory path for generated modules")
    args = parser.parse_args()

    if not args.versions:
        args.versions.extend(DEFAULT_UNICODE_VERSIONS)
    else:
        args.versions[:] = sorted(set(args.versions), reverse=False)

    print("+++ Generate Unicode categories module +++\n")
    print("Python Unicode data version: {}".format(unidata_version))
    print(f"Generate {unicode_version_info(args.versions)}\n")

    ###
    # Generate Unicode categories module
    filename = pathlib.Path(args.dirpath).joinpath('unicode_categories.py')
    if filename.is_file():
        confirm = input("Overwrite existing module %r? [Y/Yes to confirm] " % str(filename))
    else:
        confirm = 'Yes'

    if confirm.strip().upper() not in ('Y', 'YES'):
        print("\nSkip generation of Unicode categories module ...\n")
    else:
        generate_unicode_categories_module(filename, args.versions)

    ###
    # Generate Unicode blocks module
    filename = pathlib.Path(args.dirpath).joinpath('unicode_blocks.py')
    if filename.is_file():
        confirm = input("\nOverwrite existing module %r? [Y/Yes to confirm] " % str(filename))
    else:
        confirm = 'Yes'

    if confirm.strip().upper() not in ('Y', 'YES'):
        print("\nSkip generation of Unicode blocks module ...")
    else:
        generate_unicode_blocks_module(filename, args.versions)
