#!/usr/bin/env python
# encoding: utf-8
# Sebastian Schlingmann, 2008
# Thomas Nagy, 2008-2010 (ita)

from waflib import TaskGen, Utils

TaskGen.declare_chain(
	name = 'luac',
	rule = '${LUAC} -s -o ${TGT} ${SRC}',
	ext_in = '.lua',
	ext_out = '.luac',
	reentrant = False
)
	#install = 'LUADIR', # env variable TODO

@TaskGen.feature('lua')
def init_lua(self):
	self.default_chmod = Utils.O755

def configure(conf):
	conf.find_program('luac', var='LUAC')

