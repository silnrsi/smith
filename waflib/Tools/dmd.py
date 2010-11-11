#!/usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2008-2010 (ita)

import sys
from waflib.Tools import ar, d
from waflib.Configure import conf

@conf
def find_dmd(conf):
	conf.find_program(['dmd', 'ldc'], var='D')

@conf
def common_flags_ldc(conf):
	v = conf.env
	v['DFLAGS']        = ['-d-version=Posix']
	v['LINKFLAGS']     = []
	v['DFLAGS_dshlib'] = ['-relocation-model=pic']

@conf
def common_flags_dmd(conf):
	v = conf.env

	# _DFLAGS _DIMPORTFLAGS

	# Compiler is dmd so 'gdc' part will be ignored, just
	# ensure key is there, so wscript can append flags to it
	#v['DFLAGS']            = ['-version=Posix']

	v['D_SRC_F']           = ''
	v['D_TGT_F']           = ['-c', '-of']

	# linker
	v['D_LINKER']          = v['D']
	v['DLNK_SRC_F']        = ''
	v['DLNK_TGT_F']        = '-of'
	v['DINC_ST'] = '-I%s'

	v['DSHLIB_MARKER'] = v['DSTLIB_MARKER'] = ''
	v['DSTLIB_ST'] = v['DSHLIB_ST']           = '-L-l%s'
	v['DSTLIBPATH_ST'] = v['DLIBPATH_ST']   = '-L-L%s'

	v['LINKFLAGS']        = ['-quiet']

	v['DFLAGS_dshlib']    = ['-fPIC']
	v['LINKFLAGS_dshlib'] = ['-L-shared']

	v['DHEADER_ext']       = '.di'
	v['D_HDR_F']           = ['-H', '-Hf']

def configure(conf):
	conf.find_dmd()
	conf.load('ar')
	conf.load('d')
	conf.common_flags_dmd()
	conf.d_platform_flags()

	if str(conf.env.D).find('ldc') > -1:
		conf.common_flags_ldc()

