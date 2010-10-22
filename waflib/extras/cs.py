#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
C# support

We will need a demo to check that this works
bld(features='cs', source='main.cs', gen='foo')
"""

from waflib import TaskGen, Utils, Task, Options, Logs
from TaskGen import before, after, feature
from waflib.Tools import ccroot

ccroot.USELIB_VARS['cs'] = set(['CSFLAGS', 'ASSEMBLIES', 'RESOURCES'])

@feature('cs')
@after('apply_uselib_cs')
@before('process_source')
def apply_cs(self):
	try: self.meths.remove('process_source')
	except ValueError: pass

	# process the sources
	nodes = [self.path.find_resource(i) for i in self.to_list(self.source)]
	tsk = self.create_task('mcs', nodes, self.path.find_or_declare(self.gen))

	# what kind of assembly are we generating?
	tsk.env.CSTYPE = '/target:%s' % getattr(self, 'type', 'exe')
	tsk.env.OUT    = '/out:%s' % tsk.outputs[0].abspath()


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

