#! /usr/bin/env python

import os, sys, imp
from waflib import Context, Options, Configure, Utils, Logs

"""
- no build directory and no script files
- just a c4che directory for the configuration files
- configure, clean or build
"""

def options(opt):
	gr.add_option('--target', action='store', default='program', help='type: program, shlib, stlib, objects', dest='progtype')
	gr.add_option('--source', action='store', default='main.c', help='space-separated list of source files', dest='progtype')
	opt.load('compiler_c')

def configure(conf):
	conf.load('compiler_c')

def build(bld):
	from waflib import Options
	tp = Options.options.progtype
	features = 'c cprogram'
	if tp == 'shlib':
		features = 'c cshlib'
	elif tp == 'stlib':
		features = 'c cstlib'
	elif tp == 'objects':
		features = 'c'

	source = Options.options.source
	bld(features=features, source=source)

def start(cwd, version, wafdir):
	# no script file here
	Logs.init_log()
	Context.waf_dir = wafdir
	Context.out_dir = Context.top_dir = Context.run_dir = cwd
	Context.g_module = imp.new_module('wscript')
	Context.g_module.root_path = cwd
	Context.Context.recurse = lambda x, y: getattr(Context.g_module, x.cmd, Utils.nada)(x)

	Context.g_module.configure = configure
	Context.g_module.build = build

	opt = Options.OptionsContext().execute()

	do_config = 'configure' in sys.argv
	try:
		os.stat(cwd + '/c4che')
	except:
		do_config = True
	if do_config:
		Context.create_context('configure').execute()
		if 'configure' in sys.argv:

	if 'clean' in sys.argv:
		Context.create_context('clean').execute()

	if 'build' in sys.argv:
		Context.create_context('build').execute()

from waflib.Task import ASK_LATER
from waflib.Tools.c import c

class c2(c):
	# Make a subclass of the default c task, and bind the .c extension to it

	def runnable_status(self):
		ret = super(c, self).runnable_status()
		self.more_tasks = []

		# use a cache to avoid creating the same tasks
		# for example, truc.cpp might be compiled twice
		try:
			shared = self.generator.bld.shared_tasks
		except AttributeError:
			shared = self.generator.bld.shared_tasks = {}

		if ret != ASK_LATER:
			for x in self.generator.bld.node_deps[self.uid()]:
				node = x.parent.get_src().find_resource(x.name.replace('.h', '.c'))
				if node:
					try:
						tsk = shared[node]
					except:
						tsk = shared[node] = self.generator.c_hook(node)

						self.more_tasks.append(tsk)

					# add the node created to the link task outputs
					try:
						link = self.generator.link_task
					except AttributeError:
						pass
					else:
						if not tsk.outputs[0] in link.inputs:
							link.inputs.append(tsk.outputs[0])
							link.set_run_after(tsk)

							# any change in the order of the input nodes may cause a recompilation
							link.inputs.sort(key=lambda x: x.abspath())

			# if you want to modify some flags
			# you *must* have the task recompute the signature
			self.env.append_value('CXXFLAGS', '-O2')
			delattr(self, 'cache_sig')
			return super(c, self).runnable_status()

		return ret

@TaskGen.extension('.c')
def c_hook(self, node):
	return self.create_compiled_task('c2', node)

