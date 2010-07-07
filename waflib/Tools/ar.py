#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)

"Create static libraries with ar"

import os
from waflib.Configure import conf

@conf
def find_ar(conf):
	conf.check_tool('ar')

def configure(conf):
	conf.find_program('ar', var='AR')
	conf.env.ARFLAGS = 'rcs'

