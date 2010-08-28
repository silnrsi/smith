#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

"cuda"

from waflib import Task
from waflib.TaskGen import extension
from waflib.Tools import ccroot, c_preproc

class cuda(Task.Task):
	run_str = '${NVCC} ${CUDAFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} -c ${SRC} -o ${TGT}'
	color   = 'GREEN'
	ext_in  = ['.c']
	scan    = c_preproc.scan
	shell   = False

@extension('.cu', '.cuda')
def c_hook(self, node):
	return self.create_compiled_task('cuda', node)

def configure(conf):
	conf.find_program('nvcc', var='NVCC')

