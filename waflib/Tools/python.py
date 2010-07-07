#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007-2010 (ita)
# Gustavo Carneiro (gjc), 2007

"Python support"

import os, sys
from waflib import TaskGen, Utils, Utils, Runner, Options, Build, Errors
from waflib.Logs import debug, warn, info
from waflib.TaskGen import extension, taskgen_method, before, after, feature
from waflib.Configure import conf

FRAG = '''
#ifdef __cplusplus
extern "C" {
#endif
	void Py_Initialize(void);
	void Py_Finalize(void);
#ifdef __cplusplus
}
#endif
int main()
{
   Py_Initialize();
   Py_Finalize();
   return 0;
}
'''

INST = '''
import sys, py_compile
for pyfile in sys.argv[1:]:
	py_compile.compile(pyfile, pyfile + %r)
'''

@extension('.py')
def process_py(self, node):
	try:
		if not self.bld.is_install:
			return
	except:
		return

	if not getattr(self, 'install_path', None):
		self.install_path = '${PYTHONDIR}'

	def inst_py(ctx):
		install_pyfile(self, node)
	self.bld.add_post_fun(inst_py)

def install_pyfile(self, node):
	tsk = self.bld.install_files(self.install_path, [node], postpone=False)
	path = os.path.join(tsk.get_install_path(), node.name)

	if self.bld.is_install < 0:
		info("+ removing byte compiled python files")
		for x in 'co':
			try:
				os.remove(path + x)
			except OSError:
				pass

	if self.bld.is_install > 0:
		if self.env['PYC'] or self.env['PYO']:
			info("+ byte compiling %r" % path)

		if self.env['PYC']:
			argv = [self.env['PYTHON'], '-c', INST % 'c', path]
			ret = Utils.subprocess.Popen(argv).wait()
			if ret:
				raise Errors.WafError('pyc compilation failed %r' % path)

		if self.env['PYO']:
			argv = [self.env['PYTHON'], self.env['PYFLAGS_OPT'], '-c', INST % 'o', path]
			ret = Utils.subprocess.Popen(argv).wait()
			if ret:
				raise Errors.WafError('pyo compilation failed %r' % path)

@feature('py')
def feature_py(self):
	pass

@feature('pyext')
@before('propagate_uselib_vars', 'apply_link')
def init_pyext(self):
	self.install_path = '${PYTHONDIR}'
	self.uselib = self.to_list(getattr(self, 'uselib', []))
	if not 'PYEXT' in self.uselib:
		self.uselib.append('PYEXT')
	# override shlib_PATTERN set by the osx module
	self.env['cshlib_PATTERN'] = self.env['cxxshlib_PATTERN'] = self.env['pyext_PATTERN']

@before('propagate_uselib_vars')
@feature('pyembed')
def init_pyembed(self):
	self.uselib = self.to_list(getattr(self, 'uselib', []))
	if not 'PYEMBED' in self.uselib:
		self.uselib.append('PYEMBED')

@conf
def get_python_variables(conf, python_exe, variables, imports=['import sys']):
	"""Run a python interpreter and print some variables"""
	program = list(imports)
	program.append('')
	for v in variables:
		program.append("print(repr(%s))" % v)
	os_env = dict(os.environ)
	try:
		del os_env['MACOSX_DEPLOYMENT_TARGET'] # see comments in the OSX tool
	except KeyError:
		pass

	out = conf.cmd_and_log([python_exe, '-c', '\n'.join(program)], env=os_env)
	return_values = []
	for s in out.split('\n'):
		s = s.strip()
		if not s:
			continue
		if s == 'None':
			return_values.append(None)
		elif s[0] == "'" and s[-1] == "'":
			return_values.append(s[1:-1])
		elif s[0].isdigit():
			return_values.append(int(s))
		else: break
	return return_values

@conf
def check_python_headers(conf):
	"""Check for headers and libraries necessary to extend or embed python.

	On success the environment variables xxx_PYEXT and xxx_PYEMBED are added for uselib

	PYEXT: for compiling python extensions
	PYEMBED: for embedding a python interpreter"""

	if not conf.env['CC_NAME'] and not conf.env['CXX_NAME']:
		conf.fatal('load a compiler first (gcc, g++, ..)')

	if not conf.env['PYTHON_VERSION']:
		conf.check_python_version()

	env = conf.env
	python = env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')

	## On Mac OSX we need to use mac bundles for python plugins
	if Options.platform == 'darwin':
		conf.check_tool('osx')

	try:
		# Get some python configuration variables using distutils
		v = 'prefix SO SYSLIBS LDFLAGS SHLIBS LIBDIR LIBPL INCLUDEPY Py_ENABLE_SHARED MACOSX_DEPLOYMENT_TARGET'.split()
		(python_prefix, python_SO, python_SYSLIBS, python_LDFLAGS, python_SHLIBS,
		 python_LIBDIR, python_LIBPL, INCLUDEPY, Py_ENABLE_SHARED,
		 python_MACOSX_DEPLOYMENT_TARGET) = \
			conf.get_python_variables(python, ["get_config_var('%s')" % x for x in v],
					      ['from distutils.sysconfig import get_config_var'])
	except RuntimeError:
		conf.fatal("Python development headers not found (-v for details).")

	conf.to_log("""Configuration returned from %r:
python_prefix = %r
python_SO = %r
python_SYSLIBS = %r
python_LDFLAGS = %r
python_SHLIBS = %r
python_LIBDIR = %r
python_LIBPL = %r
INCLUDEPY = %r
Py_ENABLE_SHARED = %r
MACOSX_DEPLOYMENT_TARGET = %r
""" % (python, python_prefix, python_SO, python_SYSLIBS, python_LDFLAGS, python_SHLIBS,
	python_LIBDIR, python_LIBPL, INCLUDEPY, Py_ENABLE_SHARED, python_MACOSX_DEPLOYMENT_TARGET))

	if python_MACOSX_DEPLOYMENT_TARGET:
		conf.env['MACOSX_DEPLOYMENT_TARGET'] = python_MACOSX_DEPLOYMENT_TARGET
		conf.environ['MACOSX_DEPLOYMENT_TARGET'] = python_MACOSX_DEPLOYMENT_TARGET

	env['pyext_PATTERN'] = '%s'+python_SO

	# Check for python libraries for embedding
	if python_SYSLIBS is not None:
		for lib in python_SYSLIBS.split():
			if lib.startswith('-l'):
				lib = lib[2:] # strip '-l'
			env.append_value('LIB_PYEMBED', [lib])
	if python_SHLIBS is not None:
		for lib in python_SHLIBS.split():
			if lib.startswith('-l'):
				lib = lib[2:] # strip '-l'
			env.append_value('LIB_PYEMBED', [lib])

	if Options.platform != 'darwin' and python_LDFLAGS:
		env.append_value('LINKFLAGS_PYEMBED', python_LDFLAGS.split())

	result = False
	name = 'python' + env['PYTHON_VERSION']

	if python_LIBDIR is not None:
		path = [python_LIBDIR]
		conf.to_log("\n\n# Trying LIBDIR: %r\n" % path)
		result = conf.check(lib=name, uselib='PYEMBED', libpath=path)

	if not result and python_LIBPL is not None:
		conf.to_log("\n\n# try again with -L$python_LIBPL (some systems don't install the python library in $prefix/lib)\n")
		path = [python_LIBPL]
		result = conf.check(lib=name, uselib='PYEMBED', libpath=path)

	if not result:
		conf.to_log("\n\n# try again with -L$prefix/libs, and pythonXY name rather than pythonX.Y (win32)\n")
		path = [os.path.join(python_prefix, "libs")]
		name = 'python' + env['PYTHON_VERSION'].replace('.', '')
		result = conf.check(lib=name, uselib='PYEMBED', libpath=path)

	if result:
		env['LIBPATH_PYEMBED'] = path
		env.append_value('LIB_PYEMBED', [name])
	else:
		conf.to_log("\n\n### LIB NOT FOUND\n")

	# under certain conditions, python extensions must link to
	# python libraries, not just python embedding programs.
	if (sys.platform == 'win32' or sys.platform.startswith('os2')
		or sys.platform == 'darwin' or Py_ENABLE_SHARED):
		env['LIBPATH_PYEXT'] = env['LIBPATH_PYEMBED']
		env['LIB_PYEXT'] = env['LIB_PYEMBED']

	# We check that pythonX.Y-config exists, and if it exists we
	# use it to get only the includes, else fall back to distutils.
	python_config = conf.find_program(
		'python%s-config' % ('.'.join(env['PYTHON_VERSION'].split('.')[:2])),
		var='PYTHON_CONFIG')
	if not python_config:
		python_config = conf.find_program(
			'python-config-%s' % ('.'.join(env['PYTHON_VERSION'].split('.')[:2])),
			var='PYTHON_CONFIG')

	includes = []
	if python_config:
		for incstr in conf.cmd_and_log("%s %s --includes" % (python, python_config)).strip().split():
			# strip the -I or /I
			if (incstr.startswith('-I') or incstr.startswith('/I')):
				incstr = incstr[2:]
			# append include path, unless already given
			if incstr not in includes:
				includes.append(incstr)
		conf.to_log("Include path for Python extensions "
			       "(found via python-config --includes): %r\n" % (includes,))
		env['INCLUDES_PYEXT'] = includes
		env['INCLUDES_PYEMBED'] = includes
	else:
		conf.to_log("Include path for Python extensions "
			       "(found via distutils module): %r\n" % (INCLUDEPY,))
		env['INCLUDES_PYEXT'] = [INCLUDEPY]
		env['INCLUDES_PYEMBED'] = [INCLUDEPY]

	# Code using the Python API needs to be compiled with -fno-strict-aliasing
	if env['CC_NAME'] == 'gcc':
		env.append_value('CCFLAGS_PYEMBED', ['-fno-strict-aliasing'])
		env.append_value('CCFLAGS_PYEXT', ['-fno-strict-aliasing'])
	if env['CXX_NAME'] == 'gcc':
		env.append_value('CXXFLAGS_PYEMBED', ['-fno-strict-aliasing'])
		env.append_value('CXXFLAGS_PYEXT', ['-fno-strict-aliasing'])

	# See if it compiles
	conf.check(header_name='Python.h', define_name='HAVE_PYTHON_H',
		   uselib='PYEMBED', fragment=FRAG,
		   errmsg='Could not find the python development headers')

@conf
def check_python_version(conf, minver=None):
	"""
	Check if the python interpreter is found matching a given minimum version.
	minver should be a tuple, eg. to check for python >= 2.4.2 pass (2,4,2) as minver.

	If successful, PYTHON_VERSION is defined as 'MAJOR.MINOR'
	(eg. '2.4') of the actual python version found, and PYTHONDIR is
	defined, pointing to the site-packages directory appropriate for
	this python version, where modules/packages/extensions should be
	installed.
	"""
	assert minver is None or isinstance(minver, tuple)
	python = conf.env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')

	# Get python version string
	cmd = [python, '-c', 'import sys\nfor x in sys.version_info: print(str(x))']
	debug('python: Running python command %r' % cmd)
	lines = conf.cmd_and_log(cmd).split()
	assert len(lines) == 5, "found %i lines, expected 5: %r" % (len(lines), lines)
	pyver_tuple = (int(lines[0]), int(lines[1]), int(lines[2]), lines[3], int(lines[4]))

	# compare python version with the minimum required
	result = (minver is None) or (pyver_tuple >= minver)

	if result:
		# define useful environment variables
		pyver = '.'.join([str(x) for x in pyver_tuple[:2]])
		conf.env['PYTHON_VERSION'] = pyver

		if 'PYTHONDIR' in conf.environ:
			pydir = conf.environ['PYTHONDIR']
		else:
			if sys.platform == 'win32':
				(python_LIBDEST, pydir) = \
						conf.get_python_variables(python,
											  ["get_config_var('LIBDEST')",
											   "get_python_lib(standard_lib=0, prefix=%r)" % conf.env['PREFIX']],
											  ['from distutils.sysconfig import get_config_var, get_python_lib'])
			else:
				python_LIBDEST = None
				(pydir,) = \
						conf.get_python_variables(python,
											  ["get_python_lib(standard_lib=0, prefix=%r)" % conf.env['PREFIX']],
											  ['from distutils.sysconfig import get_config_var, get_python_lib'])
			if python_LIBDEST is None:
				if conf.env['LIBDIR']:
					python_LIBDEST = os.path.join(conf.env['LIBDIR'], "python" + pyver)
				else:
					python_LIBDEST = os.path.join(conf.env['PREFIX'], "lib", "python" + pyver)

		if hasattr(conf, 'define'): # conf.define is added by the C tool, so may not exist
			conf.define('PYTHONDIR', pydir)
		conf.env['PYTHONDIR'] = pydir

	# Feedback
	pyver_full = '.'.join(map(str, pyver_tuple[:3]))
	if minver is None:
		conf.msg('Python version', pyver_full)
	else:
		minver_str = '.'.join(map(str, minver))
		conf.msg('Python version', result, ">= %s" % (minver_str,) and 'GREEN' or 'YELLOW')

	if not result:
		conf.fatal('The python version is too old (%r)' % minver)

@conf
def check_python_module(conf, module_name):
	"""
	Check if the selected python interpreter can import the given python module.
	"""
	conf.start_msg('Python module %s' % module_name)
	try:
		conf.cmd_and_log([conf.env['PYTHON'], '-c', 'import %s\nprint(1)\n' % module_name])
	except:
		conf.end_msg(False)
		conf.fatal('Could not find the python module %r' % module_name)
	conf.end_msg(True)

def configure(conf):

	if not conf.env.PYTHON:
		conf.env.PYTHON = sys.executable

	conf.find_program('python', var='PYTHON')

	v = conf.env
	v['PYCMD'] = '"import sys, py_compile;py_compile.compile(sys.argv[1], sys.argv[2])"'
	v['PYFLAGS'] = ''
	v['PYFLAGS_OPT'] = '-O'

	v['PYC'] = getattr(Options.options, 'pyc', 1)
	v['PYO'] = getattr(Options.options, 'pyo', 1)

def options(opt):
	opt.add_option('--nopyc',
			action='store_false',
			default=1,
			help = 'Do not install bytecode compiled .pyc files (configuration) [Default:install]',
			dest = 'pyc')
	opt.add_option('--nopyo',
			action='store_false',
			default=1,
			help='Do not install optimised compiled .pyo files (configuration) [Default:install]',
			dest='pyo')

