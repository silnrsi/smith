#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Base for c++ programs and libraries"

from waflib import TaskGen, Task, Utils
from waflib.Tools import c_preproc
from waflib.Tools.ccroot import link_task, stlink_task

def cxx_hook(self, node):
	"map c++ files to the c++ task"
	return self.create_compiled_task('cxx', node)
TaskGen.extension('.cpp','.cc','.cxx','.C','.c++')(cxx_hook) # leave like this for python 2.3

if not '.c' in TaskGen.task_gen.mappings:
	TaskGen.task_gen.mappings['.c'] = TaskGen.task_gen.mappings['.cpp']

class cxx(Task.Task):
	"Compile c++ files into object files"
	color   = 'GREEN'
	run_str = '${CXX} ${CXXFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
	vars    = ['CXXDEPS'] # unused variable to depend on, just in case
	ext_in  = ['.h'] # set the build order easily by using ext_out=['.h']
	scan    = c_preproc.scan

class cxxprogram(link_task):
	"Link object files into a c++ program"
	run_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB} ${LINKFLAGS}'
	ext_out = ['.bin']
	inst_to = '${BINDIR}'
	chmod   = Utils.O755

class cxxshlib(cxxprogram):
	"Link object files into a c++ shared library"
	inst_to = '${LIBDIR}'

class cxxstlib(stlink_task):
	"Link object files into a c++ static library"
	pass # do not remove

