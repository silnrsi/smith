#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

import re

from waflib import Utils, Task, TaskGen, Logs
from waflib.TaskGen import feature, before, after, extension
from waflib.Configure import conf

INC_REGEX = """(?:^|['">]\s*;)\s*INCLUDE\s+(?:\w+_)?[<"'](.+?)(?=["'>])"""
USE_REGEX = """(?:^|;)\s*USE(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""
MOD_REGEX = """(?:^|;)\s*MODULE(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""

EXT_MOD = ".mod"

# TODO (DC)
#   - handle pre-processed files (FORTRANPPCOM in scons)
#   - handle modules
#   - handle multiple dialects
#   - windows...
# TODO (ita) understand what does all that mean ^^

re_inc = re.compile(INC_REGEX, re.I)
re_use = re.compile(USE_REGEX, re.I)
re_mod = re.compile(MOD_REGEX, re.I)

class fortran_parser(object):
	"""
	we cannot do it at once from a scanner function, so the idea is to let the method
	runnable_status from the fortran task do a global resolution on the names found

	the scanning will then return:
	* the nodes of the module names that will be produced
	* the nodes of the include files that will be used
	* the names of the modules to use
	"""

	def __init__(self, incpaths):
		self.seen = []

		self.nodes = []
		self.names = []

		self.incpaths = incpaths

	def find_deps(self, node):
		"""read a file and output what the regexps say about it"""
		txt = node.read()
		incs = []
		uses = []
		mods = []
		for line in txt.splitlines():
			# line by line regexp search? optimize?
			m = re_inc.search(line)
			if m:
				incs.append(m.group(1))
			m = re_use.search(line)
			if m:
				uses.append(m.group(1))
			m = re_mod.search(line)
			if m:
				mods.append(m.group(1))
		return (incs, uses, mods)

	def start(self, node):
		"""use the stack self.waiting to hold the nodes to iterate on"""
		self.waiting = [node]
		while self.waiting:
			nd = self.waiting.pop(0)
			self.iter(nd)

	def iter(self, node):
		path = node.abspath()
		incs, uses, mods = self.find_deps(node)
		for x in incs:
			if x in self.seen:
				continue
			self.seen.append(x)
			self.tryfind_header(x)

		for x in uses:
			name = "USE@%s" % x
			if not name in self.names:
				self.names.append(name)

		for x in mods:
			name = "MOD@%s" % x
			if not name in self.names:
				self.names.append(name)

		#for x in mods:
		#	node = self.task.generator.bld.bldnode.find_or_declare(x + EXT_MOD)
		#	assert(node)
		#	if node.abspath() in self.seen:
		#		continue
		#	self.task.set_inputs(node)

	def tryfind_header(self, filename):
		found = None
		for n in self.incpaths:
			found = n.find_resource(filename)
			if found and not found in self.outputs:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)

def scan(self):
	tmp = fortran_parser(self.generator.includes_nodes)
	tmp.task = self
	tmp.start(self.inputs[0])
	if Logs.verbose:
		Logs.debug('deps: deps for %r: %r; unresolved %r' % (self.inputs, tmp.nodes, tmp.names))
	return (tmp.nodes, tmp.names)

