#! /usr/bin/env python

import os, sys, imp
from waflib import Context, Options, Configure, Utils, Logs, TaskGen, Task, Build, ConfigSet
import waflib.Tools.c

"""
Create a modified waf file in which tasks use timestamps only
"""

def recurse_rep(x, y):
	f = getattr(Context.g_module, x.cmd or x.fun, Utils.nada)
	return f(x)

def start(cwd, version, wafdir):
	# this is the entry point of our small build system
	# no script file here
	Logs.init_log()
	Context.waf_dir = wafdir
	Context.out_dir = Context.top_dir = Context.run_dir = cwd
	Context.g_module = Context.load_module(cwd + '/wscript')
	#Context.g_module = imp.new_module('wscript')
	Context.g_module.root_path = cwd
	Context.Context.recurse = recurse_rep

	Context.g_module.top = Context.g_module.out = '.'

	# just parse the options and execute a build
	Options.OptionsContext().execute()
	bld = Context.create_context('build')
	bld.options = Options.options
	bld.environ = os.environ
	bld.execute()

class B2(Build.BuildContext):
	def load_envs(self):
		self.env = ConfigSet.ConfigSet()
	def store(self):
		pass
	def restore(self):
		self.init_dirs()

