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
# Unicode data version {version}
#
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


def version_number(value):
    numbers = value.strip().split('.')
    if len(numbers) != 3 or any(not x.isdigit() for x in numbers) or \
            any(x != str(int(x)) for x in numbers):
        raise ValueError(f"{value!r} is not a version number")
    return value.strip()


def iter_codepoints_with_category(version):
    if version == unidata_version:
        # If requested version matches use Python unicodedata library API
        print('Version matches, use unicodedata API ...')
        for cp in range(maxunicode + 1):
            yield cp, category(chr(cp))
        return

    print('Version is different, use normative UnicodeData.txt ...')
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

            block_name = block_name.strip().upper()
            block_name = block_name.replace(' ', '').replace('-', '').replace('_', '')

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


if __name__ == '__main__':
    import argparse
    import datetime
    import pathlib
    import pprint
    from sys import maxunicode
    from unicodedata import category, unidata_version
    from urllib.request import urlopen

    description = (
        "Generate Unicode codepoints modules. The modules contain each a "
        "dictionary with a compressed representations of the Unicode codepoints, "
        "suitable to be loaded by the elementpath library using UnicodeSubset "
        "class. The installed generated modules have to be compatible with the "
        "Unicode codepoints library used by the Python interpreter (e.g. if you "
        "need to be compatible with Python 3.8 you can generate Unicode codepoints "
        "up to version 12.1.0)."
    )

    parser = argparse.ArgumentParser(
        description=description, usage="%(prog)s [options] dirpath"
    )
    parser.add_argument('--version', type=version_number, default=unidata_version,
                        help="generate codepoints for a specific Unicode version, for default uses "
                             "the version supported by the Python interpreter.")
    parser.add_argument('dirpath', type=str, help="directory path for generated modules")
    args = parser.parse_args()

    print("+++ Generate Unicode categories module +++\n")
    print("Python Unicode data version {}".format(unidata_version))
    print("Generate Unicode data version {}\n".format(args.version))

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
        print("\nGenerating Unicode categories module ...")

        categories_map = get_unicodedata_categories(args.version)
        print("Saving Unicode categories codepoints to %s\n" % str(filename))

        with open(filename, 'w') as fp:
            categories_repr = pprint.pformat(categories_map, compact=True)
            fp.write(MODULE_TEMPLATE.format_map({
                'year': datetime.datetime.now().year,
                'version': args.version,
                'dict_name': 'RAW_UNICODE_CATEGORIES',
                'indented_items': '\n   '.join(categories_repr[1:-1].split('\n'))
            }))

    ###
    # Generate Unicode blocks module
    filename = pathlib.Path(args.dirpath).joinpath('unicode_blocks.py')
    if filename.is_file():
        confirm = input("Overwrite existing module %r? [Y/Yes to confirm] " % str(filename))
    else:
        confirm = 'Yes'

    if confirm.strip().upper() not in ('Y', 'YES'):
        print("\nSkip generation of Unicode blocks module ...")
    else:
        print("\nGenerating Unicode blocks module ...")

        blocks_map = get_unicodedata_blocks(args.version)
        print("Saving Unicode categories blocks to %s" % str(filename))

        with open(filename, 'w') as fp:
            blocks_repr = pprint.pformat(blocks_map, compact=True, sort_dicts=False)
            fp.write(MODULE_TEMPLATE.format_map({
                'year': datetime.datetime.now().year,
                'version': args.version,
                'dict_name': 'RAW_UNICODE_BLOCKS',
                'indented_items': '\n   '.join(blocks_repr[1:-1].replace('\\\\', '\\').split('\n'))
            }))
