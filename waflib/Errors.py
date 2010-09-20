#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import traceback, os, sys

class WafError(Exception):
	"""Base for all waf errors"""
	def __init__(self, msg='', ex=None, pyfile=None):
		"""the parameter msg can be an error message or an exception"""
		self.msg = msg
		self.pyfile = pyfile

		assert not isinstance(msg, Exception)

		self.stack = []
		if ex:
			if not msg:
				self.msg = str(ex)
			if isinstance(ex, WafError):
				self.stack = ex.stack
			else:
				self.stack = traceback.extract_tb(sys.exc_info()[2])
		self.stack += traceback.extract_stack()[:-1]

		# modify the stack to add the file name
		if pyfile:
			for i in range(len(self.stack)):
				tup = self.stack[i]
				if tup[0] == '<string>':
					#self.msg = "in %s:%d %s" % (pyfile, tup[1], self.msg)
					self.stack[i] = [pyfile] + list(tup[1:])
			self.msg = self.msg.replace('<string>', pyfile)
		self.verbose_msg = ''.join(traceback.format_list(self.stack))

	def __str__(self):
		return str(self.msg)

class BuildError(WafError):
	"""Error raised during the build and install phases"""
	def __init__(self, error_tasks=[]):
		self.tasks = error_tasks
		WafError.__init__(self, self.format_error())

	def format_error(self):
		"""format the error messages from the tasks that failed"""
		lst = ['Build failed']
		for tsk in self.tasks:
			txt = tsk.format_error()
			if txt: lst.append(txt)
		return '\n'.join(lst)

class ConfigurationError(WafError):
	"""configuration exception"""
	pass

class TaskRescan(WafError):
	"""task-specific exception type, trigger a signature recomputation"""
	pass

class TaskNotReady(WafError):
	"""task-specific exception type, raised when the task signature cannot be computed"""
	pass

