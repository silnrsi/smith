#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)

import os, re
from Configure import conf
import TaskGen, Task, Utils
from TaskGen import feature, before

@feature('gcj')
@before('apply_java')
def apply_gcj(self):
	Utils.def_attrs(self, jarname='', jaropts='', classpath='',
		source_root='.', jar_mf_attributes={}, jar_mf_classpath=[])

	try:
		self.meths.remove('apply_java')
	except ValueError:
		pass

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

	tsk = self.create_task('gcj_link')
	tsk.set_inputs(bld_nodes)
	tsk.set_outputs(self.path.find_or_declare(self.target))
	if getattr(self, 'gcjlinkflags', None):
		tsk.env.append_unique('GCJLINKFLAGS', self.gcjlinkflags)


cls = Task.simple_task_type('gcj', '${GCJ} -c -o ${TGT} ${GCJFLAGS} -classpath ${CLASSPATH} ${SRC}')
cls.before = 'gcj_link jar_create'
cls.color  = 'BLUE'

cls = Task.simple_task_type('gcj_link', '${GCJLINK} ${GCJLINKFLAGS} ${SRC} -o ${TGT}')
cls.before = 'jar_create'
cls.color  = 'GREEN'

def configure(conf):
	conf.find_program('gcj', var='GCJ')
	conf.env.GCJLINK = conf.env.GCJ

