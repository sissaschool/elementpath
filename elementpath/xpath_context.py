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
import datetime

from .exceptions import ElementPathTypeError
from .xpath_nodes import AttributeNode, TypedAttribute, TypedElement, is_etree_element, \
    is_element_node, is_document_node, is_attribute_node


class XPathContext(object):
    """
    The XPath dynamic context. The static context is provided by the parser.

    Usually the dynamic context instances are created providing only the root element.
    Variables argument is needed if the XPath expression refers to predefined variables.
    The other optional arguments are needed only if a specific position on the context is
    required, but have to be used with the knowledge of what is their meaning.

    :param root: the root of the XML document, can be a ElementTree instance or an Element.
    :param item: the context item. A `None` value means that the context is positioned on \
    the document node.
    :param position: the current position of the node within the input sequence.
    :param size: the number of items in the input sequence.
    :param axis: the active axis. Used to choose when apply the default axis ('child' axis).
    :param variables: dictionary of context variables that maps a QName to a value.
    :param current_dt: current dateTime of the implementation, including explicit timezone.
    :param timezone: implicit timezone to be used when a date, time, or dateTime value does \
    not have a timezone.
    """
    def __init__(self, root, item=None, position=0, size=1, axis=None, variables=None,
                 current_dt=None, timezone=None):
        if not is_element_node(root) and not is_document_node(root):
            raise ElementPathTypeError(
                "invalid argument root={!r}, an Element is required.".format(root)
            )
        self._root = root
        if item is not None:
            self.item = item
        elif is_element_node(root):
            self.item = root
        else:
            self.item = None

        self.position = position
        self.size = size
        self.axis = axis
        self.variables = {} if variables is None else dict(variables)
        self.current_dt = current_dt or datetime.datetime.now()
        self.timezone = timezone
        self._parent_map = None

    def __repr__(self):
        return '%s(root=%r, item=%r, position=%r, size=%r, axis=%r)' % (
            self.__class__.__name__, self._root, self.item, self.position, self.size, self.axis
        )

    def copy(self, clear_axis=True):
        obj = type(self)(
            root=self._root,
            item=self.item,
            position=self.position,
            size=self.size,
            axis=None if clear_axis else self.axis,
            variables=self.variables.copy(),
            current_dt=self.current_dt,
            timezone=self.timezone,
        )
        obj._parent_map = self._parent_map
        return obj

    @property
    def root(self):
        return self._root

    @property
    def parent_map(self):
        # TODO: try to implement a dynamic parent map to save memory ...
        if self._parent_map is None:
            self._parent_map = {child: elem for elem in self._root.iter() for child in elem}
        return self._parent_map

    def is_principal_node_kind(self):
        if self.axis == 'attribute':
            return is_attribute_node(self.item)
        else:
            return is_element_node(self.item)

    # Context item iterators
    def iter_self(self):
        status = self.item, self.size, self.position, self.axis
        self.axis = 'self'
        yield self.item
        self.item, self.size, self.position, self.axis = status

    def iter_attributes(self):
        if not is_element_node(self.item):
            return

        status = self.item, self.size, self.position, self.axis
        self.axis = 'attribute'

        if isinstance(self.item, TypedElement):
            self.item = self.item.elem

        for item in self.item.attrib.items():
            self.item = AttributeNode(*item)
            yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_children_or_self(self, item=None, child_axis=False):
        status = self.item, self.size, self.position, self.axis
        if not child_axis and self.axis is not None:
            yield self.item
            self.item, self.size, self.position, self.axis = status
            return

        self.axis = 'child'
        if item is not None:
            self.item = item[0] if isinstance(item, TypedElement) else item
        elif isinstance(self.item, TypedElement):
            self.item = self.item[0]

        if self.item is None:
            self.size, self.position = 1, 0
            self.item = self._root.getroot() if is_document_node(self._root) else self._root
            yield self.item
        elif is_etree_element(self.item):
            elem = self.item
            if elem.text is not None:
                self.item = elem.text
                yield self.item
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_preceding(self):
        status = self.item, self.size, self.position, self.axis

        item = e = self.item[0] if isinstance(self.item, TypedElement) else self.item
        if not is_etree_element(item):
            return
        self.axis = 'preceding'

        ancestors = []
        while True:
            try:
                parent = self.parent_map[e]
            except KeyError:
                break
            else:
                ancestors.append(parent)
                e = parent

        for e in self.root.iter():
            if e is item:
                break
            elif e not in ancestors:
                self.item = e
                yield e

        self.item, self.size, self.position, self.axis = status

    def iter_parent(self, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        try:
            if isinstance(self.item, TypedElement):
                self.item = self.parent_map[self.item[0]]
            else:
                self.item = self.parent_map[self.item]
        except KeyError:
            pass
        else:
            yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_descendants(self, item=None, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if item is not None:
            self.item = item[0] if isinstance(item, TypedElement) else item
        elif isinstance(self.item, TypedElement):
            self.item = self.item[0]

        if self.item is None:
            self.size, self.position = 1, 0
            yield self._root
            self.item = self._root.getroot() if is_document_node(self._root) else self._root
        elif not is_element_node(self.item):
            return

        for descendant in self._iter_descendants():
            yield descendant

        self.item, self.size, self.position, self.axis = status

    def _iter_descendants(self):
        elem = self.item
        yield elem
        if elem.text is not None:
            self.item = elem.text
            yield self.item
        if len(elem):
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                for item in self._iter_descendants():
                    yield item

    def iter_ancestors(self, item=None, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if item is not None:
            self.item = item[0] if isinstance(item, TypedElement) else item
        elif isinstance(self.item, TypedElement):
            self.item = self.item[0]

        while True:
            try:
                parent = self.parent_map[self.item]
            except KeyError:
                break
            else:
                self.item = parent
                yield parent

        self.item, self.size, self.position, self.axis = status

    def iter(self, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if self.item is None:
            self.size, self.position = 1, 0
            yield self._root
            self.item = self._root.getroot() if is_document_node(self._root) else self._root
        elif isinstance(self.item, TypedElement):
            self.item = self.item[0]
        elif not is_etree_element(self.item):
            return

        for item in self._iter_context():
            yield item

        self.item, self.size, self.position, self.axis = status

    def iter_results(self, results, is_root=False):
        """Iterates results in document order."""
        status = self.item, self.size, self.position
        self.item = self.root

        for item in self._iter_context():
            if item in results:
                if is_attribute_node(item):
                    yield item[1] if is_root else item
                else:
                    yield item
            elif isinstance(item, AttributeNode):
                # Match XSD decoded attributes
                for attr in filter(lambda x: isinstance(x, TypedAttribute), results):
                    if attr[0] == item:
                        yield attr[1] if is_root else attr
            elif is_etree_element(item):
                # Match XSD decoded elements
                for elem in filter(lambda x: isinstance(x, TypedElement), results):
                    if elem[0] is item:
                        yield elem[1] if is_root else elem

        self.item, self.size, self.position = status

    def _iter_context(self):
        elem = self.item
        yield elem
        if elem.text is not None:
            self.item = elem.text
            yield self.item

        for self.item in map(lambda x: AttributeNode(*x), elem.attrib.items()):
            yield self.item

        if len(elem):
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                for item in self._iter_context():
                    yield item


class XPathSchemaContext(XPathContext):
    """
    The XPath dynamic context base class for schema bounded parsers. Use this class
    as dynamic context for schema instances in order to perform a schema-based type
    checking during the static analysis phase. Don't use this as dynamic context on
    XML instances.
    """
