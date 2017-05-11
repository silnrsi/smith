#!/usr/bin/env python
'Setuptools installation file'
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2017 SIL International (http://www.sil.org)'
__version__ = '0.3.2'

try:
    from setuptools import setup
except ImportError :
    print "smith packaging & installation requires setuptools"
    sys.exit(1)

setup(
    name = 'smith',
    version = __version__, 
    url = __url__, 
    description = 'smith build tool',
    long_description = 'a build tool for fonts',
    py_modules = ['smith'],
    packages = ["waflib", "smithlib"], 
    entry_points = {
        'console_scripts' : [
            'smith=smith:main',
        ],
    }
)
