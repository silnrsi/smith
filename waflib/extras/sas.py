#!/usr/bin/env python
# encoding: utf-8
# Mark Coggeshall, 2010

"SAS support"

import os, re
from waflib import Utils, Task, TaskGen, Runner, Build, Errors, Node
from waflib.TaskGen import feature, before
from waflib.Logs import error, warn, debug

sas_fun, _ = Task.compile_fun('sas -sysin ${SRCFILE} -log ${LOGFILE} -print ${LSTFILE}', shell=False)

class sas(Task.Task):
	vars = ['SAS', 'SASFLAGS']
	def run(task):
		command = 'SAS'
   	env = task.env
   	bld = task.generator.bld

	fun = sas_fun

	node = task.inputs[0]
	srcfile = node.abspath()
	sr2 = node.parent.get_bld().abspath() + os.pathsep + node.parent.get_src().abspath() + os.pathsep
	logfilenode = node.change_ext('.log')
	lstfilenode = node.change_ext('.lst')
	#task.env.LOGFILE = os.path.join(bld.srcnode.abspath(), task.env.logdir, logfilenode.name)
	#task.env.LSTFILE = os.path.join(bld.srcnode.abspath(), task.env.lstdir, lstfilenode.name)
	a = node.make_node(os.path.join(node.parent.get_bld().abspath(), task.env.logdir))
	b = node.make_node(os.path.join(node.parent.get_bld().abspath(), task.env.lstdir))
	task.env.LOGFILE = os.path.join(node.parent.get_bld().abspath(), task.env.logdir, logfilenode.name)
	task.env.LSTFILE = os.path.join(node.parent.get_bld().abspath(), task.env.lstdir, lstfilenode.name)

	# set the cwd
	task.cwd = task.inputs[0].parent.get_src().abspath()

	warn('Running %s on %s' % (command, srcfile))

	task.env.env = {'SASINPUTS': sr2}
	task.env.SRCFILE = srcfile
	ret = fun(task)
	if ret:
		error('Running %s on %s returned a non-zero exit' % (command, task.env.SRCFILE))
		error('SRCFILE = %s' % task.env.SRCFILE)
		error('LOGFILE = %s' % task.env.LOGFILE)
		error('LSTFILE = %s' % task.env.LSTFILE)
	return ret

@feature('sas')
@before('process_source')
def apply_sas(self):
	if not getattr(self, 'type', None) in ['sas']:
		self.type = 'sas'

	self.env['logdir'] = getattr(self, 'logdir', 'log')
	self.env['lstdir'] = getattr(self, 'lstdir', 'lst')

	deps_lst = []

	if getattr(self, 'deps', None):
		deps = self.to_list(self.deps)
		for filename in deps:
			n = self.path.find_resource(filename)
			if not n: n = self.bld.root.find_resource(filename)
			if not n: raise Errors.WafError('cannot find input file %s for processing' % filename)
			if not n in deps_lst: deps_lst.append(n)

	for node in self.to_nodes(self.source):
		if self.type == 'sas':
			task = self.create_task('sas', src = node, tgt = None)
		task.env = self.env
		task.dep_nodes = deps_lst
	self.source = []

def configure(self):
	self.find_program('sas', var='SAS', mandatory=False)

