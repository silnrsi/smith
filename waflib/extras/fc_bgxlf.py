#! /usr/bin/env python
# encoding: utf-8
# WARNING! All changes made to this file will be lost!

import re
from waflib import Utils
from waflib.Tools import fc,fc_config,fc_scan
from waflib.Configure import conf
def find_bgxlf(conf):
	fc=conf.find_program(['bgxlf2003_r','bgxlf2003'],var='FC')
	fc=conf.cmd_to_list(fc)
	conf.get_ifort_version(fc,mandatory=False)
	conf.env.FC_NAME='XLF'
def bgxlf_modifier_platform(conf):
	dest_os=conf.env['DEST_OS']or Utils.unversioned_sys_platform()
	ifort_modifier_func=getattr(conf,'ifort_modifier_'+dest_os,None)
	if ifort_modifier_func:
		ifort_modifier_func()
def get_bgxlf_version(conf,fc):
	version_re=re.compile(r"Version:\s*(?P<major>\d*)\.(?P<minor>\d*)",re.I).search
	cmd=fc+['-qversion']
	out,err=fc_config.getoutput(conf,cmd,stdin=False)
	if out:
		match=version_re(out)
	else:
		match=version_re(err)
	if not match:
		conf.fatal('cannot determine xlf version.')
	k=match.groupdict()
	conf.env['FC_VERSION']=(k['major'],k['minor'])
def bgxlf_common_flags(conf):
	v=conf.env
	v['FC_SRC_F']=[]
	v['FC_TGT_F']=['-c','-o']
	if not v['LINK_FC']:v['LINK_FC']=v['FC']
	v['FCLNK_SRC_F']=[]
	v['FCLNK_TGT_F']=['-o']
	v['FCINCPATH_ST']='-I%s'
	v['FCDEFINES_ST']='-D%s'
	v['FCLIB_ST']='-l%s'
	v['FCLIBPATH_ST']='-L%s'
	v['FCSTLIB_ST']='-l%s'
	v['FCSTLIBPATH_ST']='-L%s'
	v['SONAME_ST']=''
	v['FCSHLIB_MARKER']=''
	v['FCSTLIB_MARKER']=''
	v['LINKFLAGS_fcprogram']=['']
	v['fcprogram_PATTERN']='%s'
	v['FFLAGS_fcshlib']=['-fPIC']
	v['LINKFLAGS_fcshlib']=['-G','-Wl,-bexpfull']
	v['fcshlib_PATTERN']='lib%s.so'
	v['fcstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_bgxlf()
	conf.find_ar()
	conf.bgxlf_common_flags()
	conf.bgxlf_modifier_platform()

conf(find_bgxlf)
conf(bgxlf_modifier_platform)
conf(get_bgxlf_version)
conf(bgxlf_common_flags)
