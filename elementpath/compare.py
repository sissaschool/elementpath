#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import math
from decimal import Decimal
from functools import cmp_to_key
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, Optional, Iterable

from .protocols import ElementProtocol
from .exceptions import xpath_error
from .datatypes import UntypedAtomic, AnyURI
from .collations import UNICODE_CODEPOINT_COLLATION, CollationManager
from .xpath_nodes import XPathNode, ElementNode, AttributeNode, NamespaceNode, \
    CommentNode, ProcessingInstructionNode, DocumentNode
from .xpath_tokens import XPathToken, XPathFunction, XPathMap, XPathArray

if TYPE_CHECKING:
    from .xpath_tokens import XPathToken


def deep_equal(seq1: Iterable[Any],
               seq2: Iterable[Any],
               collation: Optional[str] = None,
               token: Optional[XPathToken] = None) -> bool:

    etree_node_types = (ElementNode, CommentNode, ProcessingInstructionNode)

    def etree_deep_equal(e1: ElementProtocol, e2: ElementProtocol) -> bool:
        if cm.ne(e1.tag, e2.tag):
            return False
        elif cm.ne((e1.text or '').strip(), (e2.text or '').strip()):
            return False
        elif cm.ne((e1.tail or '').strip(), (e2.tail or '').strip()):
            return False
        elif len(e1) != len(e2) or len(e1.attrib) != len(e2.attrib):
            return False

        items1 = {(cm.strxfrm(k), cm.strxfrm(v)) for k, v in e1.attrib.items()}
        items2 = {(cm.strxfrm(k), cm.strxfrm(v)) for k, v in e2.attrib.items()}
        if items1 != items2:
            return False
        return all(etree_deep_equal(c1, c2) for c1, c2 in zip(e1, e2))

    if collation is None:
        collation = UNICODE_CODEPOINT_COLLATION

    with CollationManager(collation, token=token) as cm:
        for value1, value2 in zip_longest(seq1, seq2):
            if isinstance(value1, XPathFunction) and \
                    not isinstance(value1, (XPathMap, XPathArray)):
                raise xpath_error('FOTY0015', token=token)
            if isinstance(value2, XPathFunction) and \
                    not isinstance(value2, (XPathMap, XPathArray)):
                raise xpath_error('FOTY0015', token=token)

            if (value1 is None) ^ (value2 is None):
                return False
            elif value1 is None:
                return True
            elif isinstance(value1, XPathNode) ^ isinstance(value2, XPathNode):
                return False
            elif isinstance(value1, XPathNode):
                assert isinstance(value2, XPathNode)
                if value1.kind != value2.kind:
                    return False
                elif isinstance(value1, etree_node_types):
                    assert isinstance(value2, etree_node_types)
                    if not etree_deep_equal(value1.elem, value2.elem):
                        return False
                elif isinstance(value1, DocumentNode):
                    assert isinstance(value2, DocumentNode)
                    if not etree_deep_equal(value1.document.getroot(), value2.document.getroot()):
                        return False
                elif cm.ne(value1.value, value2.value):
                    return False
                elif isinstance(value1, AttributeNode):
                    if cm.ne(value1.name, value2.name):
                        return False
                elif isinstance(value1, NamespaceNode):
                    assert isinstance(value2, NamespaceNode)
                    if cm.ne(value1.prefix, value2.prefix):
                        return False
            else:
                try:
                    if isinstance(value1, bool):
                        if not isinstance(value2, bool) or value1 is not value2:
                            return False

                    elif isinstance(value2, bool):
                        return False

                    elif isinstance(value1, UntypedAtomic):
                        if not isinstance(value2, UntypedAtomic) or value1 != value2:
                            return False

                    elif isinstance(value2, UntypedAtomic):
                        return False

                    elif isinstance(value1, float):
                        if math.isnan(value1):
                            if not math.isnan(value2):  # type: ignore[arg-type]
                                return False
                        elif math.isinf(value1):
                            if value1 != value2:
                                return False
                        elif isinstance(value2, Decimal):
                            if value1 != float(value2):
                                return False
                        elif not isinstance(value2, (value1.__class__, int)):
                            return False
                        elif value1 != value2:
                            return False

                    elif isinstance(value2, float):
                        if math.isnan(value2):
                            return False
                        elif math.isinf(value2):
                            if value1 != value2:
                                return False
                        elif isinstance(value1, Decimal):
                            if value2 != float(value1):
                                return False
                        elif not isinstance(value1, (value2.__class__, int)):
                            return False
                        elif value1 != value2:
                            return False

                    elif value1 != value2:
                        return False
                except TypeError:
                    return False

    return True


def deep_compare(obj1: Any,
                 obj2: Any,
                 collation: Optional[str] = None,
                 token: Optional[XPathToken] = None) -> int:

    etree_node_types = (ElementNode, CommentNode, ProcessingInstructionNode)
    result: int = 0

    def etree_deep_compare(e1: ElementProtocol, e2: ElementProtocol) -> int:
        nonlocal result
        result = cm.strcoll(e1.tag, e2.tag)
        if result:
            return result

        result = cm.strcoll((e1.text or '').strip(), (e2.text or '').strip())
        if result:
            return result

        for a1, a2 in zip_longest(e1.attrib.items(), e2.attrib.items()):
            if a1 is None:
                return 1
            elif a2 is None:
                return -1

            result = cm.strcoll(a1[0], a2[0]) or cm.strcoll(a1[1], a2[1])
            if result:
                return result

        for c1, c2 in zip_longest(e1, e2):
            if c1 is None:
                return 1
            elif c2 is None:
                return -1

            result = etree_deep_compare(c1, c2)
            if result:
                return result
        else:
            result = cm.strcoll((e1.tail or '').strip(), (e2.tail or '').strip())
            if result:
                return result

            return 0

    if collation is None:
        collation = UNICODE_CODEPOINT_COLLATION

    seq1 = obj1 if isinstance(obj1, Iterable) else (obj1,)
    seq2 = obj2 if isinstance(obj2, Iterable) else (obj2,)

    with CollationManager(collation, token=token) as cm:
        for value1, value2 in zip_longest(seq1, seq2):
            if isinstance(value1, XPathFunction) and \
                    not isinstance(value1, (XPathMap, XPathArray)):
                raise xpath_error('FOTY0015', token=token)
            if isinstance(value2, XPathFunction) and \
                    not isinstance(value2, (XPathMap, XPathArray)):
                raise xpath_error('FOTY0015', token=token)

            if (value1 is None) ^ (value2 is None):
                return 0
            elif value1 is None:
                return -1
            elif isinstance(value1, XPathNode) ^ isinstance(value2, XPathNode):
                msg = f"cannot compare {type(value1)} with {type(value2)}"
                raise xpath_error('XPTY0004', msg, token=token)
            elif isinstance(value1, XPathNode):
                assert isinstance(value2, XPathNode)
                if value1.kind != value2.kind:
                    msg = f"cannot compare {type(value1)} with {type(value2)}"
                    raise xpath_error('XPTY0004', msg, token=token)
                elif isinstance(value1, etree_node_types):
                    assert isinstance(value2, etree_node_types)
                    result = etree_deep_compare(value1.elem, value2.elem)
                    if result:
                        return result
                elif isinstance(value1, DocumentNode):
                    assert isinstance(value2, DocumentNode)
                    result = etree_deep_compare(
                        value1.document.getroot(), value2.document.getroot()
                    )
                    if result:
                        return result
                else:
                    result = cm.strcoll(value1.value, value2.value)
                    if result:
                        return result

                    if isinstance(value1, AttributeNode):
                        assert isinstance(value2, AttributeNode)
                        result = cm.strcoll(value1.name, value2.name)
                        if result:
                            return result
                    elif isinstance(value1, NamespaceNode):
                        assert isinstance(value2, NamespaceNode)
                        result = cm.strcoll(value1.prefix or '', value2.prefix or '')
                        if result:
                            return result
            else:
                try:
                    if isinstance(value1, bool):
                        if not isinstance(value2, bool):
                            return -1
                        elif value1 is not value2:
                            return -1 if value1 else 1

                    elif isinstance(value2, bool):
                        return -1

                    elif isinstance(value1, UntypedAtomic):
                        if not isinstance(value2, UntypedAtomic):
                            return -1
                        else:
                            result = cm.strcoll(value1, value2)
                            if result:
                                return result

                    elif isinstance(value2, UntypedAtomic):
                        return -1

                    elif isinstance(value1, float):
                        if math.isnan(value1):
                            if not math.isnan(value2):  # type: ignore[arg-type]
                                return -1
                        elif math.isinf(value1):
                            if value1 != value2:
                                return -1 if value1 < value2 else 1
                        elif isinstance(value2, Decimal):
                            if value1 != float(value2):
                                return -1 if value1 < float(value2) else 1
                        elif not isinstance(value2, (value1.__class__, int)):
                            return -1
                        elif value1 != value2:
                            return -1 if value1 < value2 else 1

                    elif isinstance(value2, float):
                        if math.isnan(value2):
                            return -1
                        elif math.isinf(value2):
                            if value1 != value2:
                                return -1 if value1 < value2 else 1
                        elif isinstance(value1, Decimal):
                            if value2 != float(value1):
                                return -1 if float(value1) < value2 else 1
                        elif not isinstance(value1, (value2.__class__, int)):
                            return -1
                        elif value1 != value2:
                            return -1 if value1 < value2 else 1

                    elif isinstance(value1, (str, AnyURI, UntypedAtomic)) \
                            and isinstance(value1, (str, AnyURI, UntypedAtomic)):
                        result = cm.strcoll(value1, value2)
                        if result:
                            return result
                    elif value1 != value2:
                        return -1 if value1 < value2 else 1

                except TypeError as err:
                    raise xpath_error('XPTY0004', message_or_error=err, token=token)

    return 0


deep_key_function = cmp_to_key(deep_compare)
