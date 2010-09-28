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

def configure(conf):
	conf.find_gfortran()
	conf.find_ar()
	conf.fc_flags()
	conf.gfortran_flags()

