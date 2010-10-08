#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

"as and gas"

import waflib.Tools.ccroot # - leave this

def configure(conf):
	conf.find_program(['gas', 'as', 'gcc'], var='AS')
	conf.env.AS_TGT_F = '-o'
