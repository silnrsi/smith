#!/usr/bin/env python

import sys, os
from smithlib import wsiwaf
from waflib import Scripting

def main():
    Scripting.waf_entry_point(os.getcwd()) #assume smith.py runs in folder above smithlib and waflib

if __name__ == "__main__":
    sys.exit(main())
