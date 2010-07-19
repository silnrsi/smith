#! /usr/bin/env python

import os
from waflib import Utils, ConfigSet, Options, Build, Context

def cnt(ctx):
	"""do something"""
	print(2)

Context.g_module.__dict__['cnt'] = cnt

class cnt(Build.BuildContext):
	cmd = 'cnt'
	fun = 'build'

	def execute(self):
		self.load()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])
		tot = 0
		for x in self.groups:
			tot += len(x)
		self.to_log('there are %d task generators in this project\n' % tot)
