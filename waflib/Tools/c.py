#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

from waflib import TaskGen, Task, Utils
from waflib.Tools import c_preproc
from waflib.Tools.c_use import link, stlink

@TaskGen.extension('.c')
def c_hook(self, node):
	"Map c files to the c task"
	return self.create_compiled_task('c', node)

class c(Task.Task):
	"Task for compiling c files into object files"
	color   = 'GREEN'
	run_str = '${CC} ${CCFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	vars    = ['CCDEPS'] # unused variable to depend on, just in case
	ext_in  = ['.h'] # set the build order easily by using ext_out=['.h']
	scan    = c_preproc.scan

Task.classes['cc'] = cc = c # compat, remove in waf 1.7

class cprogram(link):
	"Link object files into a c program"
	run_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB} ${LINKFLAGS}'
	ext_out = ['.bin']
	inst_to = '${BINDIR}'
	chmod   = Utils.O755

class cshlib(cprogram):
	"Link object files into a c shared library"
	inst_to = '${LIBDIR}'

class cstlib(stlink):
	"Link object files into a c static library"
	pass # do not remove

