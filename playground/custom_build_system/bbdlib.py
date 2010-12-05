#! /usr/bin/env python

import os, sys, imp
from waflib import Context, Options, Configure, Utils

def start(cwd, version, wafdir):
	try:
		os.stat(cwd + '/bbit')
	except:
		print('call from a folder containing a file named "bbit"')
		sys.exit(1)

	Context.waf_dir = wafdir
	Context.top = Context.run_dir = cwd
	Context.out = os.path.join(cwd, 'build')
	Context.g_module = imp.new_module('wscript')
	Context.g_module.root_path = os.path.join(cwd, 'bbit')
	Context.Context.recurse = \
		lambda x, y: getattr(Context.g_module, x.cmd, Utils.nada)(x)

	Context.g_module.configure = lambda ctx: ctx.load('g++')
	Context.g_module.build = lambda bld: bld.objects(source='main.c')

	opt = Options.OptionsContext().execute()

	do_config = 'configure' in sys.argv
	try:
		os.stat(cwd + '/build')
	except:
		do_config = True
	if do_config:
		Context.create_context('configure').execute()

	if 'clean' in sys.argv:
		Context.create_context('clean').execute()
	if 'build' in sys.argv:
		Context.create_context('build').execute()
