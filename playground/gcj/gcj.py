#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)

"""
Native compilation using gcj for the moment
"""

import os, re
from waflib.Configure import conf
from waflib import TaskGen, Task, Utils
from waflib.TaskGen import feature, before
from waflib.Tools import ccroot

def configure(conf):
	conf.find_program('gcj', var='GCJ')
	conf.env.GCJLINK = conf.env.GCJ

class gcj(Task.Task):
	run_str = '${GCJ} -c -o ${TGT} ${GCJFLAGS} -classpath ${CLASSPATH} ${SRC}'

class gcj_link(ccroot.link_task):
	run_str = '${GCJLINK} ${GCJLINKFLAGS} ${SRC} -o ${TGT}'
	color   = 'YELLOW'

ccroot.USELIB_VARS['gcj_native'] = set(['CLASSPATH', 'JAVACFLAGS', 'GCJFLAGS', 'GCJLINKFLAGS'])


@feature('gcj_native')
@before('apply_java')
def apply_gcj(self):
	if 'javac' in self.features:
		self.bld.fatal('feature gcj_native is not compatible with javac %r' % self)

	nodes_lst = []

	if not self.classpath:
		if not self.env['CLASSPATH']:
			self.env['CLASSPATH'] = '..' + os.pathsep + '.'
	else:
		self.env['CLASSPATH'] = self.classpath

	re_foo = re.compile(self.java_source)

	source_root_node = self.path.find_dir(self.source_root)

	src_nodes = []
	bld_nodes = []

	all_at_once = getattr(self, 'gcjonce', None)

	prefix_path = source_root_node.abspath()
	for (root, dirs, filenames) in os.walk(source_root_node.abspath()):
		for x in filenames:
			file = root + '/' + x
			file = file.replace(prefix_path, '')
			if file.startswith('/'):
				file = file[1:]

			if re_foo.search(file) > -1:
				node = source_root_node.find_resource(file)

				if all_at_once:
					bld_nodes.append(node)
				else:
					node2 = node.change_ext('.o')

					tsk = self.create_task('gcj')
					tsk.set_inputs(node)
					tsk.set_outputs(node2)
					bld_nodes.append(node2)

	#self.env['OUTDIR'] = source_root_node.abspath(self.env)

@feature('gcj_native')
@after('gcj_compile')
def create_link(self)
	self.link_task = tsk = self.create_task('gcj_link')
	tsk.set_inputs(bld_nodes)
	tsk.set_outputs(self.path.find_or_declare(self.target))

