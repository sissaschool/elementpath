#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import lxml.etree
import xml.etree.ElementTree as ElementTree

from elementpath import *


class SelectorTest(unittest.TestCase):

    def test_issue_001(self):
        selector = Selector("//FullPath[ends-with(., 'Temp')]")
        self.assertListEqual(selector.select(ElementTree.XML('<A/>')), [])
        self.assertListEqual(selector.select(ElementTree.XML('<FullPath/>')), [])
        root = ElementTree.XML('<FullPath>High Temp</FullPath>')
        self.assertListEqual(selector.select(root), [root])


if __name__ == '__main__':
    unittest.main()
