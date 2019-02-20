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

from .exceptions import ElementPathTypeError, ElementPathValueError
from .xpath_helpers import AttributeNode, is_etree_element, is_element_node, is_document_node, is_attribute_node


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
            raise ElementPathTypeError("argument 'root' must be an Element: %r" % root)
        self.root = root
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
            self.__class__.__name__, self.root, self.item, self.position, self.size, self.axis
        )

    def copy(self, clear_axis=True):
        obj = type(self)(
            root=self.root,
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
    def parent_map(self):
        if self._parent_map is None:
            self._parent_map = {child: elem for elem in self.root.iter() for child in elem}
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
            self.item = item

        if self.item is None:
            self.size, self.position = 1, 0
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
            yield self.item
        elif is_element_node(self.item):
            elem = self.item
            if elem.text is not None:
                self.item = elem.text
                yield self.item
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_parent(self, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis
        try:
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
            self.item = item

        if self.item is None:
            self.size, self.position = 1, 0
            yield self.root
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
        elif not is_etree_element(self.item):
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
            self.item = item

        if not is_etree_element(self.item):
            return
        elem = self.item
        parent_map = self.parent_map
        while True:
            try:
                parent = parent_map[self.item]
            except KeyError:
                break
            else:
                if parent is elem:
                    raise ElementPathValueError("not an Element tree, circularity found for %r." % elem)
                self.item = parent
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter(self, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if self.item is None:
            self.size, self.position = 1, 0
            yield self.root
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
        elif not is_etree_element(self.item):
            return

        for item in self._iter_context():
            yield item

        self.item, self.size, self.position, self.axis = status

    def _iter_context(self):
        elem = self.item
        yield elem
        if elem.text is not None:
            self.item = elem.text
            yield self.item

        for item in elem.attrib.items():
            self.item = item
            yield item

        if len(elem):
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                for item in self._iter_context():
                    yield item


class XPathSchemaContext(XPathContext):
    """Schema context class used during static analysis phase for matching tokens with schema types."""
