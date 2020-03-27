#!/usr/bin/python3
'Setuptools installation file'
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2017 SIL International (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'
__version__ = '0.3.5'

try:
    import sys
    from setuptools import setup
except ImportError:
    print("smith packaging & installation requires setuptools")
    sys.exit(1)

setup(
    name='smith',
    version=__version__,
    url=__url__,
    license=__license__,
    author=__author__,
    description='smith build tool',
    long_description='''smith is a Python-based framework for building, testing
    and maintaining WSI (Writing Systems Implementation) components such as
    fonts and keyboards. ''',
    py_modules=['smith'],
    packages=["waflib", "waflib.Tools", "waflib", "smithlib"],
    include_package_data=True,
    package_data={
        'smithlib': [
            'smithlib/*.*', 'smithlib/templates/', 'smithlib/classes/'
        ]
    },
    entry_points={
        'console_scripts': [
            'smith=smith:main',
        ],
    },
    platforms=["Any"],
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Topic :: Text Processing :: Fonts"
        ],
)
