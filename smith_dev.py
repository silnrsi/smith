#!/usr/bin/python2

# Launch smith from its source repo.
# The main use is for smith development.
#
# The usual smith script unpacks its tarball and
# imports code from the unpack location.
# This script should run exactly as smith is run.
# E.g. From a folder with a wscript, run:
#  "python <smith repo path>/smith_dev.py configure"
# Launching tested under Linux and Win10

smith_ver = '1.6.8'  # !! MUST match WAFVERSION value in waflib/Context.py !!

# smith_repo is location of waf modules (-> Context.waf_dir)
# cwd is used to find wscript (-> Context.launch_dir)
import sys, os
smith_repo_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
cwd = os.getcwd()
# print("cwd = %s\nsmith_repo = %s\n" % (cwd, smith_repo))

# smithlib and waflib should be under the folder where this script is launched
# smithlib/__init.py__ is not required by the usual smith script
# because smithlib content is copied to waflib/extras
try:
    from smithlib import wsiwaf  # works with local smithlib/__init.py__ file
except:
    # add smithlib to the Python path (though it's not a package)
    sys.path.insert(1, os.path.join(smith_repo_dir, 'smithlib'))
    try:
        import wsiwaf
    except:
        print("smithlib is required on the Python path")
        sys.exit(0)
from waflib import Scripting

Scripting.waf_entry_point(cwd, smith_ver, smith_repo_dir)
