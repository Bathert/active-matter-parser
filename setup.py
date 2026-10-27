#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="activematter-parser",
    version="2.0.0",
    description="Pure Python parser for Active Matter local storage & JSON 2.0 raid slicer",
    author="Active Matter Community",
    packages=find_packages(),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "activematter-parser = activematter_parser.cli:main"
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3"
    ]
)
