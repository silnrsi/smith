#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
C# support

We will need a demo to check that this works
bld(features='cs', source='main.cs', gen='foo')
"""

from waflib import TaskGen, Utils, Task, Options, Logs, Errors
from TaskGen import before, after, feature
from waflib.Tools import ccroot
from waflib.Configure import conf

ccroot.USELIB_VARS['cs'] = set(['CSFLAGS', 'ASSEMBLIES', 'RESOURCES'])
ccroot.lib_patterns['csshlib'] = ['%s']

@feature('cs')
@after('apply_uselib_cs')
@before('process_source')
def apply_cs(self):
	cs_nodes = []
	no_nodes = []
	for x in self.to_nodes(self.source):
		if x.name.endswith('.cs'):
			cs_nodes.append(x)
		else:
			no_nodes.append(x)
	self.source = no_nodes

	self.cs_task = tsk = self.create_task('mcs', cs_nodes, self.path.find_or_declare(self.gen))
	tsk.env.CSTYPE = '/target:%s' % getattr(self, 'type', 'exe')
	tsk.env.OUT    = '/out:%s' % tsk.outputs[0].abspath()

@feature('cs')
@after('apply_cs')
def use_cs(self):
	names = self.to_list(getattr(self, 'use', []))
	get = self.bld.get_tgen_by_name
	for x in names:
		try:
			y = get(x)
		except Errors.WafError:
			self.cs_task.env.append_value('CSFLAGS', '/reference:%s' % x)
			continue
		y.post()

		tsk = getattr(y, 'cs_task', None) or getattr(y, 'link_task', None)
		if not tsk:
			self.bld.fatal('cs task has no link task for use %r' % self)
		self.cs_task.set_run_after(tsk) # order
		self.cs_task.dep_nodes.extend(tsk.outputs) # dependency
		self.cs_task.env.append_value('CSFLAGS', '/reference:%s' % tsk.outputs[0].abspath())

class mcs(Task.Task):
	color   = 'YELLOW'
	run_str = '${MCS} ${CSTYPE} ${CSFLAGS} ${ASS_ST:ASSEMBLIES} ${RES_ST:RESOURCES} ${OUT} ${SRC}'

def configure(conf):
	csc = getattr(Options.options, 'cscbinary', None)
	if csc:
		conf.env.MCS = csc
	conf.find_program(['csc', 'mcs', 'gmcs'], var='MCS')
	conf.env.ASS_ST = '/r:%s'
	conf.env.RES_ST = '/resource:%s'

def options(opt):
	opt.add_option('--with-csc-binary', type='string', dest='cscbinary')

class fake_csshlib(Task.Task):
	"""task used for reading a foreign .net assembly and adding the dependency on it"""
	color   = 'YELLOW'
	inst_to = None

	def runnable_status(self):
		for x in self.outputs:
			x.sig = Utils.h_file(x.abspath())
		return Task.SKIP_ME

@conf
def read_csshlib(self, name, paths=[]):
	"""read a foreign .net assembly for the use system"""
	return self(name=name, features='fake_lib', lib_paths=paths, lib_type='csshlib')

