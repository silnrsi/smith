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
'define':'defines',
'importpath':'includes',
'installpath':'install_path',
}

meths_typos = ['__call__', 'program', 'shlib', 'stlib', 'objects']

from waflib import Logs, Build
import waflib.Tools.ccroot

def replace(m):
	oldcall = getattr(Build.BuildContext, m)
	def call(self, *k, **kw):
		for x in typos:
			if x in kw:
				kw[typos[x]] = kw[x]
				del kw[x]
				Logs.error('typo %r -> %r' % (x, typos[x]))
		oldcall(self, *k, **kw)
	setattr(Build.BuildContext, m, call)

def options(opt):
	"""
	Add a few methods
	"""

	for m in meths_typos:
		replace(m)

def configure(conf):
	pass

