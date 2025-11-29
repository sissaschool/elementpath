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
import sys
from timeit import timeit
from elementpath.sequences import XSequence, empty_sequence


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


def fg():
    yield from range(10000)


def is_empty_sequence(s):
    return not s and isinstance(s, list)


if __name__ == '__main__':
    print('*' * 68)
    print("*** Memory and timing profile of XPath null values alternatives  ***")
    print('*' * 68)
    print()

    NUMBER = 1000
    SETUP = ('from __main__ import fg, obj1, obj2, t1, t2, t3, is_empty_sequence, '
             'empty_sequence, XSequence')
    obj1 = []
    obj2 = ['foo', 'bar']
    t1 = (9, 8)
    t2 = ()
    t3 = ()

    print("*** Profile evaluation ***\n")

    run_timeit('[None for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[empty_sequence for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[XSequence() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[[] for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('XSequence([1])', SETUP, NUMBER)
    run_timeit('[XSequence() for _ in range(10000)]', SETUP, NUMBER)
    run_timeit('[XSequence() for _ in range(10000)]', SETUP, NUMBER)

    print()

    run_timeit('[x for x in range(10000)]', SETUP, NUMBER)
    run_timeit('tuple([x for x in range(10000)])', SETUP, NUMBER)
    run_timeit('list([x for x in range(10000)])', SETUP, NUMBER)
    #run_timeit('make_sequence([x for x in range(10000)])', SETUP, NUMBER)
    #run_timeit('make_sequence(tuple([x for x in range(10000)]))', SETUP, NUMBER)
    run_timeit('XSequence([x for x in range(10000)])', SETUP, NUMBER)

    run_timeit('\nv = [x for x in range(10000)]\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = tuple([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = list([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)
    run_timeit('\nv = XSequence([x for x in range(10000)])\nfor _ in v: pass', SETUP, NUMBER)

    sys.exit()

    print()

    run_timeit('for _ in range(10000): obj1 is None', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj1 is EmptySequence', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj1 == []', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj1 == ()', SETUP, NUMBER)
    run_timeit('for _ in range(10000): t1 == t2', SETUP, NUMBER)
    run_timeit('for _ in range(10000): t1 is t2', SETUP, NUMBER)
    run_timeit('for _ in range(10000): t2 == t3', SETUP, NUMBER)
    run_timeit('for _ in range(10000): t2 is t3', SETUP, NUMBER)

    run_timeit('for _ in range(10000): not obj1 and isinstance(obj1, list)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj1 and isinstance(obj1, tuple)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): is_empty_sequence(obj1)', SETUP, NUMBER)

    print()

    run_timeit('for _ in range(10000): obj2 is None', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj2 == []', SETUP, NUMBER)
    run_timeit('for _ in range(10000): obj2 == ()', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj2 and isinstance(obj2, list)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj2 and isinstance(obj2, tuple)', SETUP, NUMBER)
    run_timeit('for _ in range(10000): not obj2 and isinstance(obj2, (list, tuple))', SETUP, NUMBER)
    run_timeit('for _ in range(10000): is_empty_sequence(obj2)', SETUP, NUMBER)

    print()

    run_timeit('tuple(x for x in range(10000))', SETUP, NUMBER)
    run_timeit('tuple(range(10000))', SETUP, NUMBER)
    run_timeit('list(x for x in range(10000))', SETUP, NUMBER)
    run_timeit('list(range(10000))', SETUP, NUMBER)
    run_timeit('[x for x in range(10000)]', SETUP, NUMBER)
    run_timeit('tuple([x for x in range(10000)])', SETUP, NUMBER)
    run_timeit('tuple((x for x in range(10000)))', SETUP, NUMBER)

    run_timeit('tuple(fg())', SETUP, NUMBER)
    run_timeit('list(fg())', SETUP, NUMBER)
    run_timeit('[x for x in fg()]', SETUP, NUMBER)
    run_timeit('tuple([x for x in fg()])', SETUP, NUMBER)
    run_timeit('tuple((x for x in fg()))', SETUP, NUMBER)
