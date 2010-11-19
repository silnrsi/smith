#!/usr/bin/env python
# encoding: utf-8
# Sebastian Schlingmann, 2008
# Thomas Nagy, 2008-2010 (ita)

"""
Lua support.

Compile *.lua* files into *.luac*::

	def configure(conf):
		conf.load('lua')
	def build(bld):
		bld(source='foo.lua')
"""

from waflib import TaskGen, Utils

TaskGen.declare_chain(
	name = 'luac',
	rule = '${LUAC} -s -o ${TGT} ${SRC}',
	ext_in = '.lua',
	ext_out = '.luac',
	reentrant = False
)

def configure(conf):
	"""
	Detect the luac compiler and set *conf.env.LUAC*
	"""
	conf.find_program('luac', var='LUAC')

