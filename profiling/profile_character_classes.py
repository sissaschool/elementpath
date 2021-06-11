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

from elementpath.regex import CharacterClass


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def character_class_objects():
    return [CharacterClass(r'\c') for _ in range(10000)]


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of CharacterClass class      ***")
    print("***" + ' ' * 56 + "***")
    print("*** Note: save ~15% of memory with __slots__ (from v2.2.3) ***")
    print('*' * 62)
    print()

    character_class_objects()

    character_class = CharacterClass(r'\c')
    character_class -= CharacterClass(r'\i')
    SETUP = 'from __main__ import character_class'
    NUMBER = 10000

    run_timeit('"9" in character_class   # True ', SETUP, NUMBER)
    run_timeit('"q" in character_class   # False', SETUP, NUMBER)
    run_timeit('8256 in character_class  # True ', SETUP, NUMBER)
    run_timeit('8257 in character_class  # False', SETUP, NUMBER)
