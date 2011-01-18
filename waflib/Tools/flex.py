#!/usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006
# Thomas Nagy, 2006-2010 (ita)

"""
The **flex** program is a code generator which creates C or C++ files.
The generated files are compiled into object files.
"""

import waflib.TaskGen

def decide_ext(self, node):
	if 'cxx' in self.features:
		return ['.lex.cc']
	return ['.lex.c']

waflib.TaskGen.declare_chain(
	name = 'flex',
	rule = '${FLEX} -o${TGT} ${FLEXFLAGS} ${SRC}',
	ext_in = '.l',
	decider = decide_ext,
	shell = True,
)

def configure(conf):
	"""
	Detect the *flex* program
	"""
	conf.find_program('flex', var='FLEX')

