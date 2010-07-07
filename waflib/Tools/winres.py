#!/usr/bin/env python
# encoding: utf-8
# Brant Young, 2007

"This hook is called when the class cpp/cc task generator encounters a '.rc' file: X{.rc -> [.res|.rc.o]}"

import os, sys, re
from waflib import TaskGen, Task
from waflib.TaskGen import extension

@extension('.rc')
def rc_file(self, node):
	obj_ext = '.rc.o'
	if self.env['WINRC_TGT_F'] == '/fo':
		obj_ext = '.res'
	rctask = self.create_task('winrc', node, node.change_ext(obj_ext))
	self.compiled_tasks.append(rctask)

class winrc(Task.Task):
	run_str = '${WINRC} ${_CPPDEFFLAGS} ${_CCDEFFLAGS} ${WINRCFLAGS} ${_CPPINCFLAGS} ${_CCINCFLAGS} ${WINRC_TGT_F} ${TGT} ${WINRC_SRC_F} ${SRC}'
	color   = 'BLUE'

def configure(conf):
	v = conf.env
	v['WINRC_TGT_F'] = '-o'
	v['WINRC_SRC_F'] = '-i'

	# find rc.exe
	if not conf.env.WINRC:
		if v.CC_NAME in ['gcc', 'cc', 'g++', 'c++']:
			winrc = conf.find_program('windres', var='WINRC')
		elif v.CC_NAME == 'msvc':
			winrc = conf.find_program('RC', var='WINRC')
			v['WINRC_TGT_F'] = '/fo'
			v['WINRC_SRC_F'] = ''

	if not conf.env.WINRC:
		conf.fatal('winrc was not found!')

	v['WINRCFLAGS'] = []

