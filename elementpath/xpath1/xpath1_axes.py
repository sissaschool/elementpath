#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from ..xpath_nodes import NamespaceNode, is_element_node
from .xpath1_functions import XPath1Parser

method = XPath1Parser.method
axis = XPath1Parser.axis


@method('@', bp=80)
def nud(self):
    self.parser.expected_name(
        '*', '(name)', ':', '{', 'Q{', message="invalid attribute specification")
    self[:] = self.parser.expression(rbp=80),
    return self


@method('@')
@method(axis('attribute'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    for _ in context.iter_attributes():
        yield from self[0].select(context)


@method(axis('namespace'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    elif is_element_node(context.item):
        elem = context.item
        namespaces = self.parser.namespaces

        for prefix_, uri in namespaces.items():
            context.item = NamespaceNode(prefix_, uri)
            yield context.item

        if hasattr(elem, 'nsmap'):
            # Add element's namespaces for lxml (and use None for default namespace)
            # noinspection PyUnresolvedReferences
            for prefix_, uri in elem.nsmap.items():
                if prefix_ not in namespaces:
                    context.item = NamespaceNode(prefix_, uri, elem)
                    yield context.item


@method(axis('self'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_self():
            yield from self[0].select(context)


@method(axis('child'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_children_or_self():
            yield from self[0].select(context)


@method(axis('parent', reverse_axis=True))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_parent():
            yield from self[0].select(context)


@method(axis('following-sibling'))
@method(axis('preceding-sibling', reverse_axis=True))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_siblings(axis=self.symbol):
            yield from self[0].select(context)


@method(axis('ancestor', reverse_axis=True))
@method(axis('ancestor-or-self', reverse_axis=True))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_ancestors(axis=self.symbol):
            yield from self[0].select(context)


@method(axis('descendant'))
@method(axis('descendant-or-self'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_descendants(axis=self.symbol):
            yield from self[0].select(context)


@method(axis('following'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        for _ in context.iter_followings():
            yield from self[0].select(context)


@method(axis('preceding', reverse_axis=True))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    elif is_element_node(context.item):
        for _ in context.iter_preceding():
            yield from self[0].select(context)


register = XPath1Parser.register('(end)')
