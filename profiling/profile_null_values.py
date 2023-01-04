#!/usr/bin/env python
#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from timeit import timeit
from memory_profiler import profile

from elementpath import XPath1Parser
from elementpath.xpath_tokens import ValueToken


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def xpath_none_null_values():
    null_values = [None for _ in range(50000)]
    return null_values


@profile
def xpath_list_null_values():
    null_values = [[] for _ in range(50000)]
    return null_values


@profile
def xpath_tuple_null_values():
    null_values = [() for _ in range(50000)]
    return null_values


def is_empty_sequence(s):
    return not s and isinstance(s, list)


if __name__ == '__main__':
    print('*' * 68)
    print("*** Memory and timing profile of XPath null values alternatives  ***")
    print('*' * 68)
    print()

    NUMBER = 1000
    SETUP = 'from __main__ import obj1, obj2, is_empty_sequence'
    obj1 = []
    obj2 = ['foo', 'bar']

    print("*** Profile evaluation ***\n")

    run_timeit('[None for _ in range(10000)]', number=NUMBER)
    run_timeit('[[] for _ in range(10000)]', number=NUMBER)
    run_timeit('[() for _ in range(10000)]', number=NUMBER)

    print()

    run_timeit('for _ in range(10000): obj1 is None', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj1 == []', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj1 == ()', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj1 and isinstance(obj1, list)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj1 and isinstance(obj1, tuple)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): is_empty_sequence(obj1)', SETUP, NUMBER)

    print()

    run_timeit('for _ in range(10000): obj2 is None', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj2 == []', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj2 == ()', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj2 and isinstance(obj2, list)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj2 and isinstance(obj2, tuple)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): is_empty_sequence(obj2)', SETUP, NUMBER)

    print()
    print("*** Profile memory ***\n")

    xpath_none_null_values()
    xpath_list_null_values()
    xpath_tuple_null_values()
