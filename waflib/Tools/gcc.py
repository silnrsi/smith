#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)
# Yinon Ehrlich, 2009

import os, sys
from waflib import Configure, Options, Utils
from waflib.Tools import ccroot, ar
from waflib.Configure import conf

@conf
def find_gcc(conf):
	cc = conf.find_program(['gcc', 'cc'], var='CC')
	cc = conf.cmd_to_list(cc)
	conf.get_cc_version(cc, gcc=True)
	conf.env.CC_NAME = 'gcc'
	conf.env.CC      = cc

@conf
def gcc_common_flags(conf):
	v = conf.env

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = ['-c', '-o', ''] # shell hack for -MD

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = ['-o', ''] # shell hack for -MD
	v['CPPPATH_ST']          = '-I%s'
	v['DEFINES_ST']          = '-D%s'

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STLIB_ST']            = '-l%s'
	v['STLIBPATH_ST']        = '-L%s'
	v['RPATH_ST']            = '-Wl,-rpath,%s'

	v['SONAME_ST']           = '-Wl,-h,%s'
	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STLIB_MARKER']        = '-Wl,-Bstatic'

	# program
	v['cprogram_PATTERN']    = '%s'

	# shared librar
	v['CFLAGS_cshlib']      = ['-fPIC']
	v['LINKFLAGS_cshlib']    = ['-shared']
	v['cshlib_PATTERN']      = 'lib%s.so'

	# static lib
	v['LINKFLAGS_cstlib']    = ['-Wl,-Bstatic']
	v['cstlib_PATTERN']      = 'lib%s.a'

	# osx stuff
	v['LINKFLAGS_MACBUNDLE'] = ['-bundle', '-undefined', 'dynamic_lookup']
	v['CFLAGS_MACBUNDLE']   = ['-fPIC']
	v['macbundle_PATTERN']   = '%s.bundle'

@conf
def gcc_modifier_win32(conf):
	v = conf.env
	v['cprogram_PATTERN']    = '%s.exe'

	v['cshlib_PATTERN']      = '%s.dll'
	v['implib_PATTERN']      = 'lib%s.dll.a'
	v['IMPLIB_ST']           = '-Wl,--out-implib,%s'

	v['CFLAGS_cshlib']      = []

	v.append_value('CFLAGS_cshlib', ['-DDLL_EXPORT']) # TODO adding nonstandard defines like this DLL_EXPORT is not a good idea

	# Auto-import is enabled by default even without this option,
	# but enabling it explicitly has the nice effect of suppressing the rather boring, debug-level messages
	# that the linker emits otherwise.
	v.append_value('LINKFLAGS', ['-Wl,--enable-auto-import'])

@conf
def gcc_modifier_cygwin(conf):
	gcc_modifier_win32(conf)
	v = conf.env
	v['cshlib_PATTERN'] = 'cyg%s.dll'
	v.append_value('LINKFLAGS_cshlib', ['-Wl,--enable-auto-image-base'])
	v['CFLAGS_cshlib'] = []

@conf
def gcc_modifier_darwin(conf):
	v = conf.env
	v['CFLAGS_cshlib']      = ['-fPIC', '-compatibility_version', '1', '-current_version', '1']
	v['LINKFLAGS_cshlib']    = ['-dynamiclib']
	v['cshlib_PATTERN']      = 'lib%s.dylib'
	v['FRAMEWORKPATH_ST']    = '-F%s'
	v['FRAMEWORK_ST']        = '-framework %s'

	v['LINKFLAGS_cstlib']    = []

	v['SHLIB_MARKER']        = ''
	v['STLIB_MARKER']        = ''
	v['SONAME_ST']           = ''

@conf
def gcc_modifier_aix(conf):
	v = conf.env
	v['LINKFLAGS_cprogram']  = ['-Wl,-brtl']

	v['LINKFLAGS_cshlib']    = ['-shared','-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

@conf
def gcc_modifier_platform(conf):
	# * set configurations specific for a platform.
	# * the destination platform is detected automatically by looking at the macros the compiler predefines,
	#   and if it's not recognised, it fallbacks to sys.platform.
	gcc_modifier_func = globals().get('gcc_modifier_' + conf.env.DEST_OS)
	if gcc_modifier_func:
			gcc_modifier_func(conf)

configure = '''
find_gcc
find_ar
gcc_common_flags
gcc_modifier_platform
cc_load_tools
cc_add_flags
link_add_flags
'''
