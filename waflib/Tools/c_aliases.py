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
			if not isinstance(x, str):
				x = x.name
			ret.append(x[x.rfind('.') + 1:])
		except:
			pass
	return ret

def sniff_features(**kw):
	"""look at the source files and return the features for a task generator (mainly cc and cxx)"""
	exts = get_extensions(kw['source'])
	type = kw['_type']
	feats = []

	# watch the order, cxx will have the precedence
	if 'cxx' in exts or 'cpp' in exts or 'c++' in exts or 'cc' in exts:
		feats.append('cxx')

	if 'c' in exts or 'vala' in exts:
		feats.append('c')

	if 'd' in exts:
		feats.append('d')

	if 'java' in exts:
		feats.append('java')

	if 'java' in exts:
		return 'java'

	if type in ['program', 'shlib', 'stlib']:
		for x in feats:
			if x in ['cxx', 'd', 'c']:
				feats.append(x + type)

	return feats

def set_features(kw, _type):
	kw['_type'] = _type
	kw['features'] = Utils.to_list(kw.get('features', [])) + Utils.to_list(sniff_features(**kw))

@conf
def program(bld, *k, **kw):
	"""alias for features='c cprogram' bound to the build context"""
	set_features(kw, 'program')
	return bld(*k, **kw)

@conf
def shlib(bld, *k, **kw):
	"""alias for features='c cshlib' bound to the build context"""
	set_features(kw, 'shlib')
	return bld(*k, **kw)

@conf
def stlib(bld, *k, **kw):
	"""alias for features='c cstlib' bound to the build context"""
	set_features(kw, 'stlib')
	return bld(*k, **kw)

@conf
def objects(bld, *k, **kw):
	"""alias for features='c' bound to the build context"""
	set_features(kw, 'objects')
	return bld(*k, **kw)

