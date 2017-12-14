#!/usr/bin/python2
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
    copyright=__copyright__,
    license=__license__,
    author=__author__,
    description='smith build tool',
    long_description='''smith is a Python-based framework for building, testing
    and maintaining WSI (Writing Systems Implementation) components such as
    fonts and keyboards. ''',
    py_modules=['smith'],
    packages=["waflib", "waflib.Tools", "waflib.extras", "smithlib"],
    include_package_data=True,
    package_data={
        'smithlib': [
            'smithlib/*.txt', 'smithlib/dot.*', 'smithlib/*.md',
            'smithlib/wscript', 'smithlib/*.html', 'smithlib/*.nsi'
        ]
    },
    entry_points={
        'console_scripts': [
            'smith=smith:main',
        ],
    },
    platforms=["Any"]
)
