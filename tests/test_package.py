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
import platform


class PackageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.package_dir = os.path.dirname(cls.test_dir)
        cls.source_dir = os.path.join(cls.package_dir, 'elementpath/')
        cls.missing_debug = re.compile(
            r"(\bimport\s+pdb\b|\bpdb\s*\.\s*set_trace\(\s*\)|\bprint\s*\(|\bbreakpoint\s*\()"
        )
        cls.get_version = re.compile(
            r"(?:\bversion|__version__)(?:\s*=\s*)(\'[^\']*\'|\"[^\"]*\")"
        )
        cls.get_python_requires = re.compile(
            r"(?:\brequires-python\s*=\s*)(\'[^\']*\'|\"[^\"]*\")"
        )
        cls.get_classifier_version = re.compile(
            r"(?:'Programming\s+Language\s+::\s+Python\s+::\s+)(3\.\d+)(?:\s*')"
        )

    @unittest.skipIf(platform.system() == 'Windows', 'Skip on Windows platform')
    def test_missing_debug_statements(self):
        message = "\nFound a debug missing statement at line %d of file %r: %r"
        filename = None
        source_files = glob.glob(os.path.join(self.source_dir, '*.py')) + \
            glob.glob(os.path.join(self.source_dir, '*/*.py'))

        for line in fileinput.input(source_files):
            if fileinput.isfirstline():
                filename = os.path.basename(fileinput.filename())
                if filename == 'generate_categories.py':
                    fileinput.nextfile()
                    continue

            lineno = fileinput.filelineno()

            match = self.missing_debug.search(line)
            self.assertIsNone(
                match, message % (lineno, filename, match.group(0) if match else None)
            )

    def test_version_matching(self):
        message = "\nFound a different version at line %d of file %r: %r (maybe %r)."
        files = [
            os.path.join(self.source_dir, '__init__.py'),
            os.path.join(self.package_dir, 'pyproject.toml'),
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

    def test_python_requirement(self):
        files = [
            os.path.join(self.package_dir, 'pyproject.toml'),
            os.path.join(self.package_dir, 'pyproject.toml'),
        ]

        min_version = None

        for line in fileinput.input(files):
            if min_version is None:
                match = self.get_python_requires.search(line)
                if match is not None:
                    min_version = match.group(1).strip('\'\"')
                    self.assertTrue(
                        min_version.startswith('>=3.') and min_version[4:].isdigit(),
                        msg="Wrong python_requires directive in pyproject.toml: %s" % min_version
                    )
                    min_version = min_version[2:]
            else:
                match = self.get_classifier_version.search(line)
                if match is not None:
                    python_version = match.group(1)
                    self.assertEqual(python_version[:2], min_version[:2])
                    self.assertGreaterEqual(int(python_version[2:]), int(min_version[2:]))

        self.assertIsNotNone(min_version, msg="Missing python_requires in pyproject.toml")


if __name__ == '__main__':
    unittest.main()
