#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

from waflib.extras import fc
from waflib.Configure import conf

@conf
def find_gfortran(conf):
	conf.find_program(['gfortran', 'g95'], var='FC')
	conf.env.FC_NAME = 'GFORTRAN'

@conf
def gfortran_flags(conf):
	v = conf.env
	v['FCFLAGS_fcshlib']   = ['-fPIC']
	v['FORTRANMODFLAG']  = ['-M', ''] # template for module path
	v['FCFLAGS_DEBUG'] = ['-Werror'] # why not

@conf
def gfortran_modifier_darwin(conf):
	v = conf.env
	v['FCFLAGS_fcshlib']   = ['-fPIC', '-compatibility_version', '1', '-current_version', '1']
	v['LINKFLAGS_fcshlib'] = ['-dynamiclib']
	v['fcshlib_PATTERN']   = 'lib%s.dylib'
	v['FRAMEWORKPATH_ST']  = '-F%s'
	v['FRAMEWORK_ST']      = '-framework %s'

	v['LINKFLAGS_fcstlib'] = []

	v['FCSHLIB_MARKER']    = ''
	v['FCSTLIB_MARKER']    = ''
	v['SONAME_ST']         = ''

@conf
def gfortran_modifier_platform(conf):
	dest_os = conf.env['DEST_OS'] or Utils.unversioned_sys_platform()
	gfortran_modifier_func = globals().get('gfortran_modifier_' + dest_os)
	if gfortran_modifier_func:
			gfortran_modifier_func(conf)

def configure(conf):
	conf.find_gfortran()
	conf.find_ar()
	conf.fc_flags()
	conf.gfortran_flags()
	conf.gfortran_modifier_platform()

