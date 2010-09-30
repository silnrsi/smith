#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
burn a book, save a tree
"""

import os
all_modifs = {}

def fixdir(dir):
	"""call all the substitution functions on the waf folders"""
	global all_modifs
	for k in all_modifs:
		for v in all_modifs[k]:
			modif(os.path.join(dir, 'waflib'), k, v)

def modif(dir, name, fun):
	"""execute a substitution function"""
	if name == '*':
		lst = []
		for y in '. Tools extras'.split():
			for x in os.listdir(os.path.join(dir, y)):
				if x.endswith('.py'):
					lst.append(y + os.sep + x)
		for x in lst:
			modif(dir, x, fun)
		return

	filename = os.path.join(dir, name)
	f = open(filename, 'r')
	txt = f.read()
	f.close()

	txt = fun(txt)

	f = open(filename, 'w')
	f.write(txt)
	f.close()

def subst(*k):
	"""register a substitution function"""
	def do_subst(fun):
		global all_modifs
		for x in k:
			try:
				all_modifs[x].append(fun)
			except KeyError:
				all_modifs[x] = [fun]
		return fun
	return do_subst

@subst('*')
def r1(code):
	"utf-8 fixes for python < 2.6"
	code = code.replace('as e:', ',e:')
	code = code.replace(".decode('utf-8')", '')
	code = code.replace('.encode()', '')
	return code

@subst('Utils.py')
def r2(code):
	"byte objects for python < 2.6"
	code = code.replace("b'iluvcuteoverload'", "'iluvcuteoverload'")
	return code

@subst('Tools/c_config.py')
def r3(code):
	"more byte objects"
	code = code.replace("b'\\n'", "'\\n'")
	return code

@subst('Runner.py')
def r4(code):
	"generator syntax"
	code = code.replace('next(self.biter)', 'self.biter.next()')
	return code

