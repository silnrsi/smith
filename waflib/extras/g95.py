#! /usr/bin/env python
# encoding: utf-8
# KWS 2010
# Thomas Nagy 2010 (ita)

from waflib.extras import fc
from waflib.Configure import conf

@conf
def find_g95(conf):
	fc = conf.find_program('g95', var='FC')
	fc = conf.cmd_to_list(fc)
	conf.get_fc_version(fc, g95=True)
	conf.env.FC_NAME = 'G95'

@conf
def g95_flags(conf):
	v = conf.env
	v['FCFLAGS_fcshlib']   = ['-fPIC']
	v['FORTRANMODFLAG']  = ['-fmod=', ''] # template for module path
	v['FCFLAGS_DEBUG'] = ['-Werror'] # why not

@conf
def g95_modifier_darwin(conf):
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
def g95_modifier_platform(conf):
	dest_os = conf.env['DEST_OS'] or Utils.unversioned_sys_platform()
	g95_modifier_func = globals().get('g95_modifier_' + dest_os)
	if g95_modifier_func:
			g95_modifier_func(conf)

def configure(conf):
	conf.find_g95()
	conf.find_ar()
	conf.fc_flags()
	conf.g95_flags()
	conf.g95_modifier_platform()
