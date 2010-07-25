#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

from waflib import TaskGen, Task, Utils
from waflib.Tools import ccroot
from waflib.Tools.ccroot import link_task, stlink_task

@TaskGen.extension('.c')
def c_hook(self, node):
	return self.create_compiled_task('c', node)

class c(Task.Task):
	color   = 'GREEN'
	run_str = '${CC} ${CCFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	vars    = ['CCDEPS']
	ext_in  = ['.h']
	scan    = ccroot.scan

Task.classes['cc'] = cc = c # compat, remove in waf 1.7

class cprogram(link_task):
	run_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB} ${LINKFLAGS}'
	ext_out = ['.bin']
	inst_to = '${BINDIR}'
	chmod   = Utils.O755

class cshlib(cprogram):
	inst_to = '${LIBDIR}'

class cstlib(stlink_task):
	pass

