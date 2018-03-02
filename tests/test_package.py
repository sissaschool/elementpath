#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import glob
import fileinput
import os


class PackageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(__file__)
        cls.source_dir = os.path.join(cls.test_dir, '../elementpath/')
        cls.missing_debug_regex = r"(\bimport\s+pdb\b|\bpdb\s*\.\s*set\_trace\(\s*\)|\bprint\s*\()"

    def test_missing_debug_statements(self):
        message = "\nFound a debug missing statement at line %d or file %r."
        filename = None
        for line in fileinput.input(glob.glob(self.source_dir + '*.py')):
            if fileinput.isfirstline():
                filename = fileinput.filename()
            lineno = fileinput.lineno()

            # noinspection PyCompatibility
            self.assertNotRegex(line, self.missing_debug_regex, message % (lineno, filename))


if __name__ == '__main__':
    unittest.main()
