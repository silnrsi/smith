#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
Dumb C/C++ preprocessor for finding dependencies

It will look at all include files it can find after removing the comments
"""

import re, sys, os, string, traceback
from waflib import Logs, Build, Utils, Errors
from waflib.Logs import debug, error

re_inc = re.compile(
	'^[ \t]*(#|%:)[ \t]*(include)[ \t]*(.*)\r*$',
	re.IGNORECASE | re.MULTILINE)

def lines_includes(filename):
	code = Utils.readf(filename)
	if use_trigraphs:
		for (a, b) in trig_def: code = code.split(a).join(b)
	code = re_nl.sub('', code)
	code = re_cpp.sub(repl, code)
	return [(m.group(2), m.group(3)) for m in re.finditer(re_inc, code)]

def get_deps_simple(node, env, nodepaths=[], defines={}):
	"""
	Get the dependencies by just looking recursively at the #include statements
	"""

	nodes = []
	names = []

	def find_deps(node):
		lst = lines_includes(node.abspath())

		for (_, line) in lst:
			(t, filename) = extract_include(line, defines)
			if filename in names:
				continue

			if filename.endswith('.moc'):
				names.append(filename)

			found = None
			for n in nodepaths:
				if found:
					break
				found = n.find_resource(filename)

			if not found:
				if not filename in names:
					names.append(filename)
			elif not found in nodes:
				nodes.append(found)
				find_deps(node)

	find_deps(node)
	return (nodes, names)


