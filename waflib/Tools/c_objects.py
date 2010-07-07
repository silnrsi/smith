#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re
from waflib import TaskGen, Task, Utils, Logs, Build, Options, Node, Errors
from waflib.Logs import error, debug, warn
from waflib.TaskGen import after, before, feature, taskgen_method
from waflib.Tools import c_aliases, c_preproc, c_config, c_asm

@feature('cprogram', 'cxxprogram', 'cstlib', 'cxxstlib', 'cshlib', 'cxxshlib', 'dprogram', 'dstlib', 'dshlib')
@after('apply_link')
def apply_objdeps(self):
	"add the .o files produced by some other object files in the same manner as uselib_local"
	names = getattr(self, 'add_objects', [])
	if not names:
		return
	names = self.to_list(names)

	get = self.bld.get_tgen_by_name
	seen = []
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = get(x)

		# object has ancestors to process first ? update the list of names
		if getattr(y, 'add_objects', None):
			added = 0
			lst = y.to_list(y.add_objects)
			lst.reverse()
			for u in lst:
				if u in seen: continue
				added = 1
				names = [u]+names
			if added: continue # list of names modified, loop

		# safe to process the current object
		y.post()
		seen.append(x)

		for t in getattr(y, 'compiled_tasks', []):
			self.link_task.inputs.extend(t.outputs)

@after('apply_link')
def process_obj_files(self):
	if not hasattr(self, 'obj_files'):
		return
	for x in self.obj_files:
		node = self.path.find_resource(x)
		self.link_task.inputs.append(node)

@taskgen_method
def add_obj_file(self, file):
	"""Small example on how to link object files as if they were source
	obj = bld.create_obj('cc')
	obj.add_obj_file('foo.o')"""
	if not hasattr(self, 'obj_files'): self.obj_files = []
	if not 'process_obj_files' in self.meths: self.meths.append('process_obj_files')
	self.obj_files.append(file)

