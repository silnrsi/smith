#!/usr/bin/env python

import sys, os

from smithlib import wsiwaf
from waflib import Scripting, Context

#assumes smith.py runs in folder above waflib
waf_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

def main():
    Scripting.waf_entry_point(os.getcwd(), Context.WAFVERSION, waf_dir)

if __name__ == "__main__":
    sys.exit(main())
