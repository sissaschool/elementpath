#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import re
from abc import abstractmethod
from .atomic_types import AtomicTypeABCMeta, AnyAtomicType


class Notation(metaclass=AtomicTypeABCMeta):
    name = 'NOTATION'
    pattern = re.compile(
        r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
        r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
    )

    @abstractmethod
    def __new__(cls, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        if any(cls.pattern.match(x) for x in value.split()):
            raise cls.invalid_value(value)


class QName(AnyAtomicType):
    """
    XPath compliant QName, bound with a prefix and a namespace.

    :param uri: the bound namespace URI, must be a not empty \
    URI if a prefixed name is provided for the 2nd argument.
    :param qname: the prefixed name or a local name.
    """
    name = 'QName'
    pattern = re.compile(
        r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
        r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
    )

    def __init__(self, uri, qname):
        if uri is None:
            self.namespace = ''
        elif isinstance(uri, str):
            self.namespace = uri
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
    def expanded_name(self):
        if not self.namespace:
            return self.local_name
        return '{%s}%s' % (self.namespace, self.local_name)

    def __repr__(self):
        if not self.namespace:
            return '%s(%r)' % (self.__class__.__name__, self.qname)
        return '%s(%r, namespace=%r)' % (self.__class__.__name__, self.qname, self.namespace)

    def __str__(self):
        return self.qname

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare {!r} to {!r}".format(type(self), type(other)))
        return self.namespace == other.namespace and self.local_name == other.local_name
