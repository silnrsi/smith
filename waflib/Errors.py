#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import traceback, os, sys

class WafError(Exception):
	"""Base for all waf errors"""
	def __init__(self, msg, pyfile=None):
		"""the parameter msg can be an error message or an exception"""
		self.msg = msg
		self.pyfile = pyfile

		if isinstance(msg, Exception):
			self.msg = str(msg)
			self.stack = traceback.extract_tb(sys.exc_info()[2])
		else:
			self.stack = traceback.extract_stack()

		# modify the stack to add the file name
		if pyfile:
			for i in range(len(self.stack)):
				tup = self.stack[i]
				if tup[0] == '<string>':
					self.msg = "%s:%d %s" % (pyfile, tup[1], self.msg)
					self.stack[i] = [pyfile] + list(tup[1:])
					break
			else:
				self.msg = self.msg.replace('<string>', pyfile)

		self.verbose_msg = ''.join(traceback.format_list(self.stack))

	def __str__(self):
		if self.pyfile:
			return "in %s: %s" % (self.pyfile, str(self.msg))
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

