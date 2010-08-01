#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re
from waflib import Utils, Build
from waflib.Configure import conf

def get_extensions(lst):
	ret = []
	for x in Utils.to_list(lst):
		try:
			ret.append(x[x.rfind('.') + 1:])
		except:
			pass
	return ret

def sniff_features(**kw):
	"""look at the source files and return the features (mainly cc and cxx)"""
	exts = get_extensions(kw['source'])
	type = kw['_type']

	if 'cxx' in exts or 'cpp' in exts or 'c++' in exts:
		if type == 'program':
			return 'cxx cxxprogram'
		if type == 'shlib':
			return 'cxx cxxshlib'
		if type == 'stlib':
			return 'cxx cxxstlib'
		return 'cxx'

	if 'd' in exts:
		if type == 'program':
			return 'd dprogram'
		if type == 'shlib':
			return 'd dshlib'
		if type == 'stlib':
			return 'd dstlib'
		return 'd'

	if 'vala' in exts or 'c' in exts:
		if type == 'program':
			return 'c cprogram'
		if type == 'shlib':
			return 'c cshlib'
		if type == 'stlib':
			return 'c cstlib'
		return 'c'

	if 'java' in exts:
		return 'java'

	return ''

@conf
def program(bld, *k, **kw):
	"""alias for features='c cprogram' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'program'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)

@conf
def shlib(bld, *k, **kw):
	"""alias for features='c cshlib' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'shlib'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)

@conf
def stlib(bld, *k, **kw):
	"""alias for features='c cstlib' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'stlib'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)

@conf
def objects(bld, *k, **kw):
	"""alias for features='c' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'objects'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)

