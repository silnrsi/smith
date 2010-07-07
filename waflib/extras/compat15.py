#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import sys

from waflib import ConfigSet, Logs, Options, Scripting, Task, Build, Configure, Node, Runner, TaskGen, Utils, Errors

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
Configure.conftest = Configure.conf
Configure.ConfigurationError = Errors.ConfigurationError

Options.OptionsContext.sub_options = Options.OptionsContext.recurse
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

