#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

import eopsin

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="eopsin-lang",
    version=eopsin.__version__,
    description="A simple pythonic programming language for Smart Contracts on Cardano ",
    author=eopsin.__author__,
    author_email=eopsin.__author_email__,
    url=eopsin.__url__,
    py_modules=["eopsin"],
    packages=find_packages(),
    install_requires=["pluthon", "uplc"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=eopsin.__license__,
    classifiers=[
        "Development Status :: 3 - Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Compilers",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="python cardano smart contract blockchain verification haskell",
    python_requires=">=3",
)