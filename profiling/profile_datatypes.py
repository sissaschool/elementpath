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

from elementpath import XPath1Parser
from elementpath.datatypes import Language, UntypedAtomic

def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of XPathToken class          ***")
    print("***" + ' ' * 56 + "***")
    print("*** Note: save ~34% of memory with __slots__ (from v2.2.3) ***")
    print('*' * 62)
    print()

    NUMBER = 300000

    print("*** Profile evaluation ***\n")

    run_timeit('UntypedAtomic("foo.bar")', 'from __main__ import UntypedAtomic', NUMBER)

    print()
