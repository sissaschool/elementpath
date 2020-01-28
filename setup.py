# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from setuptools import setup

with open("README.rst") as readme:
    long_description = readme.read()

setup(
    name='elementpath',
    version='1.4.1',
    packages=['elementpath'],
    author='Davide Brunato',
    author_email='brunato@sissa.it',
    url='https://github.com/sissaschool/elementpath',
    keywords=['XPath', 'XPath2', 'Pratt-parser', 'ElementTree', 'lxml'],
    license='MIT',
    description='XPath 1.0/2.0 parsers and selectors for ElementTree and lxml',
    long_description=long_description,
    extra_require={
        'dev': ['tox', 'coverage', 'lxml', 'xmlschema~=1.1.0', 'Sphinx']
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries'
    ]
)
