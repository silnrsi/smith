#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re
from waflib import TaskGen, Task, Utils, Logs, Build, Options, Node, Errors
from waflib.Logs import error, debug, warn
from waflib.TaskGen import after, before, feature, taskgen_method
from waflib.Tools import c_aliases, c_preproc, c_config, c_asm, c_objects, c_osx, c_tests

USELIB_VARS = Utils.defaultdict(set)
USELIB_VARS['c']   = set(['INCLUDES', 'FRAMEWORKPATH', 'DEFINES', 'CCDEPS', 'CCFLAGS'])
USELIB_VARS['cxx'] = set(['INCLUDES', 'FRAMEWORKPATH', 'DEFINES', 'CXXDEPS', 'CXXFLAGS'])
USELIB_VARS['d']   = set(['INCLUDES', 'DFLAGS'])

USELIB_VARS['cprogram'] = USELIB_VARS['cxxprogram'] = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'FRAMEWORK', 'FRAMEWORKPATH'])
USELIB_VARS['cshlib']   = USELIB_VARS['cxxshlib']   = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'FRAMEWORK', 'FRAMEWORKPATH'])
USELIB_VARS['cstlib']   = USELIB_VARS['cxxstlib']   = set(['ARFLAGS', 'LINKDEPS'])

USELIB_VARS['dprogram'] = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS'])
USELIB_VARS['dshlib']   = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS'])
USELIB_VARS['dstlib']   = set(['ARFLAGS', 'LINKDEPS'])

USELIB_VARS['go'] = set(['GOCFLAGS'])
USELIB_VARS['goprogram'] = set(['GOLFLAGS'])

# =================================================================================================

def scan(self):
	"scanner for c and c++ tasks, uses the python-based preprocessor from the module preproc.py (task method)"
	(nodes, names) = c_preproc.get_deps(self)
	if Logs.verbose:
		debug('deps: deps for %r: %r; unresolved %r' % (self.inputs, nodes, names))
	return (nodes, names)

@taskgen_method
def create_compiled_task(self, name, node):
	"""
	creates the compilation task: c, cxx, asm, ...
	the task is appended to the list 'compiled_tasks' which is used by
	'apply_link'
	"""
	out = '%s.%d.o' % (node.name, self.idx)
	task = self.create_task(name, node, node.parent.find_or_declare(out))
	try:
		self.compiled_tasks.append(task)
	except AttributeError:
		self.compiled_tasks = [task]
	return task

@taskgen_method
def get_dest_binfmt(self):
	# The only thing we need for cross-compilation is DEST_BINFMT.
	# At some point, we may reach a case where DEST_BINFMT is not enough, but for now it's sufficient.
	# Currently, cross-compilation is auto-detected only for the gnu and intel compilers.
	if not self.env.DEST_BINFMT:
		# Infer the binary format from the os name.
		self.env.DEST_BINFMT = Utils.unversioned_sys_platform_to_binary_format(
			self.env.DEST_OS or Utils.unversioned_sys_platform())
	return self.env.DEST_BINFMT

@feature('c', 'cxx', 'd', 'go', 'asm', 'fc', 'includes')
@after('propagate_uselib_vars', 'process_source')
def apply_incpaths(self):
	"""used by the scanner
	after processing the uselib for INCLUDES
	after process_source because some processing may add include paths
	"""

	paths = self.to_list(getattr(self, 'includes', [])) + self.env['INCLUDES']

	lst = []
	seen = set([])
	for path in paths:

		if path in seen:
			continue
		seen.add(path)

		if isinstance(path, Node.Node):
			lst.append(path)
		else:
			if os.path.isabs(path):
				lst.append(self.bld.root.make_node(path))
			else:
				if path[0] == '#':
					lst.append(self.bld.bldnode.make_node(path[1:]))
					lst.append(self.bld.srcnode.make_node(path[1:]))
				else:
					lst.append(self.path.get_bld().make_node(path))
					lst.append(self.path.make_node(path))

	self.includes_nodes = lst
	self.env['INCPATHS'] = [x.abspath() for x in lst]

class link_task(Task.Task):
	color   = 'YELLOW'
	inst_to = None
	chmod   = Utils.O644

	def add_target(self, target):
		if isinstance(target, str):
			pattern = self.env[self.__class__.__name__ + '_PATTERN']
			if not pattern:
				pattern = '%s'
			folder, name = os.path.split(target)

			if self.__class__.__name__.find('shlib') > 0:
				if self.generator.get_dest_binfmt() == 'pe' and getattr(self.generator, 'vnum', None):
					# include the version in the dll file name,
					# the import lib file name stays unversionned.
					name = name + '-' + self.generator.vnum.split('.')[0]

			tmp = folder + os.sep + pattern % name
			target = self.generator.path.find_or_declare(tmp)
		self.set_outputs(target)

class stlink_task(link_task):
	run_str = '${AR} ${ARFLAGS} ${AR_TGT_F}${TGT} ${AR_SRC_F}${SRC}'
	def run(self):
		"""remove the file before creating it (ar behaviour is to append to the existin file)"""
		try:
			os.remove(self.outputs[0].abspath())
		except OSError:
			pass
		return Task.Task.run(self)

@feature('c', 'cxx', 'd', 'go', 'fc')
@after('process_source')
def apply_link(self):
	"""executes after process_source for collecting 'compiled_tasks' and creating a 'link_task'"""

	for x in self.features:
		if x == 'cprogram' and 'cxx' in self.features: # limited compat
			x = 'cxxprogram'
		elif x == 'cshlib' and 'cxx' in self.features:
			x = 'cxxshlib'

		if x in Task.classes:
			if hasattr(Task.classes[x], 'inst_to'):
				link = x
				break
	else:
		return

	objs = [t.outputs[0] for t in getattr(self, 'compiled_tasks', [])]
	self.link_task = self.create_task(link, objs)
	self.link_task.add_target(self.target)

	if getattr(self.bld, 'is_install', None):
		# remember that the install paths are given by the task generators
		try:
			inst_to = self.install_path
		except AttributeError:
			inst_to = self.link_task.__class__.inst_to
		if inst_to:
			self.install_task = self.bld.install_files(inst_to, self.link_task.outputs, env=self.env, chmod=self.link_task.chmod)

@feature('c', 'cxx', 'd')
@before('apply_incpaths')
@after('apply_link')
def apply_uselib_local(self):
	"""
	process the uselib_local attribute
	execute after apply_link because of the execution order set on 'link_task'
	"""
	env = self.env

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
				try:
					if not isinstance(obj.link_task, stlink_task):
						tmp.append(x)
				except AttributeError:
					Logs.warn('task generator %s has no link task' % x)

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
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

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

@taskgen_method
def get_uselib_vars(self):
	_vars = set([])
	for x in self.features:
		if x in USELIB_VARS:
			_vars |= USELIB_VARS[x]
	return _vars

@feature('c', 'cxx', 'd', 'fc', 'cs', 'uselib')
@after('apply_uselib_local')
def propagate_uselib_vars(self):
	_vars = self.get_uselib_vars()
	env = self.env

	# 1. add the attributes defined in a lowercase manner such as obj.cxxflags
	for x in _vars:

		# TODO for debugging, detect the invalid variables such as ldflags, ccflag, header, etc (plurals, capitalization, ...)
		y = x.lower()
		env.append_unique(x, self.to_list(getattr(self, y, [])))

	# 2. each compiler defines variables like 'CXXFLAGS_cshlib', 'LINKFLAGS_cshlib', etc
	# so when we make a task generator of the type cshlib, CXXFLAGS are modified accordingly
	# the order was reversed compared to waf 1.5: cshlib_LINKFLAGS -> LINKFLAGS_cshlib
	for x in self.features:
		for var in _vars:
			compvar = '%s_%s' % (var, x)
			env.append_value(var, env[compvar])

	# 3. the case of the libs defined outside
	for x in self.to_list(getattr(self, 'uselib', [])):
		for v in _vars:
			env.append_value(v, env[v + '_' + x])

# ============ the code above must not know anything about import libs ==========

@feature('cshlib', 'cxxshlib')
@after('apply_link')
@before('apply_lib_vars', 'apply_objdeps')
def apply_implib(self):
	"""On mswindows, handle dlls and their import libs
	the .dll.a is the import lib and it is required for linking so it is installed too
	"""
	if not self.get_dest_binfmt() == 'pe':
		return

	dll = self.link_task.outputs[0]
	implib = self.env['implib_PATTERN'] % os.path.split(self.target)[1]
	implib = dll.parent.find_or_declare(implib)
	self.env.append_value('LINKFLAGS', (self.env['IMPLIB_ST'] % implib.bldpath()).split())
	self.link_task.outputs.append(implib)

	if getattr(self, 'defs', None):
		node = self.path.find_resource(self.defs)
		if not node:
			raise Errors.WafError('invalid def file %r' % self.defs)
		self.env.append_value('LINKFLAGS', '/defs:%s' % node.abspath())

	try:
		inst_to = self.install_path
	except AttributeError:
		inst_to = self.link_task.__class__.inst_to
	if not inst_to:
		return

	self.implib_install_task = self.bld.install_as('${LIBDIR}/%s' % implib.name, implib, self.env)

# ============ the code above must not know anything about vnum processing on unix platforms =========

@feature('cshlib', 'cxxshlib', 'dshlib', 'vnum')
@after('apply_link')
def apply_vnum(self):
	"""
	libfoo.so is installed as libfoo.so.1.2.3
	create symlinks libfoo.so → libfoo.so.1.2.3 and libfoo.so.1 → libfoo.so.1.2.3
	"""
	if not getattr(self, 'vnum', '') or not 'cshlib' in self.features or os.name != 'posix' or self.get_dest_binfmt() not in ('elf', 'mac-o'):
		return

	link = self.link_task
	nums = self.vnum.split('.')
	node = link.outputs[0]

	libname = node.name
	if libname.endswith('.dylib'):
		name3 = libname.replace('.dylib', '.%s.dylib' % self.vnum)
		name2 = libname.replace('.dylib', '.%s.dylib' % nums[0])
	else:
		name3 = libname + '.' + self.vnum
		name2 = libname + '.' + nums[0]

	# add the so name for the ld linker - to disable, just unset env.SONAME_ST
	if self.env.SONAME_ST:
		v = self.env.SONAME_ST % name2
		self.env.append_value('LINKFLAGS', v.split())

	if not getattr(self.bld, 'is_install', None):
		return

	path = getattr(self, 'install_path', None)
	if not path:
		return

	# the following task is just to enable execution from the build dir :-/
	tsk = self.create_task('vnum')
	tsk.set_inputs([node])
	tsk.set_outputs(node.parent.find_or_declare(name2))

	self.install_task.hasrun = Task.SKIP_ME
	bld = self.bld
	t1 = bld.install_as(path + os.sep + name3, node, env=self.env)
	t2 = bld.symlink_as(path + os.sep + name2, name3)
	t3 = bld.symlink_as(path + os.sep + libname, name3)
	self.vnum_install_task = (t1, t2, t3)

class vnum_task(Task.Task):
	color = 'CYAN'
	quient = True
	ext_in = ['.bin']
	def run(self):
		path = self.outputs[0].abspath()
		try:
			os.remove(path)
		except OSError:
			pass

		try:
			os.symlink(self.inputs[0].name, path)
		except OSError:
			return 1

