# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from setuptools import setup, find_packages

with open("README.rst") as readme:
    long_description = readme.read()

setup(
    name='elementpath',
    version='4.3.0',
    packages=find_packages(include=['elementpath', 'elementpath.*']),
    package_data={
        'elementpath': ['py.typed'],
        'elementpath.validators': ['analyze-string.xsd', 'schema-for-json.xsd'],
    },
    author='Davide Brunato',
    author_email='brunato@sissa.it',
    url='https://github.com/sissaschool/elementpath',
    keywords=['XPath', 'XPath2', 'XPath3', 'XPath31', 'Pratt-parser', 'ElementTree', 'lxml'],
    license='MIT',
    license_file='LICENSE',
    description='XPath 1.0/2.0/3.0/3.1 parsers and selectors for ElementTree and lxml',
    long_description=long_description,
    python_requires='>=3.8',
    extras_require={
        'dev': ['tox', 'coverage', 'lxml', 'xmlschema>=2.0.0', 'Sphinx',
                'memory-profiler', 'memray', 'flake8', 'mypy', 'lxml-stubs']
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing :: Markup :: XML',
    ]
)
