#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)
# Yinon Ehrlich, 2009
# Michael Kuhn, 2009

import os, sys
from waflib.Tools import ccroot, ar
from waflib.Configure import conf

@conf
def find_xlcxx(conf):
	cxx = conf.find_program(['xlc++_r', 'xlc++'], var='CXX')
	cxx = conf.cmd_to_list(cxx)
	conf.env.CXX_NAME = 'xlc++'
	conf.env.CXX      = cxx

@conf
def xlcxx_common_flags(conf):
	v = conf.env

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = ['-c', '-o', ''] # shell hack for -MD

	# linker
	if not v['LINK_CXX']: v['LINK_CXX'] = v['CXX']
	v['CXXLNK_SRC_F']        = ''
	v['CXXLNK_TGT_F']        = ['-o', ''] # shell hack for -MD
	v['CPPPATH_ST'] = '-I%s'
	v['DEFINES_ST'] = '-D%s'

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STLIB_ST']        = '-l%s'
	v['STLIBPATH_ST']    = '-L%s'
	v['RPATH_ST']            = '-Wl,-rpath,%s'

	v['SONAME_ST']           = ''
	v['SHLIB_MARKER']        = ''
	v['STLIB_MARKER']    = ''
	v['FULLSTATIC_MARKER']   = '-static'

	# program
	v['LINKFLAGS_cxxprogram']   = ['-Wl,-brtl']
	v['program_PATTERN']     = '%s'

	# shared library
	v['CXXFLAGS_cxxshlib']      = ['-fPIC']
	v['LINKFLAGS_cxxshlib']     = ['-G', '-Wl,-brtl,-bexpfull']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['LINKFLAGS_cxxstlib'] = ''
	v['cxxstlib_PATTERN']   = 'lib%s.a'

configure = '''
find_xlcxx
find_ar
xlcxx_common_flags
cxx_load_tools
cxx_add_flags
link_add_flags
'''
