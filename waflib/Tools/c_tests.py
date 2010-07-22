#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
configuration tests...
"""

from waflib.Configure import conf
from waflib.TaskGen import feature, before

LIB_CODE = '''
#ifdef _MSC_VER
#define testEXPORT __declspec(dllexport)
#else
#define testEXPORT
#endif
testEXPORT int lib_func(void) { return 9; }
'''

MAIN_CODE = '''
#ifdef _MSC_VER
#define testEXPORT __declspec(dllimport)
#else
#define testEXPORT
#endif
testEXPORT int lib_func(void);
int main(void) {return !(lib_func() == 9);}
'''

@feature('link_lib_test')
@before('process_source')
def link_lib_test_fun(self):
	"""
	the configuration test declares a unique task generator,
	so we create other task generators from there
	"""
	def write_test_file(task):
		task.outputs[0].write(task.generator.code)

	rpath = []
	if getattr(self, 'add_rpath', False):
		rpath = [self.bld.path.get_bld().abspath()]

	mode = self.mode
	m = '%s %s' % (mode, mode)
	bld = self.bld
	bld(rule=write_test_file, target='test.c', code=LIB_CODE)
	bld(rule=write_test_file, target='main.c', code=MAIN_CODE)
	bld(features= m + 'shlib', source='test.c', target='test')
	bld(features= m + 'program test_exec', source='main.c', target='app', uselib_local='test', rpath=rpath)

@conf
def check_library(self, mode=None):
	"""
	see if the platform supports building libraries
	"""
	if not mode:
		mode = 'c'
		if self.env.CXX:
			mode = 'cxx'
	self.check(
		compile_filename = [],
		features = 'link_lib_test',
		msg = 'Checking for libraries',
		mode = mode
		)

########################################################################################

INLINE_CODE = '''
typedef int foo_t;
static %s foo_t static_foo () {return 0; }
%s foo_t foo () {
	return 0;
}
'''
INLINE_VALUES = ['inline', '__inline__', '__inline']

@conf
def check_inline(self, **kw):
	"""
	check for the right value for inline
	define INLINE_MACRO to 1 if the define is found
	if the inline macro is not 'inline', add a define for the config.h (#define inline __inline__)
	"""

	self.start_msg('Checking for inline')

	if not 'define_name' in kw:
		kw['define_name'] = 'INLINE_MACRO'
	if not 'features' in kw:
		if self.env.CXX:
			kw['features'] = ['cxx']
		else:
			kw['features'] = ['c']

	for x in INLINE_VALUES:
		kw['fragment'] = INLINE_CODE % (x, x)

		try:
			self.check(**kw)
		except self.errors.ConfigurationError:
			continue
		else:
			self.end_msg(x)
			if x != 'inline':
				self.define('inline', i, quote=False)
			return x
	self.fatal('could not use inline functions')

########################################################################################

LARGE_FRAGMENT = '#include <unistd.h>\nint main() { return !(sizeof(off_t) >= 8); };'

@conf
def check_large_file(self, **kw):
	"""
	see if large files are supported and define the macro HAVE_LARGEFILE
	"""

	if not 'define_name' in kw:
		kw['define_name'] = 'HAVE_LARGEFILE'
	if not 'execute' in kw:
		kw['execute'] = True

	if not 'features' in kw:
		if self.env.CXX:
			kw['features'] = ['cxx', 'cxxprogram']
		else:
			kw['features'] = ['c', 'cprogram']

	kw['fragment'] = LARGE_FRAGMENT
	kw['msg'] = 'Checking for large file support'
	try:
		self.check(**kw)
	except self.errors.ConfigurationError:
		pass
	else:
		return True

	kw['msg'] = 'Checking for -D_FILE_OFFSET_BITS=64'
	kw['defines'] = ['_FILE_OFFSET_BITS=64']
	try:
		self.check(**kw)
	except self.errors.ConfigurationError:
		pass
	else:
		self.define('_FILE_OFFSET_BITS', 64)
		return True

	self.fatal('There is no support for large files')

########################################################################################


