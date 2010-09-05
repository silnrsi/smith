#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
This file is provided to enable compatibility with waf 1.5, it will be removed in waf 1.7
"""

import sys
from waflib import ConfigSet, Logs, Options, Scripting, Task, Build, Configure, Node, Runner, TaskGen, Utils, Errors, Context

# the following is to bring some compatibility with waf 1.5 "import waflib.Configure → import Configure"
sys.modules['Environment'] = ConfigSet
ConfigSet.Environment = ConfigSet.ConfigSet

sys.modules['Logs'] = Logs
sys.modules['Options'] = Options
sys.modules['Scripting'] = Scripting
sys.modules['Task'] = Task
sys.modules['Build'] = Build
sys.modules['Configure'] = Configure
sys.modules['Node'] = Node
sys.modules['Runner'] = Runner
sys.modules['TaskGen'] = TaskGen
sys.modules['Utils'] = Utils

from waflib.Tools import c_preproc
sys.modules['preproc'] = c_preproc

from waflib.Tools import c_config
sys.modules['config_c'] = c_config

ConfigSet.ConfigSet.copy = ConfigSet.ConfigSet.derive
ConfigSet.ConfigSet.set_variant = Utils.nada

Build.BuildContext.add_subdirs = Build.BuildContext.recurse
Build.BuildContext.new_task_gen = Build.BuildContext.__call__
Build.BuildContext.is_install = 0
Node.Node.relpath_gen = Node.Node.path_from

def name_to_obj(self, s, env=None):
	Logs.warn('compat: change "name_to_obj(name, env)" by "get_tgen_by_name(name)"')
	return self.get_tgen_by_name(s)
Build.BuildContext.name_to_obj = name_to_obj

Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse
Configure.ConfigurationContext.check_tool = Configure.ConfigurationContext.tool
Configure.conftest = Configure.conf
Configure.ConfigurationError = Errors.ConfigurationError

Options.OptionsContext.sub_options = Options.OptionsContext.recurse
Options.OptionsContext.tool_options = Context.Context.tool
Options.Handler = Options.OptionsContext

Task.simple_task_type = Task.task_type_from_func = Task.task_factory
Task.TaskBase.classes = Task.classes

@TaskGen.feature('d')
@TaskGen.before('apply_incpaths')
def old_importpaths(self):
	if getattr(self, 'importpaths', []):
		self.includes = self.importpaths

from waflib import Context
eld = Context.load_tool
def load_tool(*k, **kw):
	ret = eld(*k, **kw)
	if 'set_options' in ret.__dict__:
		Logs.warn('compat: rename "set_options" to options')
		ret.options = ret.set_options
	if 'detect' in ret.__dict__:
		Logs.warn('compat: rename "detect" to "configure"')
		ret.configure = ret.detect
	return ret
Context.load_tool = load_tool

rev = Context.load_module
def load_module(path):
	ret = rev(path)
	if 'set_options' in ret.__dict__:
		Logs.warn('compat: rename "set_options" to "options" (%r)' % path)
		ret.options = ret.set_options
	if 'srcdir' in ret.__dict__:
		Logs.warn('compat: rename "srcdir" to "top" (%r)' % path)
		ret.top = ret.srcdir
	if 'blddir' in ret.__dict__:
		Logs.warn('compat: rename "blddir" to "out" (%r)' % path)
		ret.out = ret.blddir
	return ret
Context.load_module = load_module

old_apply = TaskGen.task_gen.apply
def apply(self):
	self.features = self.to_list(self.features)
	if 'cc' in self.features:
		Logs.warn('compat: the feature cc does not exist anymore (use "c")')
		self.features.remove('cc')
		self.features.append('c')
	if 'cstaticlib' in self.features:
		Logs.warn('compat: the feature cstaticlib does not exist anymore (use "cstlib" or "cxxstlib")')
		self.features.remove('cstaticlib')
		self.features.append(('cxx' in self.features) and 'cxxstlib' or 'cstlib')
	old_apply(self)
TaskGen.task_gen.apply = apply

def waf_version(*k, **kw):
	Logs.warn('wrong version (waf_version was removed in waf 1.6)')
Utils.waf_version = waf_version


import os
@TaskGen.feature('c', 'cxx', 'd')
@TaskGen.before('apply_incpaths')
@TaskGen.after('apply_link', 'process_source')
def apply_uselib_local(self):
	"""
	process the uselib_local attribute
	execute after apply_link because of the execution order set on 'link_task'
	"""
	env = self.env
	from waflib.Tools.ccroot import stlink_task

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	self.uselib = self.to_list(getattr(self, 'uselib', []))
	self.includes = self.to_list(getattr(self, 'includes', []))
	names = self.to_list(getattr(self, 'uselib_local', []))
	get = self.bld.get_tgen_by_name
	seen = set([])
	tmp = Utils.deque(names) # consume a copy of the list of names
	while tmp:
		lib_name = tmp.popleft()
		# visit dependencies only once
		if lib_name in seen:
			continue

		y = get(lib_name)
		y.post()
		seen.add(lib_name)

		# object has ancestors to process (shared libraries): add them to the end of the list
		if getattr(y, 'uselib_local', None):
			for x in self.to_list(getattr(y, 'uselib_local', [])):
				obj = get(x)
				obj.post()
				if getattr(obj, 'link_task', None):
					if not isinstance(obj.link_task, stlink_task):
						tmp.append(x)

		# link task and flags
		if getattr(y, 'link_task', None):

			link_name = y.target[y.target.rfind(os.sep) + 1:]
			if isinstance(y.link_task, stlink_task):
				env.append_value('STLIB', [link_name])
			else:
				# some linkers can link against programs
				env.append_value('LIB', [link_name])

			# the order
			self.link_task.set_run_after(y.link_task)

			# for the recompilation
			self.link_task.dep_nodes += y.link_task.outputs

			# add the link path too
			tmp_path = y.link_task.outputs[0].parent.bldpath()
			if not tmp_path in env['LIBPATH']:
				env.prepend_value('LIBPATH', [tmp_path])

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

@TaskGen.feature('cprogram', 'cxxprogram', 'cstlib', 'cxxstlib', 'cshlib', 'cxxshlib', 'dprogram', 'dstlib', 'dshlib')
@TaskGen.after('apply_link')
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

@TaskGen.after('apply_link')
def process_obj_files(self):
	if not hasattr(self, 'obj_files'):
		return
	for x in self.obj_files:
		node = self.path.find_resource(x)
		self.link_task.inputs.append(node)

@TaskGen.taskgen_method
def add_obj_file(self, file):
	"""Small example on how to link object files as if they were source
	obj = bld.create_obj('cc')
	obj.add_obj_file('foo.o')"""
	if not hasattr(self, 'obj_files'): self.obj_files = []
	if not 'process_obj_files' in self.meths: self.meths.append('process_obj_files')
	self.obj_files.append(file)


old_define = Configure.ConfigurationContext.define

@Configure.conf
def define(self, key, val, quote=True):
	old_define(self, key, val, quote)
	if key.startswith('HAVE_'):
		self.env[key] = 1

old_undefine = Configure.ConfigurationContext.undefine

@Configure.conf
def undefine(self, key):
	old_undefine(self, key)
	if key.startswith('HAVE_'):
		self.env[key] = 0

# some people might want to use export_incdirs, but it was renamed
def set_incdirs(self, val):
	Logs.warn('compat: change "export_incdirs" by "export_includes"')
	self.export_includes = val
TaskGen.task_gen.export_incdirs = property(None, set_incdirs)

