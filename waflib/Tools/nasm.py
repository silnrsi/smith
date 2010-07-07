#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

"""
Nasm tool (asm processing)
"""

import waflib.Tools.ccroot # <- leave this
from waflib.TaskGen import feature

@feature('asm')
def apply_nasm_vars(self):
	self.env.append_value('ASFLAGS', self.to_list(getattr(self, 'nasm_flags', [])))

def configure(conf):
	nasm = conf.find_program(['nasm', 'yasm'], var='AS')

