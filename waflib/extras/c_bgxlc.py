#! /usr/bin/env python
# encoding: utf-8
# harald at klimachs.de

import os
from waflib.Tools import ccroot,ar
from waflib.Configure import conf

@conf
def find_xlc(conf):
	cc = conf.find_program(['bgxlc_r','bgxlc'], var='CC')
	conf.env.CC = conf.cmd_to_list(cc)
	conf.env.CC_NAME = 'bgxlc'

def configure(conf):
	conf.find_xlc()
	conf.find_ar()
	conf.xlc_common_flags()
	conf.env.LINKFLAGS_cshlib = ['-G','-Wl,-bexpfull']
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

