#!/usr/bin/env python
#
# Copyright (c), 2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from timeit import timeit
from memory_profiler import profile

from elementpath.regex import UNICODE_CATEGORIES, UnicodeSubset


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def unicode_subset_objects():
    return [UnicodeSubset('\U00020000-\U0002A6D6') for _ in range(10000)]


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of UnicodeSubset class       ***")
    print("***" + ' ' * 56 + "***")
    print("*** Note: save ~28% of memory with __slots__ (from v2.2.3) ***")
    print('*' * 62)
    print()

    unicode_subset_objects()

    subset = UNICODE_CATEGORIES['C']
    SETUP = 'from __main__ import subset'
    NUMBER = 10000

    run_timeit('1328 in subset   # True ', SETUP, NUMBER)
    run_timeit('1329 in subset   # False', SETUP, NUMBER)
    run_timeit('72165 in subset  # True ', SETUP, NUMBER)
    run_timeit('72872 in subset  # False', SETUP, NUMBER)
