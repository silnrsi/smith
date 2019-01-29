#!/usr/bin/python3
''' generic runner '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011-2018 SIL International (http://www.sil.org)'
__author__ = 'Alan Ward, Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'

import sys
import os

from smithlib import wsiwaf
from waflib import Scripting, Context

# assumes smith.py runs in folder above waflib
# this fails if the script is relocated somewhere else by installation
# or if it is executed by launcher (since the launcher path will be found)
# but that likely doesn't matter since smith wscripts don't usually
# have items in them requiring wafdir be set correctly
# waf_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

waflib_dir = os.path.dirname(os.path.abspath(Scripting.__file__)).split(os.sep)
waf_dir = os.sep.join(waflib_dir[:-1])


def main():
    Scripting.waf_entry_point(os.getcwd(), Context.WAFVERSION, waf_dir)


if __name__ == "__main__":
    sys.exit(main())
