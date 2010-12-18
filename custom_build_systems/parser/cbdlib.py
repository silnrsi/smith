#! /usr/bin/env python

import os, sys, imp
from waflib import Context, Options, Configure, Utils, Logs

def options(opt):
	opt.load('compiler_c')

def configure(conf):
	conf.options = Options.options
	conf.load('compiler_c')

def build(bld):
	bld.objects(source='main.c')

def recurse_rep(x, y):
	f = getattr(Context.g_module, x.cmd or x.fun, Utils.nada)
	return f(x)

def start(cwd, version, wafdir):
	# simple example, the file main.c is hard-coded
	try:
		os.stat(cwd + '/cbit')
	except:
		print('call from a folder containing a file named "cbit"')
		sys.exit(1)

	Logs.init_log()
	Context.waf_dir = wafdir
	Context.top_dir = Context.run_dir = cwd
	Context.out_dir = os.path.join(cwd, 'build')
	Context.g_module = imp.new_module('wscript')
	Context.g_module.root_path = os.path.join(cwd, 'cbit')
	Context.Context.recurse = recurse_rep

	# this is a fake module, which looks like a standard wscript file
	Context.g_module.options = options
	Context.g_module.configure = configure
	Context.g_module.build = build

	Options.OptionsContext().execute()

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
