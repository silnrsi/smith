#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
Search for common mistakes

There is a performance hit, so this tool must be loaded manually
"""

typos = {
'feature':'features',
'sources':'source',
'targets':'target',
'include':'includes',
'export_include':'export_includes',
'define':'defines',
'importpath':'includes',
'installpath':'install_path',
}

meths_typos = ['__call__', 'program', 'shlib', 'stlib', 'objects']

from waflib import Logs, Build, Node
import waflib.Tools.ccroot

def replace(m):
	"""
	We could add properties, but they would not work in some cases:
	bld.program(...) requires 'source' in the attributes
	"""
	oldcall = getattr(Build.BuildContext, m)
	def call(self, *k, **kw):
		for x in typos:
			if x in kw:
				kw[typos[x]] = kw[x]
				del kw[x]
				Logs.error('typo %r -> %r' % (x, typos[x]))
		return oldcall(self, *k, **kw)
	setattr(Build.BuildContext, m, call)

def enhance_lib():
	for m in meths_typos:
		replace(m)

	# catch '..' in ant_glob patterns
	old_ant_glob = Node.Node.ant_glob
	def ant_glob(self, *k, **kw):
		for x in k[0].split('/'):
			if x == '..':
				Logs.error("In ant_glob pattern %r: '..' means 'two dots', not 'parent directory'" % k[0])
		return old_ant_glob(self, *k, **kw)
	Node.Node.ant_glob = ant_glob

def options(opt):
	"""
	Add a few methods
	"""
	enhance_lib()

def configure(conf):
	pass

