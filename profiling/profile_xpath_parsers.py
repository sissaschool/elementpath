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

from elementpath import XPath1Parser, XPath2Parser
from elementpath.xpath30 import XPath30Parser


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def xpath1_parser_objects():
    return [XPath1Parser() for _ in range(10000)]


@profile
def xpath2_parser_objects():
    return [XPath2Parser() for _ in range(10000)]


@profile
def xpath30_parser_objects():
    return [XPath30Parser() for _ in range(10000)]


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of XPathParser1/2/3 classes  ***")
    print("***" + ' ' * 56 + "***")
    print('*' * 62)
    print()

    xpath1_parser_objects()
    xpath2_parser_objects()
    xpath30_parser_objects()

    NUMBER = 10000

    SETUP = 'from __main__ import XPath1Parser'

    run_timeit("XPath1Parser().parse('18 - 9 + 10')", SETUP, NUMBER)
    run_timeit("XPath1Parser().parse('true()')", SETUP, NUMBER)
    run_timeit("XPath1Parser().parse('contains(\"foobar\", \"bar\")')", SETUP, NUMBER)
    run_timeit("XPath1Parser().parse('/A/B/C/D')", SETUP, NUMBER)

    print()
    SETUP = 'from __main__ import XPath2Parser'

    run_timeit("XPath2Parser().parse('18 - 9 + 10')", SETUP, NUMBER)
    run_timeit("XPath2Parser().parse('true()')", SETUP, NUMBER)
    run_timeit("XPath2Parser().parse('contains(\"foobar\", \"bar\")')", SETUP, NUMBER)
    run_timeit("XPath2Parser().parse('/A/B/C/D')", SETUP, NUMBER)

    print()
    SETUP = 'from __main__ import XPath30Parser'

    run_timeit("XPath30Parser().parse('18 - 9 + 10')", SETUP, NUMBER)
    run_timeit("XPath30Parser().parse('true()')", SETUP, NUMBER)
    run_timeit("XPath30Parser().parse('contains(\"foobar\", \"bar\")')", SETUP, NUMBER)
    run_timeit("XPath30Parser().parse('/A/B/C/D')", SETUP, NUMBER)

    print()
