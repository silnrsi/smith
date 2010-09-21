#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

"cuda"

import os
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

	if not self.env.NVCC:
		self.fatal('check for nvcc first')

	d = self.root.find_node(self.env.NVCC).parent.parent

	node = d.find_node('include')
	_includes = node and node.abspath() or ''

	node = d.find_node('lib')
	_libpath = node and node.abspath() or ''

	# this should not raise any error
	self.check_cxx(header='cuda.h', lib='cuda', libpath=_libpath, includes=_includes)

	# TODO set conf.env.LIB_CUDA = ['cuda']
	# TODO set conf.env.INCLUDES_CUDA = ["path1", "path2"]
	# TODO set conf.env.LIBPATH_CUDA = ["libpath1"]

	#self.env.LIB_CUDA = ['cuda', 'cudart']
	#self.env.LIBPATH_CUDA = ['/comp/cuda/lib64']
	#self.env.RPATH_CUDA   = ['/comp/cuda/lib64']


