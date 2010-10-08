#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

USELIB_VARS = Utils.defaultdict(set)
USELIB_VARS['c']   = set(['INCLUDES', 'FRAMEWORKPATH', 'DEFINES', 'CCDEPS', 'CCFLAGS'])
USELIB_VARS['cxx'] = set(['INCLUDES', 'FRAMEWORKPATH', 'DEFINES', 'CXXDEPS', 'CXXFLAGS'])

USELIB_VARS['cprogram'] = USELIB_VARS['cxxprogram'] = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'FRAMEWORK', 'FRAMEWORKPATH'])
USELIB_VARS['cshlib']   = USELIB_VARS['cxxshlib']   = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS', 'FRAMEWORK', 'FRAMEWORKPATH'])
USELIB_VARS['cstlib']   = USELIB_VARS['cxxstlib']   = set(['ARFLAGS', 'LINKDEPS'])

@taskgen_method
def use_rec(self, name, objects=True, stlib=True):
	"""
	process the use keyword, recursively
	"""
	if name in self.seen_libs:
		return
	else:
		self.seen_libs.add(name)

	get = self.bld.get_tgen_by_name
	try:
		y = get(name)
	except Errors.WafError:
		self.uselib.append(name)
		return

	y.post()
	has_link = getattr(y, 'link_task', None)
	is_static = has_link and isinstance(y.link_task, stlink_task)

	# depth-first processing
	for x in self.to_list(getattr(y, 'use', [])):
		self.use_rec(x, objects and not has_link, stlib and (is_static or not has_link))

	# link task and flags
	if getattr(self, 'link_task', None):
		if has_link:
			if (not is_static) or (is_static and stlib):
				var = isinstance(y.link_task, stlink_task) and 'STLIB' or 'LIB'
				self.env.append_value(var, [y.target[y.target.rfind(os.sep) + 1:]])

				# the order
				self.link_task.set_run_after(y.link_task)

				# for the recompilation
				self.link_task.dep_nodes.extend(y.link_task.outputs)

				# add the link path too
				tmp_path = y.link_task.outputs[0].parent.bldpath()
				if not tmp_path in self.env[var + 'PATH']:
					self.env.prepend_value(var + 'PATH', [tmp_path])
		elif objects:
			for t in getattr(y, 'compiled_tasks', []):
				self.link_task.inputs.extend(t.outputs)

	# add ancestors uselib too - but only propagate those that have no staticlib defined
	for v in self.to_list(getattr(y, 'uselib', [])):
		if not self.env['STLIB_' + v]:
			if not v in self.uselib:
				self.uselib.insert(0, v)

	# if the library task generator provides 'export_incdirs', add to the include path
	# the export_incdirs must be a list of paths relative to the other library
	if getattr(y, 'export_includes', None):
		self.includes.extend(y.to_incnodes(y.export_includes))

@feature('c', 'cxx', 'd', 'use', 'fc')
@before('apply_incpaths', 'propagate_uselib_vars')
@after('apply_link', 'process_source')
def process_use(self):
	"""
	process the 'use' attribute which is like uselib+uselib_local+add_objects
	execute after apply_link because of the execution order must be set on 'link_task'

	propagation rules:
	a static library is found -> propagation on anything stops
	a shared library (non-static) is found -> propagation continues, but objects are not added
	"""

	self.uselib = self.to_list(getattr(self, 'uselib', []))
	self.includes = self.to_list(getattr(self, 'includes', []))
	names = self.to_list(getattr(self, 'use', []))
	self.seen_libs = set([])

	for x in names:
		self.use_rec(x)

@taskgen_method
def get_uselib_vars(self):
	"helper function"
	_vars = set([])
	for x in self.features:
		if x in USELIB_VARS:
			_vars |= USELIB_VARS[x]
	return _vars

@feature('c', 'cxx', 'd', 'fc', 'cs', 'uselib')
@after('process_use')
def propagate_uselib_vars(self):
	"""process uselib variables for adding flags"""
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


