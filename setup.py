#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from os.path import join, dirname

from setuptools import setup, find_packages

with open(join(dirname(__file__), 'pygraphql', '__init__.py'), 'r') as f:
    version = re.match(r".*__version__ = '(.*?)'", f.read(), re.S).group(1)

install_requires = [
    "GraphQL-core-next>=1.0.5,<1.1.0",
]

dev_requires = [
    "flake8>=3.7.7",
    "pytest>=5.0.0",
]


cmdclass = {}
ext_modules = []


setup(name="pygraphql",
      version=version,
      description="Pythonic implementation of GraphQL",
      keywords="python graphql",
      author="Tzu-hsing Gwo",
      author_email="zi-xing.guo@ubisoft.com",
      packages=find_packages(exclude=["tests", "test.*", "examples", "examples.*"]),
      url="https://pygraphql.readthedocs.io/",
      license="MIT",
      install_requires=install_requires,
      tests_require=dev_requires,
      python_requires='>=3.4',
      extras_require={
          "dev": dev_requires
      },
      classifiers=[
          "Topic :: Software Development",
          "Development Status :: 1 - Planning",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: Implementation :: CPython",
          "Programming Language :: Python :: Implementation :: PyPy",
      ])
