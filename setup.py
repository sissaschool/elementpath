# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
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
    version='2.3.1',
    packages=find_packages(include=['elementpath', 'elementpath.*']),
    include_package_data=True,
    author='Davide Brunato',
    author_email='brunato@sissa.it',
    url='https://github.com/sissaschool/elementpath',
    keywords=['XPath', 'XPath2', 'Pratt-parser', 'ElementTree', 'lxml'],
    license='MIT',
    license_file='LICENSE',
    description='XPath 1.0/2.0 parsers and selectors for ElementTree and lxml',
    long_description=long_description,
    python_requires='>=3.6',
    extras_require={
        'dev': ['tox', 'coverage', 'lxml', 'xmlschema>=1.2.3',
                'Sphinx', 'memory-profiler', 'flake8', 'mypy']
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing :: Markup :: XML',
    ]
)
