#
# Copyright (c), 2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Imports for subscriptable types and common type hints aliases.
"""
import sys
from typing import Optional

if sys.version_info < (3, 9):
    from typing import Dict, MutableMapping
else:
    from collections.abc import MutableMapping
    Dict = dict

NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element

__all__ = ['MutableMapping', 'Dict', 'NamespacesType', 'NsmapType']
