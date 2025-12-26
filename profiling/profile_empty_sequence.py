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
from elementpath.sequences import xlist  # noqa


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


if __name__ == '__main__':
    print('*' * 68)
    print("*** Memory and timing profile of XPath null values alternatives  ***")
    print('*' * 68)
    print()

    NUMBER = 1000
    SETUP = 'from __main__ import xlist'

    print("*** Profile evaluation ***\n")

    run_timeit('[None for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[[] for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[xlist() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[[] for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('xlist([1])', SETUP, NUMBER)
    run_timeit('[xlist() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[xlist() for _ in range(10000)]', SETUP, NUMBER)

    print()

    run_timeit('[x for x in range(10000)]', SETUP, NUMBER)
    run_timeit('tuple([x for x in range(10000)])', SETUP, NUMBER)
    run_timeit('list([x for x in range(10000)])', SETUP, NUMBER)
    run_timeit('xlist([x for x in range(10000)])', SETUP, NUMBER)

    run_timeit('\nv = [x for x in range(10000)]\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = tuple([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = list([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = xlist([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)
