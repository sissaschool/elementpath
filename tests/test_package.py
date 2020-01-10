#!/usr/bin/env python
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
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
import re


class PackageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.package_dir = os.path.dirname(cls.test_dir)
        cls.source_dir = os.path.join(cls.package_dir, 'elementpath/')
        cls.missing_debug = re.compile(r"(\bimport\s+pdb\b|\bpdb\s*\.\s*set_trace\(\s*\)|\bprint\s*\()")
        cls.get_version = re.compile(r"(?:\bversion|__version__)(?:\s*=\s*)(\'[^\']*\'|\"[^\"]*\")")

    def test_missing_debug_statements(self):
        message = "\nFound a debug missing statement at line %d of file %r: %r"
        filename = None
        for line in fileinput.input(glob.glob(os.path.join(self.source_dir, '*.py'))):
            if fileinput.isfirstline():
                filename = os.path.basename(fileinput.filename())
            lineno = fileinput.filelineno()

            match = self.missing_debug.search(line)
            self.assertIsNone(match, message % (lineno, filename, match.group(0) if match else None))

    def test_version_matching(self):
        message = "\nFound a different version at line %d of file %r: %r (maybe %r)."
        files = [
            os.path.join(self.source_dir, '__init__.py'),
            os.path.join(self.package_dir, 'setup.py'),
        ]
        version = filename = None
        for line in fileinput.input(files):
            if fileinput.isfirstline():
                filename = fileinput.filename()
            lineno = fileinput.filelineno()

            match = self.get_version.search(line)
            if match is not None:
                if version is None:
                    version = match.group(1).strip('\'\"')
                else:
                    self.assertTrue(
                        version == match.group(1).strip('\'\"'),
                        message % (lineno, filename, match.group(1).strip('\'\"'), version)
                    )


if __name__ == '__main__':
    unittest.main()
