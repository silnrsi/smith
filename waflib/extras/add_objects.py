#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2011 (ita)

"""
Use this tool only if your company has lost the original source code :-)
"""

from waflib.TaskGen import extension
from waflib import Task, Utils

class fake_o(Task.Task):
	def runnable_status(self):
		return Task.SKIP_ME

@extension('.o', '.obj')
def add_those_o_files(self, node):
	tsk = self.create_task('fake_o', [], node)
	try:
		self.compiled_tasks.append(tsk)
	except AttributeError:
		self.compiled_tasks = [tsk]

