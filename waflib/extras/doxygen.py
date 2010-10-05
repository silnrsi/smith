#! /usr/bin/env python
# encoding: UTF-8
# Thomas Nagy 2008-2010 (ita)

"""
ported from waf 1.5 (incomplete)
"""

from fnmatch import fnmatchcase
import os, os.path, re, stat
from waflib import Task, Utils, Node
from waflib.TaskGen import feature

DOXY_STR = '${DOXYGEN} - '
DOXY_FMTS = 'html latex man rft xml'.split()
DOXY_EXTS = '**/*.(c|cc|cxx|cpp|c\\+\\+|C|h|hh|hxx|hpp|h\\+\\+|H|py|java|cs|ii|ixx|ipp|i\\+\\+|inl|idl|odl|php|php3|inc|m|mm)'

class doxygen(Task.Task):
	vars  = ['DOXYGEN', 'DOXYFLAGS']
	color = 'BLUE'

	def runnable_status(self):
		'''
		self.pars are populated in runnable_status - because this function is being
		run *before* both self.pars "consumers" - scan() and run()
		'''
		if not getattr(self, 'pars', None):
			self.pars = Utils.str2dict(self.inputs[0].read())
			if not self.pars.get('OUTPUT_DIRECTORY'):
				self.pars['OUTPUT_DIRECTORY'] = self.inputs[0].parent.get_bld().abspath()
			if not self.pars.get('INPUT'):
				self.pars['INPUT'] = self.inputs[0].parent.abspath()
		self.signature()
		return Task.Task.runnable_status(self)

	def scan(self):
		recurse = self.pars.get('RECURSIVE') == 'YES'
		excludes = self.pars.get('EXCLUDE_PATTERNS', '').split()
		includes = self.pars.get('FILE_PATTERNS', '').split()
		if not includes:
			includes = DOXY_EXTS
		ret = [x for x in self.inputs[0].parent.ant_glob(includes) if not x.is_child_of(self.generator.bld.bldnode)]
		return (ret, [])

	def run(self):
		code = '\n'.join(['%s = %s' % (x, self.pars[x]) for x in self.pars])
		#fmt = DOXY_STR % (self.inputs[0].parent.abspath())
		cmd = Utils.subst_vars(DOXY_STR, self.env)
		proc = Utils.subprocess.Popen(cmd, shell=True, stdin=Utils.subprocess.PIPE)
		proc.communicate(code)
		return proc.returncode

	def post_run(self):

		nodes = self.inputs[0].parent.get_bld().ant_glob('**/*')
		for x in nodes:
			x.sig = Utils.h_file(x.abspath())
		self.outputs += nodes

		return Task.Task.post_run(self)

	#def install(self):
	#	if getattr(self.generator, 'install_to', None):
	#		update_build_dir(self.inputs[0].parent, self.env)
	#		pattern = getattr(self, 'instype', 'html/*')
	#		self.generator.bld.install_files(self.generator.install_to, self.generator.path.ant_glob(pattern, dir=0, src=0))

class tar(Task.Task):
	"quick tar creation"
	run_str = '${TAR} ${TAROPTS} ${TGT} ${SRC}'
	color   = 'RED'
	after   = ['doxygen']
	def runnable_status(self):
		for x in getattr(self, 'input_tasks', []):
			if not x.hasrun:
				return Task.ASK_LATER

		if not getattr(self, 'tar_done_adding', None):
			# execute this only once
			self.tar_done_adding = True
			for x in getattr(self, 'input_tasks', []):
				self.set_inputs(x.outputs)
			if not self.inputs:
				return Task.SKIP_ME
		return Task.Task.runnable_status(self)

	def __str__(self):
		tgt_str = ' '.join([a.nice_path(self.env) for a in self.outputs])
		return '%s: %s\n' % (self.__class__.__name__, tgt_str)

@feature('doxygen')
def process_doxy(self):
	if not getattr(self, 'doxyfile', None):
		self.generator.bld.fatal('no doxyfile??')

	node = self.path.find_resource(self.doxyfile)
	if not node:
		raise ValueError('doxygen file not found')

	# the task instance
	dsk = self.create_task('doxygen', node)

	if getattr(self, 'doxy_tar', None):
		tsk = self.create_task('tar')
		tsk.input_tasks = [dsk]
		tsk.set_outputs(self.path.find_or_declare(self.doxy_tar))
		if self.doxy_tar.endswith('bz2'):
			tsk.env['TAROPTS'] = ['cjf']
		elif self.doxy_tar.endswith('gz'):
			tsk.env['TAROPTS'] = ['czf']
		else:
			tsk.env['TAROPTS'] = ['cf']

def configure(conf):
	conf.find_program('doxygen', var='DOXYGEN')
	conf.find_program('tar', var='TAR')

