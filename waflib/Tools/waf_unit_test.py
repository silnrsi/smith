#!/usr/bin/env python
# encoding: utf-8

import os, sys
from waflib import Build, TaskGen, Utils, Options, Logs, Task
from waflib.TaskGen import before, after, feature

"""
New unit test system

The targets with feature 'test' are executed after they are built
bld(features='cprogram cc test', ...)

To display the results:
import UnitTest
bld.add_post_fun(UnitTest.summary)
"""

import threading
testlock = threading.Lock()

@feature('test')
@after('apply_link', 'vars_target_cprogram')
def make_test(self):
	if getattr(self, 'link_task', None):
		self.default_install_path = None
		self.create_task('utest', self.link_task.outputs)

def exec_test(self):
	testlock.acquire()
	fail = False
	try:
		filename = self.inputs[0].abspath()

		try:
			fu = getattr(self.generator.bld, 'all_test_paths')
		except AttributeError:
			fu = os.environ.copy()
			self.generator.bld.all_test_paths = fu

			lst = []
			for g in self.generator.bld.groups:
				for tg in g:
					link_task = getattr(tg, 'link_task', None)
					if link_task:
						lst.append(link_task.outputs[0].parent.abspath())

			def add_path(dct, path, var):
				dct[var] = os.pathsep.join(Utils.to_list(path) + [os.environ.get(var, '')])
			if sys.platform == 'win32':
				add_path(fu, lst, 'PATH')
			elif sys.platform == 'darwin':
				add_path(fu, lst, 'DYLD_LIBRARY_PATH')
				add_path(fu, lst, 'LD_LIBRARY_PATH')
			else:
				add_path(fu, lst, 'LD_LIBRARY_PATH')

		try:
			ret = self.generator.bld.cmd_and_log(filename, cwd=self.inputs[0].parent.abspath(), quiet=1, env=fu)
		except Exception as e:
			fail = True
			ret = '' + str(e)
		else:
			pass

		stats = getattr(self.generator.bld, 'utest_results', [])
		stats.append((filename, fail, ret))
		self.generator.bld.utest_results = stats
	finally:
		testlock.release()

class utest(Task.Task):
	color = 'RED'
	quiet = True
	ext_in = ['.bin']
	run = exec_test
	vars = []
	def runnable_status(self):
		ret = super(utest, self).runnable_status()
		if ret == Task.SKIP_ME:
			if getattr(Options.options, 'all_tests', False):
				return Task.RUN_ME
		return ret

def summary(bld):
	lst = getattr(bld, 'utest_results', [])
	if lst:
		Logs.pprint('CYAN', 'execution summary')
		for (f, fail, ret) in lst:
			col = fail and 'RED' or 'GREEN'
			Logs.pprint(col, (fail and 'FAIL' or 'ok') + " " + f)
			if fail: Logs.pprint('NORMAL', ret.replace('\\n', '\n'))

def options(opt):
	opt.add_option('--alltests', action='store_true', default=False, help='Exec all unit tests', dest='all_tests')

