#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

"assembly support - used by gas and nasm"

import os, sys
import waflib.Task
from waflib.TaskGen import extension, feature

@feature('asm')
def apply_asm_vars(self):
	self.env.append_value('ASFLAGS', self.to_list(getattr(self, 'asflags', [])))

class asm(waflib.Task.Task):
	color = 'BLUE'
	run_str = '${AS} ${ASFLAGS} ${_INCFLAGS} ${SRC} -o ${TGT}'

@extension('.s', '.S', '.asm', '.ASM', '.spp', '.SPP')
def asm_hook(self, node):
	return self.create_compiled_task('asm', node)

