#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

"""
fortran configuration helpers
"""

import re, shutil, os, sys, string, shlex
from waflib.Configure import conf
from waflib.TaskGen import feature, after, before
from waflib import Build, Utils
from waflib.Utils import subprocess

FC_FRAGMENT = '        program main\n        end     program main\n'
FC_FRAGMENT2 = '        PROGRAM MAIN\n        END\n' # what's the actual difference between these?

@conf
def fc_flags(conf):
	v = conf.env

	v['FC_SRC_F']    = ''
	v['FC_TGT_F']    = ['-c', '-o', '']
	v['FCINCPATH_ST']  = '-I%s'
	v['FCDEFINES_ST']  = '-D%s'

	if not v['LINK_FC']: v['LINK_FC'] = v['FC']
	v['FCLNK_SRC_F'] = ''
	v['FCLNK_TGT_F'] = ['-o', '']

	v['FCFLAGS_fcshlib']   = ['-fpic']
	v['LINKFLAGS_fcshlib'] = ['-shared']
	v['fcshlib_PATTERN']   = 'lib%s.so'

	v['fcstlib_PATTERN']   = 'lib%s.a'

	v['FCLIB_ST']       = '-l%s'
	v['FCLIBPATH_ST']   = '-L%s'
	v['FCSTLIB_ST']     = '-l%s'
	v['FCSTLIBPATH_ST'] = '-L%s'
	v['FCSTLIB_MARKER'] = '-Wl,-Bstatic'
	v['FCSHLIB_MARKER'] = '-Wl,-Bdynamic'

	v['SONAME_ST']           = '-Wl,-h,%s'

@conf
def check_fortran(self, *k, **kw):
	"""see if the compiler works by compiling a fragment"""
	self.check_cc(
		fragment         = FC_FRAGMENT,
		compile_filename = 'test.f',
		features         = 'fc fcprogram',
		msg              = 'Compiling a simple fortran app')

# ------------------------------------------------------------------------

@conf
def check_fortran_dummy_main(self, *k, **kw):
	"""
	Guess if a main function is needed by compiling a code snippet with
	the C compiler and link with the Fortran compiler

	TODO: (DC)
	- handling dialects (F77, F90, etc... -> needs core support first)
	- fix dummy main check (AC_FC_DUMMY_MAIN vs AC_FC_MAIN)

	TODO: what does the above mean? (ita)
	"""

	if not self.env.CC:
		self.fatal('A c compiler is required for check_fortran_dummy_main')

	lst = ['MAIN__', '__MAIN', '_MAIN', 'MAIN_', 'MAIN']
	lst.extend([m.lower() for m in lst])
	lst.append('')

	self.start_msg('Detecting whether we need a dummy main')
	for main in lst:
		kw['fortran_main'] = main
		try:
			self.check_cc(
				fragment = 'int %s() { return 0; }\n' % (main or 'test'),
				features = 'c fcprogram',
				mandatory = True
			)
			if not main:
				self.env.FC_MAIN = -1
				self.end_msg('no')
			else:
				self.env.FC_MAIN = main
				self.end_msg('yes %s' % main)
			break
		except self.errors.ConfigurationError:
			pass
	else:
		self.end_msg('not found')
		self.fatal('could not detect whether fortran requires a dummy main, see the config.log')

# ------------------------------------------------------------------------

GCC_DRIVER_LINE = re.compile('^Driving:')
POSIX_STATIC_EXT = re.compile('\S+\.a')
POSIX_LIB_FLAGS = re.compile('-l\S+')

@conf
def is_link_verbose(self, txt):
	"""Return True if 'useful' link options can be found in txt"""
	if sys.platform == 'win32':
		raise NotImplementedError("FIXME: not implemented on win32")

	assert isinstance(txt, str)
	for line in txt.splitlines():
		if not GCC_DRIVER_LINE.search(line):
			if POSIX_STATIC_EXT.search(line) or POSIX_LIB_FLAGS.search(line):
				return True
	return False

@conf
def check_fortran_verbose_flag(self, *k, **kw):
	"""
	check what kind of -v flag works, then set it to env.FC_VERBOSE_FLAG
	"""
	self.start_msg('fortran link verbose flag')
	for x in ['-v', '--verbose', '-verbose', '-V']:
		try:
			self.check_cc(
				features = 'fc fcprogram_test',
				fragment = FC_FRAGMENT2,
				compile_filename = 'test.f',
				linkflags = [x],
				mandatory=True
				)
		except self.errors.ConfigurationError:
			pass
		else:
			# output is on stderr
			if self.is_link_verbose(self.test_bld.err):
				self.end_msg(x)
				break
	else:
		self.end_msg('failure')
		self.fatal('Could not obtain the fortran link verbose flag (see config.log)')

	self.env.FC_VERBOSE_FLAG = x
	return x

# ------------------------------------------------------------------------

# linkflags which match those are ignored
LINKFLAGS_IGNORED = [r'-lang*', r'-lcrt[a-zA-Z0-9]*\.o', r'-lc$', r'-lSystem', r'-libmil', r'-LIST:*', r'-LNO:*']
if os.name == 'nt':
	LINKFLAGS_IGNORED.extend([r'-lfrt*', r'-luser32', r'-lkernel32', r'-ladvapi32', r'-lmsvcrt', r'-lshell32', r'-lmingw', r'-lmoldname'])
else:
	LINKFLAGS_IGNORED.append(r'-lgcc*')
RLINKFLAGS_IGNORED = [re.compile(f) for f in LINKFLAGS_IGNORED]

def _match_ignore(line):
	"""True if the line should be ignored."""
	for i in RLINKFLAGS_IGNORED:
		if i.match(line):
			return True
	return False

def parse_fortran_link(lines):
	"""Given the output of verbose link of Fortran compiler, this returns a
	list of flags necessary for linking using the standard linker."""
	# TODO: On windows ?
	final_flags = []
	for line in lines:
		if not GCC_DRIVER_LINE.match(line):
			_parse_flink_line(line, final_flags)
	return final_flags

SPACE_OPTS = re.compile('^-[LRuYz]$')
NOSPACE_OPTS = re.compile('^-[RL]')

def _parse_flink_line(line, final_flags):
	"""private"""
	lexer = shlex.shlex(line, posix = True)
	lexer.whitespace_split = True

	t = lexer.get_token()
	tmp_flags = []
	while t:
		def parse(token):
			# Here we go (convention for wildcard is shell, not regex !)
			#   1 TODO: we first get some root .a libraries
			#   2 TODO: take everything starting by -bI:*
			#   3 Ignore the following flags: -lang* | -lcrt*.o | -lc |
			#   -lgcc* | -lSystem | -libmil | -LANG:=* | -LIST:* | -LNO:*)
			#   4 take into account -lkernel32
			#   5 For options of the kind -[[LRuYz]], as they take one argument
			#   after, the actual option is the next token
			#   6 For -YP,*: take and replace by -Larg where arg is the old
			#   argument
			#   7 For -[lLR]*: take

			# step 3
			if _match_ignore(token):
				pass
			# step 4
			elif token.startswith('-lkernel32') and sys.platform == 'cygwin':
				tmp_flags.append(token)
			# step 5
			elif SPACE_OPTS.match(token):
				t = lexer.get_token()
				if t.startswith('P,'):
					t = t[2:]
				for opt in t.split(os.pathsep):
					tmp_flags.append('-L%s' % opt)
			# step 6
			elif NOSPACE_OPTS.match(token):
				tmp_flags.append(token)
			# step 7
			elif POSIX_LIB_FLAGS.match(token):
				tmp_flags.append(token)
			else:
				# ignore anything not explicitely taken into account
				pass

			t = lexer.get_token()
			return t
		t = parse(t)

	final_flags.extend(tmp_flags)
	return final_flags

@conf
def check_fortran_clib(self, autoadd=True, *k, **kw):
	"""
	Obtain flags for linking with the c library
	if this check works, add uselib='CLIB' to your task generators
	"""
	if not self.env.FC_VERBOSE_FLAG:
		self.fatal('env.FC_VERBOSE_FLAG is not set: execute check_fortran_verbose_flag?')

	self.start_msg('Getting fortran runtime link flags')
	try:
		self.check_cc(
			fragment = FC_FRAGMENT2,
			compile_filename = 'test.f',
			features = 'fc fcprogram_test',
			linkflags = [self.env.FC_VERBOSE_FLAG]
		)
	except:
		self.end_msg(False)
		if kw.get('mandatory', True):
			conf.fatal('Could not find the c library flags')
	else:
		out = self.test_bld.err
		flags = parse_fortran_link(out.splitlines())
		self.end_msg('ok (%s)' % ' '.join(flags))
		self.env.CLIB_LINKFLAGS = flags
		return flags
	return []

@conf
def get_fc_version(conf, fc, gfortran=False, g95=False, ifort=False):
	"""get the compiler version"""

	def getoutput(cmd, stdin=False):
		try:
			if stdin:
				stdin = subprocess.PIPE
			else:
				stdin = None
			p = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			if stdin:
				p.stdin.write(b'\n')
			stdout, stderr = p.communicate()
		except:
			conf.fatal('could not determine the compiler version %r' % cmd)
		else:
			if not isinstance(stdout, str):
				stdout = stdout.decode('utf-8')
			if not isinstance(stderr, str):
				stderr = stderr.decode('utf-8')
			return stdout, stderr

	if ifort:
		version_re = re.compile(r"Version\s*(?P<major>\d*)\.(?P<minor>\d*)", re.I).search
		cmd = fc + ['-logo']
		out, err = getoutput(cmd, stdin=False)
		if out:
			match = version_re(out)
		else:
			match = version_re(err)
		if not match:
			conf.fatal('cannot determine ifort version.')
		k = match.groupdict()
		conf.env['FC_VERSION'] = (k['major'], k['minor'])
		return

	elif g95:
		version_re = re.compile(r"g95\s*(?P<major>\d*)\.(?P<minor>\d*)").search
		cmd = fc + ['-dumpversion']
		out, err = getoutput(cmd, stdin=False)
		if out:
			match = version_re(out)
		else:
			match = version_re(err)
		if not match:
			conf.fatal('cannot determine g95 version')
		k = match.groupdict()
		conf.env['FC_VERSION'] = (k['major'], k['minor'])
		return

	elif gfortran:
		cmd = fc + ['-dM', '-E', '-']
		out, err = getoutput(cmd, stdin=True)

		if out.find('__GNUC__') < 0:
			conf.fatal('Could not determine the compiler type')

		k = {}
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

		conf.env['FC_VERSION'] = (k['__GNUC__'], k['__GNUC_MINOR__'], k['__GNUC_PATCHLEVEL__'])

# ------------------------------------------------------------------------

ROUTINES_CODE = """\
      subroutine foobar()
      return
      end
      subroutine foo_bar()
      return
      end
"""

MAIN_CODE = """
void %(dummy_func_nounder)s(void);
void %(dummy_func_under)s(void);
int %(main_func_name)s() {
  %(dummy_func_nounder)s();
  %(dummy_func_under)s();
  return 0;
}
"""

@feature('link_main_routines_func')
@before('process_source')
def link_main_routines_tg_method(self):
	"""
	the configuration test declares a unique task generator,
	so we create other task generators from there
	"""
	def write_test_file(task):
		task.outputs[0].write(task.generator.code)
	bld = self.bld
	bld(rule=write_test_file, target='main.c', code=MAIN_CODE % self.__dict__)
	bld(rule=write_test_file, target='test.f', code=ROUTINES_CODE)
	bld(features='fc fcstlib', source='test.f', target='test')
	bld(features='c fcprogram', source='main.c', target='app', use='test')

def mangling_schemes():
	"""
	generate triplets for use with mangle_name
	(used in check_fortran_mangling)
	the order is tuned for gfortan
	"""
	for u in ['_', '']:
		for du in ['', '_']:
			for c in ["lower", "upper"]:
				yield (u, du, c)

def mangle_name(u, du, c, name):
	"""mangle a name from a triplet (used in check_fortran_mangling)"""
	return getattr(name, c)() + u + (name.find('_') != -1 and du or '')

@conf
def check_fortran_mangling(self, *k, **kw):
	"""
	detect the mangling scheme, sets FORTRAN_MANGLING to the triplet found

	compile a fortran static library, then link a c app against it
	"""
	if not self.env.CC:
		self.fatal('A c compiler is required for link_main_routines')
	if not self.env.FC:
		self.fatal('A fortran compiler is required for link_main_routines')
	if not self.env.FC_MAIN:
		self.fatal('Checking for mangling requires self.env.FC_MAIN (execute "check_fortran_dummy_main" first?)')

	self.start_msg('Getting fortran mangling scheme')
	for (u, du, c) in mangling_schemes():
		try:
			self.check_cc(
				compile_filename = [],
				features         = 'link_main_routines_func',
				msg = 'nomsg',
				errmsg = 'nomsg',
				mandatory=True,
				dummy_func_nounder = mangle_name(u, du, c, "foobar"),
				dummy_func_under   = mangle_name(u, du, c, "foo_bar"),
				main_func_name     = self.env.FC_MAIN
			)
		except self.errors.ConfigurationError:
			pass
		else:
			self.end_msg("ok ('%s', '%s', '%s-case')" % (u, du, c))
			self.env.FORTRAN_MANGLING = (u, du, c)
			break
	else:
		self.end_msg(False)
		self.fatal('mangler not found')

	return (u, du, c)

