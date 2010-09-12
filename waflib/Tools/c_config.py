#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
c/c++ configuration routines
"""

import os, imp, sys, shlex, shutil
from waflib import Build, Utils, Configure, Task, Options, Logs, TaskGen, Errors, ConfigSet
from waflib.TaskGen import before, after, feature
from waflib.Configure import conf
from waflib.Utils import subprocess

WAF_CONFIG_H   = 'config.h'
"""default name for the config.h file"""

DEFKEYS = 'define_key'
INCKEYS = 'include_key'

cfg_ver = {
	'atleast-version': '>=',
	'exact-version': '==',
	'max-version': '<=',
}

SNIP_FUNCTION = '''
	int main() {
	void *p;
	p=(void*)(%s);
	return 0;
}
'''

SNIP_TYPE = '''
int main() {
	if ((%(type_name)s *) 0) return 0;
	if (sizeof (%(type_name)s)) return 0;
}
'''

SNIP_CLASS = '''
int main() {
	if (
}
'''

SNIP_EMPTY_PROGRAM = '''
int main() {
	return 0;
}
'''

SNIP_FIELD = '''
int main() {
	char *off;
	off = (char*) &((%(type_name)s*)0)->%(field_name)s;
	return (size_t) off < sizeof(%(type_name)s);
}
'''

@conf
def parse_flags(self, line, uselib, env=None):
	"""pkg-config still has bugs on some platforms, and there are many -config programs, parsing flags is necessary :-/"""

	assert(isinstance(line, str))

	env = env or self.env

	app = env.append_unique
	lst = shlex.split(line)
	while lst:
		x = lst.pop(0)
		st = x[:2]
		ot = x[2:]

		if st == '-I' or st == '/I':
			if not ot: ot = lst.pop(0)
			app('INCLUDES_' + uselib, [ot])
		elif st == '-D':
			if not ot: ot = lst.pop(0)
			app('DEFINES_' + uselib, [ot])
		elif st == '-l':
			if not ot: ot = lst.pop(0)
			app('LIB_' + uselib, [ot])
		elif st == '-L':
			if not ot: ot = lst.pop(0)
			app('LIBPATH_' + uselib, [ot])
		elif x == '-pthread' or x.startswith('+'):
			app('CCFLAGS_' + uselib, [x])
			app('CXXFLAGS_' + uselib, [x])
			app('LINKFLAGS_' + uselib, [x])
		elif x == '-framework':
			app('FRAMEWORK_' + uselib, [lst.pop(0)])
		elif x.startswith('-F'):
			app('FRAMEWORKPATH_' + uselib, [x[2:]])
		elif x.startswith('-std'):
			app('CCFLAGS_' + uselib, [x])
			app('CXXFLAGS_' + uselib, [x])
			app('LINKFLAGS_' + uselib, [x])
		elif x.startswith('-Wl'):
			app('LINKFLAGS_' + uselib, [x])
		elif x.startswith('-m') or x.startswith('-f'):
			app('CCFLAGS_' + uselib, [x])
			app('CXXFLAGS_' + uselib, [x])

@conf
def ret_msg(self, f, kw):
	"""execute a function, when provided"""
	if isinstance(f, str):
		return f
	return f(kw)

@conf
def validate_cfg(self, kw):

	if not 'path' in kw:
		if not self.env.PKGCONFIG:
			self.find_program('pkg-config', var='PKGCONFIG')
		kw['path'] = self.env.PKGCONFIG

	# pkg-config version
	if 'atleast_pkgconfig_version' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for pkg-config version >= %r' % kw['atleast_pkgconfig_version']
		return

	if not 'okmsg' in kw:
		kw['okmsg'] = 'yes'
	if not 'errmsg' in kw:
		kw['errmsg'] = 'not found'

	if 'modversion' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for %r version' % kw['modversion']
		return

	# checking for the version of a module, for the moment, one thing at a time
	for x in cfg_ver.keys():
		y = x.replace('-', '_')
		if y in kw:
			if not 'package' in kw:
				raise ValueError('%s requires a package' % x)

			if not 'msg' in kw:
				kw['msg'] = 'Checking for %r %s %s' % (kw['package'], cfg_ver[x], kw[y])
			return

	if not 'msg' in kw:
		kw['msg'] = 'Checking for %r' % (kw['package'] or kw['path'])

@conf
def exec_cfg(self, kw):

	# pkg-config version
	if 'atleast_pkgconfig_version' in kw:
		cmd = [kw['path'], '--atleast-pkgconfig-version=%s' % kw['atleast_pkgconfig_version']]
		self.cmd_and_log(cmd)
		if not 'okmsg' in kw:
			kw['okmsg'] = 'yes'
		return

	# checking for the version of a module
	for x in cfg_ver:
		y = x.replace('-', '_')
		if y in kw:
			self.cmd_and_log([kw['path'], '--%s=%s' % (x, kw[y]), kw['package']])
			if not 'okmsg' in kw:
				kw['okmsg'] = 'yes'
			self.define(self.have_define(kw.get('uselib_store', kw['package'])), 1, 0)
			break

	# retrieving the version of a module
	if 'modversion' in kw:
		version = self.cmd_and_log([kw['path'], '--modversion', kw['modversion']]).strip()
		self.define('%s_VERSION' % Utils.quote_define_name(kw.get('uselib_store', kw['modversion'])), version)
		return version

	# retrieving variables of a module
	if 'variables' in kw:
		env = kw.get('env', self.env)
		uselib = kw.get('uselib_store', kw['package'].upper())
		vars = Utils.to_list(kw['variables'])
		for v in vars:
			val = self.cmd_and_log('%s --variable=%s %s' % (kw['path'], v, kw['package']), kw).strip()
			var = '%s_%s' % (uselib, v)
			env[var] = val
		if not 'okmsg' in kw:
			kw['okmsg'] = 'yes'
		return

	lst = [kw['path']]


	defi = kw.get('define_variable', None)
	if not defi:
		defi = self.env.PKG_CONFIG_DEFINES or {}
	for key, val in defi.items():
		lst.append('--define-variable=%s=%s' % (key, val))

	if 'args' in kw:
		lst += Utils.to_list(kw['args'])
	if kw['package']:
		lst.extend(Utils.to_list(kw['package']))

	# so we assume the command-line will output flags to be parsed afterwards
	ret = self.cmd_and_log(lst)
	if not 'okmsg' in kw:
		kw['okmsg'] = 'yes'

	self.define(self.have_define(kw.get('uselib_store', kw['package'])), 1, 0)
	self.parse_flags(ret, kw.get('uselib_store', kw['package'].upper()), kw.get('env', self.env))
	return ret

@conf
def check_cfg(self, *k, **kw):

	if k:
		lst = k[0].split()
		kw['package'] = lst[0]
		kw['args'] = ' '.join(lst[1:])

	self.validate_cfg(kw)
	if 'msg' in kw:
		self.start_msg(kw['msg'])
	ret = None
	try:
		ret = self.exec_cfg(kw)
	except self.errors.WafError as e:
		if 'errmsg' in kw:
			self.end_msg(kw['errmsg'], 'YELLOW')
		if Logs.verbose > 1:
			raise
		else:
			self.fatal('The configuration failed')
	else:
		kw['success'] = ret
		if 'okmsg' in kw:
			self.end_msg(self.ret_msg(kw['okmsg'], kw))

	return ret

# the idea is the following: now that we are certain
# that all the code here is only for c or c++, it is
# easy to put all the logic in one function
#
# this should prevent code duplication (ita)

# env: an optional environment (modified -> provide a copy)
# compiler: cc or cxx - it tries to guess what is best
# type: program, shlib, stlib, objects
# code: a c code to execute
# uselib_store: where to add the variables
# uselib: parameters to use for building
# define: define to set, like FOO in #define FOO, if not set, add /* #undef FOO */
# execute: True or False - will return the result of the execution

@conf
def validate_c(self, kw):
	"""validate the parameters for the test method"""

	if not 'env' in kw:
		kw['env'] = self.env.derive()
	env = kw['env']

	if not 'compiler' in kw:
		kw['compiler'] = 'c'
		if env['CXX_NAME'] and Task.classes.get('cxx', None):
			kw['compiler'] = 'cxx'
			if not self.env['CXX']:
				self.fatal('a c++ compiler is required')
		else:
			if not self.env['CC']:
				self.fatal('a c compiler is required')

	if not 'compile_mode' in kw:
		kw['compile_mode'] = (kw['compiler'] == 'cxx') and 'cxx' or 'c'

	if not 'type' in kw:
		kw['type'] = 'cprogram'

	if not 'features' in kw:
		kw['features'] = [kw['compile_mode'], kw['type']] # "cprogram c"
	else:
		kw['features'] = Utils.to_list(kw['features'])

	if not 'compile_filename' in kw:
		kw['compile_filename'] = 'test.c' + ((kw['compile_mode'] == 'cxx') and 'pp' or '')


	def to_header(dct):
		if 'header_name' in dct:
			dct = Utils.to_list(dct['header_name'])
			return ''.join(['#include <%s>\n' % x for x in dct])
		return ''

	#OSX
	if 'framework_name' in kw:
		fwkname = kw['framework_name']
		if not 'uselib_store' in kw:
			kw['uselib_store'] = fwkname.upper()

		if not kw.get('no_header', False):
			if not 'header_name' in kw:
				kw['header_name'] = []
			fwk = '%s/%s.h' % (fwkname, fwkname)
			if kw.get('remove_dot_h', None):
				fwk = fwk[:-2]
			kw['header_name'] = Utils.to_list(kw['header_name']) + [fwk]

		kw['msg'] = 'Checking for framework %s' % fwkname
		kw['framework'] = fwkname
		#kw['frameworkpath'] = set it yourself

	if 'function_name' in kw:
		fu = kw['function_name']
		if not 'msg' in kw:
			kw['msg'] = 'Checking for function %s' % fu
		kw['code'] = to_header(kw) + SNIP_FUNCTION % fu
		if not 'uselib_store' in kw:
			kw['uselib_store'] = fu.upper()
		if not 'define_name' in kw:
			kw['define_name'] = self.have_define(fu)

	elif 'type_name' in kw:
		tu = kw['type_name']
		if not 'header_name' in kw:
			kw['header_name'] = 'stdint.h'
		if 'field_name' in kw:
			field = kw['field_name']
			kw['code'] = to_header(kw) + SNIP_FIELD % {'type_name' : tu, 'field_name' : field}
			if not 'msg' in kw:
				kw['msg'] = 'Checking for field %s in %s' % (field, tu)
			if not 'define_name' in kw:
				kw['define_name'] = self.have_define((tu + '_' + field).upper())
		else:
			kw['code'] = to_header(kw) + SNIP_TYPE % {'type_name' : tu}
			if not 'msg' in kw:
				kw['msg'] = 'Checking for type %s' % tu
			if not 'define_name' in kw:
				kw['define_name'] = self.have_define(tu.upper())

	elif 'header_name' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for header %s' % kw['header_name']

		l = Utils.to_list(kw['header_name'])
		assert len(l)>0, 'list of headers in header_name is empty'

		kw['code'] = to_header(kw) + SNIP_EMPTY_PROGRAM

		if not 'uselib_store' in kw:
			kw['uselib_store'] = l[0].upper()

		if not 'define_name' in kw:
			kw['define_name'] = self.have_define(l[0])

	if 'lib' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for library %s' % kw['lib']
		if not 'uselib_store' in kw:
			kw['uselib_store'] = kw['lib'].upper()

	if 'stlib' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for static library %s' % kw['stlib']
		if not 'uselib_store' in kw:
			kw['uselib_store'] = kw['stlib'].upper()

	if 'fragment' in kw:
		# an additional code fragment may be provided to replace the predefined code
		# in custom headers
		kw['code'] = kw['fragment']
		if not 'msg' in kw:
			kw['msg'] = 'Checking for code snippet'
		if not 'errmsg' in kw:
			kw['errmsg'] = 'no'

	for (flagsname,flagstype) in [('cxxflags','compiler'), ('cflags','compiler'), ('linkflags','linker')]:
		if flagsname in kw:
			if not 'msg' in kw:
				kw['msg'] = 'Checking for %s flags %s' % (flagstype, kw[flagsname])
			if not 'errmsg' in kw:
				kw['errmsg'] = 'no'

	if not 'execute' in kw:
		kw['execute'] = False
	if kw['execute']:
		kw['features'].append('test_exec')

	if not 'errmsg' in kw:
		kw['errmsg'] = 'not found'

	if not 'okmsg' in kw:
		kw['okmsg'] = 'yes'

	if not 'code' in kw:
		kw['code'] = SNIP_EMPTY_PROGRAM

	if not kw.get('success'): kw['success'] = None

	assert 'msg' in kw, 'invalid parameters, read http://freehackers.org/~tnagy/wafbook/single.html#config_helpers_c'

@conf
def post_check(self, *k, **kw):
	"set the variables after a test was run successfully"

	is_success = 0
	if kw['execute']:
		if kw['success'] is not None:
			if kw.get('define_ret', False):
				is_success = kw['success']
			else:
				is_success = (kw['success'] == 0)
	else:
		is_success = (kw['success'] == 0)

	def define_or_stuff():
		nm = kw['define_name']
		if kw['execute'] and kw.get('define_ret', None) and isinstance(is_success, str):
			self.define(kw['define_name'], is_success, quote=kw.get('quote', 1))
		else:
			self.define_cond(kw['define_name'], is_success)

	if 'define_name' in kw:
		if 'header_name' in kw or 'function_name' in kw or 'type_name' in kw or 'fragment' in kw:
			define_or_stuff()

	if is_success and 'uselib_store' in kw:
		from waflib.Tools import ccroot

		# TODO see get_uselib_vars from ccroot.py
		_vars = set([])
		for x in kw['features']:
			if x in ccroot.USELIB_VARS:
				_vars |= ccroot.USELIB_VARS[x]

		for k in _vars:
			lk = k.lower()
			if k == 'INCLUDES': lk = 'includes'
			if k == 'DEFINES': lk = 'defines'
			if lk in kw:
				val = kw[lk]
				# remove trailing slash
				if isinstance(val, str):
					val = val.rstrip(os.path.sep)
				self.env.append_unique(k + '_' + kw['uselib_store'], val)

@conf
def check(self, *k, **kw):
	# so this will be the generic function
	# it will be safer to use check_cxx or check_cc
	self.validate_c(kw)
	self.start_msg(kw['msg'])
	ret = None
	try:
		ret = self.run_c_code(*k, **kw)
	except self.errors.ConfigurationError as e:
		self.end_msg(kw['errmsg'], 'YELLOW')
		if Logs.verbose > 1:
			raise
		else:
			self.fatal('The configuration failed')
	else:
		kw['success'] = ret
		self.end_msg(self.ret_msg(kw['okmsg'], kw))

	self.post_check(*k, **kw)
	if not kw.get('execute', False):
		return ret == 0
	return ret

class test_exec_task(Task.Task):
	"""
	a task for executing a program after it is built
	"""
	color = 'PINK'
	def run(self):
		if getattr(self.generator, 'rpath', None):
			if getattr(self.generator, 'define_ret', False):
				self.generator.bld.retval = self.generator.bld.cmd_and_log([self.inputs[0].abspath()])
			else:
				self.generator.bld.retval = self.generator.bld.exec_command([self.inputs[0].abspath()])
		else:
			env = {}
			env.update(dict(os.environ))
			env['LD_LIBRARY_PATH'] = self.inputs[0].parent.abspath()
			if getattr(self.generator, 'define_ret', False):
				self.generator.bld.retval = self.generator.bld.cmd_and_log([self.inputs[0].abspath()], env=env)
			else:
				self.generator.bld.retval = self.generator.bld.exec_command([self.inputs[0].abspath()], env=env)

@feature('test_exec')
@after('apply_link')
def test_exec_fun(self):
	"""
	create a task that tries to execute the link task output
	used by conf.check(execute=1)
	"""
	self.create_task('test_exec', self.link_task.outputs[0])

CACHE_RESULTS = 1
COMPILE_ERRORS = 2

@conf
def run_c_code(self, *k, **kw):
	"""
	To use the cache in your scripts, provide the following option
	and execute  "waf configure --confcache"

	def options(opt):
		opt.add_option('--confcache', dest='confcache', default=0,
			action='count', help='Use a configuration cache')
	"""

	lst = [str(v) for (p, v) in kw.items() if p != 'env']
	h = Utils.h_list(lst)
	dir = self.bldnode.abspath() + os.sep + '.conf_check_' + Utils.to_hex(h)

	try:
		os.makedirs(dir)
	except:
		pass

	try:
		os.stat(dir)
	except:
		self.fatal('cannot use the configuration test folder %r' % dir)

	cachemode = getattr(Options.options, 'confcache', None)
	if cachemode == CACHE_RESULTS:
		try:
			proj = ConfigSet.ConfigSet(os.path.join(dir, 'cache_run_c_code'))
			return proj['cache_run_c_code']
		except:
			pass

	bdir = os.path.join(dir, 'testbuild')

	if not os.path.exists(bdir):
		os.makedirs(bdir)

	self.test_bld = bld = Build.BuildContext(top_dir=dir, out_dir=bdir) # keep the temporary build context on an attribute for debugging
	if cachemode == COMPILE_ERRORS:
		# TODO unlikely to be used, remove
		bld.load()
	else:
		bld.init_dirs()
	bld.progress_bar = 0
	bld.targets = '*'

	if kw['compile_filename']:
		node = bld.srcnode.make_node(kw['compile_filename'])
		node.write(kw['code'])

	bld.logger = self.logger
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default'] = kw['env']

	o = bld(features=kw['features'], source=kw['compile_filename'], target='testprog')

	for k, v in kw.items():
		setattr(o, k, v)

	self.to_log("==>\n%s\n<==" % kw['code'])

	# compile the program
	bld.targets = '*'

	ret = -1
	try:
		try:
			bld.compile()
		except Errors.WafError:
			self.fatal('Test does not build: %s' % Utils.ex_stack())
		else:
			ret = getattr(bld, 'retval', 0)
	finally:
		# cache the results each time
		proj = ConfigSet.ConfigSet()
		proj['cache_run_c_code'] = ret
		proj.store(os.path.join(dir, 'cache_run_c_code'))

	return ret

@conf
def check_cxx(self, *k, **kw):
	kw['compiler'] = 'cxx'
	return self.check(*k, **kw)

@conf
def check_cc(self, *k, **kw):
	kw['compiler'] = 'c'
	return self.check(*k, **kw)

@conf
def define(self, key, val, quote=True):
	"""
	store a single define and its state into a list
	the value can be a string or an int
	"""
	assert key and isinstance(key, str)

	if isinstance(val, int):
		s = '%s=%s'
	else:
		s = quote and '%s="%s"' or '%s=%s'
	app = s % (key, str(val))

	ban = key + '='
	lst = self.env['DEFINES']
	for x in lst:
		if x.startswith(ban):
			lst[lst.index(x)] = app
			break
	else:
		self.env.append_value('DEFINES', app)

	self.env.append_unique(DEFKEYS, key)

@conf
def undefine(self, key):
	"""
	remove a define
	"""
	assert key and isinstance(key, str)

	ban = key + '='
	lst = [x for x in self.env['DEFINES'] if not x.startswith(ban)]
	self.env['DEFINES'] = lst
	self.env.append_unique(DEFKEYS, key)

@conf
def define_cond(self, key, val):
	"""Conditionally define a name.
	Formally equivalent to: if val: define(name, 1) else: undefine(name)"""
	assert key and isinstance(key, str)

	if val:
		self.define(key, 1)
	else:
		self.undefine(key)

@conf
def is_defined(self, key):
	"is something defined?"
	assert key and isinstance(key, str)

	ban = key + '='
	for x in self.env['DEFINES']:
		if x.startswith(ban):
			return True
	return False

@conf
def get_define(self, key):
	"get the value of a previously stored define"
	assert key and isinstance(key, str)

	ban = key + '='
	for x in self.env['DEFINES']:
		if x.startswith(ban):
			return x[len(ban):]
	return None

@conf
def have_define(self, key):
	"prefix the define with 'HAVE_' and make sure it has valid characters."
	return self.__dict__.get('HAVE_PAT', 'HAVE_%s') % Utils.quote_define_name(key)

@conf
def write_config_header(self, configfile='', guard='', top=False, env=None, defines=True, headers=False, remove=True):
	"""
	save the defines into a file
	with configfile=foo/bar.h and a script in folder xyz
	top -> build/foo/bar.h
	!top -> build/xyz/foo/bar.h

	this method will reset the define keys and values
	"""
	if not configfile: configfile = WAF_CONFIG_H
	waf_guard = guard or '_%s_WAF' % Utils.quote_define_name(configfile)

	node = top and self.bldnode or self.path.get_bld()
	node = node.make_node(configfile)
	node.parent.mkdir()

	lst = ['/* WARNING! All changes made to this file will be lost! */\n']
	lst.append('#ifndef %s\n#define %s\n' % (waf_guard, waf_guard))
	lst.append(self.get_config_header(defines, headers))
	lst.append('\n#endif /* %s */\n' % waf_guard)

	node.write('\n'.join(lst))

	env = env or self.env

	# config files are not removed on "waf clean"
	env.append_unique(Build.CFG_FILES, [node.path_from(self.bldnode)])

	if remove:
		for key in self.env[DEFKEYS]:
			self.undefine(key)
		self.env[DEFKEYS] = []

@conf
def get_config_header(self, defines=True, headers=False):
	"""
	Create the contents of a config.h file from the accumulated includes and defines
	There is no include guard here

	Override this method when you need to write your own config header
	"""
	lst = []
	if headers:
		for x in self.env[INCKEYS]:
			lst.append('#include <%s>' % x)

	if defines:
		for x in self.env[DEFKEYS]:
			if self.is_defined(x):
				val = self.get_define(x)
				lst.append('#define %s %s' % (x, val))
			else:
				lst.append('/* #undef %s */' % x)
	return "\n".join(lst)

@conf
def cc_add_flags(conf):
	conf.add_os_flags('CFLAGS', 'CCFLAGS')

@conf
def cxx_add_flags(conf):
	conf.add_os_flags('CXXFLAGS')

@conf
def link_add_flags(conf):
	conf.add_os_flags('LINKFLAGS')
	conf.add_os_flags('LDFLAGS', 'LINKFLAGS')

@conf
def cc_load_tools(conf):
	conf.load('c')

@conf
def cxx_load_tools(conf):
	conf.load('cxx')

@conf
def get_cc_version(conf, cc, gcc=False, icc=False):
	"""get the compiler version"""
	cmd = cc + ['-dM', '-E', '-']
	try:
		p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.stdin.write(b'\n')
		out = p.communicate()[0]
	except:
		conf.fatal('could not determine the compiler version %r' % cmd)

	if not isinstance(out, str):
		out = out.decode('utf-8')

	if gcc:
		if out.find('__INTEL_COMPILER') >= 0:
			conf.fatal('The intel compiler pretends to be gcc')
		if out.find('__GNUC__') < 0:
			conf.fatal('Could not determine the compiler type')

	if icc and out.find('__INTEL_COMPILER') < 0:
		conf.fatal('Not icc/icpc')

	k = {}
	if icc or gcc:
		out = out.split('\n')
		import shlex

		for line in out:
			lst = shlex.split(line)
			if len(lst)>2:
				key = lst[1]
				val = lst[2]
				k[key] = val

		def isD(var):
			return var in k

		def isT(var):
			return var in k and k[var] != '0'

		# Some documentation is available at http://predef.sourceforge.net
		# The names given to DEST_OS must match what Utils.unversioned_sys_platform() returns.
		mp1 = {
			'__linux__'   : 'linux',
			'__GNU__'     : 'gnu',
			'__FreeBSD__' : 'freebsd',
			'__NetBSD__'  : 'netbsd',
			'__OpenBSD__' : 'openbsd',
			'__sun'       : 'sunos',
			'__hpux'      : 'hpux',
			'__sgi'       : 'irix',
			'_AIX'        : 'aix',
			'__CYGWIN__'  : 'cygwin',
			'__MSYS__'    : 'msys',
			'_UWIN'       : 'uwin',
			'_WIN64'      : 'win32',
			'_WIN32'      : 'win32',
			'__POWERPC__' : 'powerpc',
			}

		for i in mp1:
			if isD(i):
				conf.env.DEST_OS = mp1[i]
				break
		else:
			if isD('__APPLE__') and isD('__MACH__'):
				conf.env.DEST_OS = 'darwin'
			elif isD('__unix__'): # unix must be tested last as it's a generic fallback
				conf.env.DEST_OS = 'generic'

		if isD('__ELF__'):
			conf.env.DEST_BINFMT = 'elf'
		elif isD('__WINNT__') or isD('__CYGWIN__'):
			conf.env.DEST_BINFMT = 'pe'
			conf.env.LIBDIR = conf.env['PREFIX'] + '/bin'
		elif isD('__APPLE__'):
			conf.env.DEST_BINFMT = 'mac-o'

		if not conf.env.DEST_BINFMT:
			# Infer the binary format from the os name.
			conf.env.DEST_BINFMT = Utils.unversioned_sys_platform_to_binary_format(
				conf.env.DEST_OS or Utils.unversioned_sys_platform())

		mp2 = {
				'__x86_64__'  : 'x86_64',
				'__i386__'    : 'x86',
				'__ia64__'    : 'ia',
				'__mips__'    : 'mips',
				'__sparc__'   : 'sparc',
				'__alpha__'   : 'alpha',
				'__arm__'     : 'arm',
				'__hppa__'    : 'hppa',
				'__powerpc__' : 'powerpc',
				}
		for i in mp2:
			if isD(i):
				conf.env.DEST_CPU = mp2[i]
				break

		Logs.debug('ccroot: dest platform: ' + ' '.join([conf.env[x] or '?' for x in ('DEST_OS', 'DEST_BINFMT', 'DEST_CPU')]))
		conf.env['CC_VERSION'] = (k['__GNUC__'], k['__GNUC_MINOR__'], k['__GNUC_PATCHLEVEL__'])
	return k

# ============ the --as-needed flag should added during the configuration, not at runtime =========

@conf
def add_as_needed(self):
	if self.env.DEST_BINFMT == 'elf' and 'gcc' in (self.env.CXX_NAME, self.env.CC_NAME):
		self.env.append_unique('LINKFLAGS', '--as-needed')

