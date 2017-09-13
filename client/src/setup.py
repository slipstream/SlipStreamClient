#!/usr/bin/env python

import os
from distutils.core import setup


def _fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return _fullsplit(head, [tail] + result)


def get_packages(basepkg_name, root_dir=''):
    # Compile the list of packages available, because distutils doesn't have
    # an easy way to do this.
    packages = []
    root_dir = os.path.join(os.path.dirname(__file__), root_dir)
    cwd = os.getcwd()
    if root_dir != '':
        os.chdir(root_dir)

    for dirpath, dirnames, filenames in os.walk(basepkg_name):
        # Ignore dirnames that start with '.'
        for i, dirname in enumerate(dirnames):
            if dirname.startswith('.'):
                del dirnames[i]
        if '__init__.py' in filenames:
            packages.append('.'.join(_fullsplit(dirpath)))

    os.chdir(cwd)
    return packages

NAME = 'slipstream-client'
VERSION = '${project.version}'
DESCRIPTION = 'SlipStream client'
LONG_DESCRIPTION = 'SlipStream client: API and CLI'
AUTHOR = 'SixSq Sarl, (sixsq.com)'
AUTHOR_EMAIL = 'info@sixsq.com'
LICENSE = 'Apache License, Version 2.0'
PLATFORMS = 'Any'
URL = 'http://sixsq.com'
# Cheese shop (PyPI)
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: Unix",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Software Development :: Libraries :: Python Modules"
]

root_dir = 'main/python'
basepkg_name = 'slipstream'
packages = get_packages(basepkg_name, root_dir)

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    platforms=PLATFORMS,
    url=URL,
    classifiers=CLASSIFIERS,
    packages=packages,
    package_dir={'slipstream': 'main/python/slipstream'},
    requires=['httplib2']
)
