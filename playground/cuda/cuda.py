#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

"cuda"

from waflib import Task
from waflib.TaskGen import extension
from waflib.Tools import ccroot, c_preproc
from waflib.Configure import conf

class cuda(Task.Task):
	run_str = '${NVCC} ${CUDAFLAGS} ${CXXFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
	color   = 'GREEN'
	ext_in  = ['.h']
	vars    = ['CCDEPS']
	scan    = c_preproc.scan
	shell   = False

@extension('.cu', '.cuda')
def c_hook(self, node):
	return self.create_compiled_task('cuda', node)

def configure(conf):
	conf.find_program('nvcc', var='NVCC')
	conf.find_cuda_dirs()

@conf
def find_cuda_dirs(self):
	"""
	find the cuda include and library folders

	use ctx.program(source='main.c', target='app', use='CUDA')
	"""
	# TODO set conf.env.LIB_CUDA = ['cuda']
	# TODO set conf.env.INCLUDES_CUDA = ["path1", "path2"]
	# TODO set conf.env.LIBPATH_CUDA = ["libpath1"]
	pass

