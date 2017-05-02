#!/usr/bin/python2

# Launch smith from its source repo.
# The main use is for smith development.
#
# The usual smith script unpacks its tarball and 
# imports code from the unpack location.
# This script should run exactly as smith is run.
# E.g. From a folder with a wscript, run:
#  "python <smith repo path>/smith_dev.py configure"

smith_ver = '1.6.8' # !! MUST match WAFVERSION value in waflib/Context.py !!

#smith_repo is location of waf modules (-> Context.waf_dir)
#cwd is used to find wscript (-> Context.launch_dir)
import sys, os
smith_repo_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
cwd = os.getcwd()
#print("cwd = %s\nsmith_repo = %s\n" % (cwd, smith_repo))

#smithlib and waflib should be under the folder where this script is launched
# normally this script should be at the root of the smith repo
# both lib folders must contain an __init.py__ for the below imports to work
#  smithlib/__init.py__ is not required by the usual smith script because 
#  its content is copied to waflib/extras
# TODO: add smithlib to the Python path if __init.py__ is missing
try:
    from smithlib import wsiwaf
except:
    print("This script requires an __init.py__ file in smithlib\n")
    sys.exit(0)
from waflib import Scripting

Scripting.waf_entry_point(cwd, smith_ver, smith_repo_dir)
