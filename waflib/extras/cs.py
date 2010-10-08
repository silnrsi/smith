#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
C# support

We will need a demo to check that this works
bld(features='cs', source='main.cs', target='foo')
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

	# what kind of assembly are we generating?
	self.env['CSTYPE'] = getattr(self, 'type', 'exe')

	# process the sources
	nodes = [self.path.find_resource(i) for i in self.to_list(self.source)]
	self.create_task('mcs', nodes, self.path.find_or_declare(self.target))

class mcs(Task.Task):
	color   = 'YELLOW'
	run_str = '${MCS} ${SRC} /target:${CSTYPE} /out:${TGT} ${CSFLAGS} ${ASS_ST:ASSEMBLIES} ${RES_ST:RESOURCES}'

def configure(conf):
	csc = getattr(Options.options, 'cscbinary', None)
	if csc:
		conf.env.MCS = csc
	conf.find_program(['gmcs', 'mcs'], var='MCS')
	conf.env.ASS_ST = '/r:%s'
	conf.env.RES_ST = '/resource:%s'

def options(opt):
	opt.add_option('--with-csc-binary', type='string', dest='cscbinary')

