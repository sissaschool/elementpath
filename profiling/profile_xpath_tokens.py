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

from elementpath import XPath1Parser
from elementpath.xpath_tokens import ValueToken


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def xpath_token_objects():
    true_token = XPath1Parser.symbol_table['true']
    return [true_token(parser) for _ in range(10000)]


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of XPathToken class          ***")
    print("***" + ' ' * 56 + "***")
    print("*** Note: save ~34% of memory with __slots__ (from v2.2.3) ***")
    print('*' * 62)
    print()

    parser = XPath1Parser()
    xpath_token_objects()

    t1 = parser.parse('18 - 9 + 10')
    t2 = parser.parse('true()')
    t3 = parser.parse('contains("foobar", "bar")')

    NUMBER = 30000

    print("*** Profile evaluation ***\n")

    run_timeit('t1.evaluate()  # 19 ', 'from __main__ import t1', NUMBER)
    run_timeit('t2.evaluate()  # True ', 'from __main__ import t2', NUMBER)
    run_timeit('t3.evaluate()  # True ', 'from __main__ import t3', NUMBER)

    print()
    print("*** Profile MutableSequence operations ***\n")

    tk = ValueToken(parser, 1)
    SETUP = 'from __main__ import tk'

    run_timeit('tk.extend((1, 2, 3))', SETUP, NUMBER)
    run_timeit('tk._items.extend((1, 2, 3))', SETUP, NUMBER)

    print()

    run_timeit('tk[:] = (1, 2, 3)', SETUP, NUMBER)
    run_timeit('tk._items[:] = (1, 2, 3)', SETUP, NUMBER)

    print()

    run_timeit('tk.append(1); tk.append(2); tk.append(3)', SETUP, NUMBER)
    run_timeit('tk._items.append(1); tk._items.append(2); tk._items.append(3)', SETUP, NUMBER)

    print()

    run_timeit('tk.append(1)', SETUP, NUMBER)
    run_timeit('tk._items.append(1)', SETUP, NUMBER)

    print()

    run_timeit('tk.append(1); tk[0]', SETUP, NUMBER)
    run_timeit('tk._items.append(1); tk._items[0]', SETUP, NUMBER)
