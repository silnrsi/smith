#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

import re

import waflib
import waflib.Logs as _msg
from waflib.Task import Task
from waflib.TaskGen import extension, feature, before, after

re_cyt = re.compile('import\\s(\\w+)\\s*$', re.M)
def cy_scan(self):

	txt = self.inputs[0].read()
	mods = []
	for m in re_cyt.finditer(txt):
		mods.append(m.group(1))

	_msg.debug("modules: %r" % mods)
	incs = getattr(self.generator, 'cython_includes', [])
	incs = [self.generator.path.find_dir(x) for x in incs]
	incs.append(self.inputs[0].parent)

	found = []
	missing = []
	for x in mods:
		for y in incs:
			k = y.find_resource(x + '.pxd')
			if k:
				found.append(k)
				break
		else:
			missing.append(x)
	_msg.debug("==> cython defs: %r" % found)
	return (found, missing)

@extension('.pyx')
def decide_ext(self, node):
	if 'cxx' in self.features:
		self.env.append_unique('CYTHONFLAGS', '--cplus')
		return ['.cc']
	return ['.c']

waflib.TaskGen.declare_chain(
	name	  = 'cython',
	rule	  = '${CYTHON} ${CYTHONFLAGS} -o ${TGT} ${SRC}',
	color	 = 'GREEN',
	ext_in	= '.pyx',
	scan	  = cy_scan,
	reentrant = True,
	decider   = decide_ext,
)

def options(ctx):
	ctx.add_option('--cython-flags', action='store', default='', help='space separated list of flags to pass to cython')

def configure(ctx):
	if not ctx.env.CC and not ctx.env.CXX:
		ctx.fatal('Load a C/C++ compiler first')
	if not ctx.env.PYTHON:
		ctx.fatal('Load the python tool first!')
	ctx.find_program('cython', var='CYTHON')
	if ctx.options.cython_flags:
		ctx.env.CYTHONFLAGS = ctx.options.cython_flags

@feature('cython')
def feature_cython(self):
	return

