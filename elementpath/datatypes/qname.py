#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from abc import abstractmethod
from .atomic_types import AtomicTypeMeta
from .helpers import QNAME_PATTERN


class AbstractQName(metaclass=AtomicTypeMeta):
    """
    XPath compliant QName, bound with a prefix and a namespace.

    :param uri: the bound namespace URI, must be a not empty \
    URI if a prefixed name is provided for the 2nd argument.
    :param qname: the prefixed name or a local name.
    """
    pattern = QNAME_PATTERN

    @abstractmethod
    def __init__(self, uri, qname):
        if uri is None:
            self.uri = ''
        elif isinstance(uri, str):
            self.uri = uri
        else:
            raise TypeError('the 1st argument has an invalid type %r' % type(uri))

        if not isinstance(qname, str):
            raise TypeError('the 2nd argument has an invalid type %r' % type(qname))
        self.qname = qname.strip()

        match = self.pattern.match(self.qname)
        if match is None:
            raise ValueError('invalid value {!r} for an xs:QName'.format(self.qname))

        self.prefix = match.groupdict()['prefix']
        self.local_name = match.groupdict()['local']
        if not uri and self.prefix:
            msg = '{!r}: cannot associate a non-empty prefix with no namespace'
            raise ValueError(msg.format(self))

    @property
    def namespace(self):
        return self.uri

    @property
    def expanded_name(self):
        return '{%s}%s' % (self.uri, self.local_name) if self.uri else self.local_name

    def __repr__(self):
        return '%s(uri=%r, qname=%r)' % (self.__class__.__name__, self.uri, self.qname)

    def __str__(self):
        return self.qname

    def __hash__(self):
        return hash((self.uri, self.local_name))

    def __eq__(self, other):
        if not isinstance(other, AbstractQName):
            raise TypeError("cannot compare {!r} to {!r}".format(type(self), type(other)))
        return self.uri == other.uri and self.local_name == other.local_name


class QName(AbstractQName):
    """
    XPath compliant QName, bound with a prefix and a namespace.

    :param uri: the bound namespace URI, must be a not empty \
    URI if a prefixed name is provided for the 2nd argument.
    :param qname: the prefixed name or a local name.
    """
    name = 'QName'

    def __init__(self, uri, qname):
        super().__init__(uri, qname)


class Notation(AbstractQName):
    name = 'NOTATION'

    @abstractmethod
    def __init__(self, uri, qname):
        super().__init__(uri, qname)
