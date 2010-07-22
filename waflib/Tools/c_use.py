#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import os
from waflib import Utils, Errors, Logs
import waflib.Tools
from waflib.TaskGen import feature, before, after

@feature('c', 'cxx', 'd')
@before('apply_incpaths')
@after('apply_link', 'process_source')
def process_use(self):
	"""
	process the uselib_local attribute
	execute after apply_link because of the execution order set on 'link_task'
	"""
	env = self.env

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	self.uselib = self.to_list(getattr(self, 'uselib', []))
	self.includes = self.to_list(getattr(self, 'includes', []))
	names = self.to_list(getattr(self, 'use', []))
	get = self.bld.get_tgen_by_name
	seen = set([])
	tmp = Utils.deque(names) # consume a copy of the list of names
	while tmp:
		lib_name = tmp.popleft()
		# visit dependencies only once
		if lib_name in seen:
			continue

		try:
			y = get(lib_name)
		except Errors.WafError:
			seen.add(lib_name)
			self.uselib.append(lib_name)
			continue

		y.post()
		seen.add(lib_name)

		# object has ancestors to process (shared libraries): add them to the end of the list
		if getattr(y, 'use', None):
			for x in self.to_list(getattr(y, 'use', [])):
				try:
					obj = get(x)
				except Errors.WafError:
					self.uselib.append(x)
				else:
					obj.post()
					try:
						if not isinstance(obj.link_task, waflib.Tools.ccroot.stlink_task):
							tmp.append(x)
					except AttributeError:
						Logs.warn('task generator %s has no link task' % x)

		# link task and flags
		if getattr(y, 'link_task', None):

			link_name = y.target[y.target.rfind(os.sep) + 1:]
			if isinstance(y.link_task, waflib.Tools.ccroot.stlink_task):
				env.append_value('STLIB', [link_name])
			else:
				# some linkers can link against programs
				env.append_value('LIB', [link_name])

			# the order
			self.link_task.set_run_after(y.link_task)

			# for the recompilation
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

			# add the link path too
			tmp_path = y.link_task.outputs[0].parent.bldpath()
			if not tmp_path in env['LIBPATH']:
				env.prepend_value('LIBPATH', [tmp_path])
		else:
			if getattr(self, 'link_task', None):
				for t in getattr(y, 'compiled_tasks', []):
					self.link_task.inputs.extend(t.outputs)

		# add ancestors uselib too - but only propagate those that have no staticlib defined
		for v in self.to_list(getattr(y, 'uselib', [])):
			if not env['STLIB_' + v]:
				if not v in self.uselib:
					self.uselib.insert(0, v)

		# if the library task generator provides 'export_incdirs', add to the include path
		# the export_incdirs must be a list of paths relative to the other library
		if getattr(y, 'export_incdirs', None):
			for x in self.to_list(y.export_incdirs):
				node = y.path.find_dir(x)
				if not node:
					raise Errors.WafError('object %r: invalid folder %r in export_incdirs' % (y.target, x))
				self.includes.append(node)

