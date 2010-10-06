#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

from waflib.extras import fc
from waflib.Configure import conf

@conf
def find_ifort(conf):
	fc = conf.find_program('ifort', var='FC')
	fc = conf.cmd_to_list(fc)
	conf.get_fc_version(fc, ifort=True)
	conf.env.FC_NAME = 'IFORT'

@conf
def ifort_modifier_win32(conf):
    raise NotImplementedError("Ifort on win32 not yet implemented")

def configure(conf):
	conf.find_ifort()
	conf.find_ar()
	conf.fc_flags()

