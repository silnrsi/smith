#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""ConfigSet representation

Values must be lists. Everywhere.

There is one gotcha: getitem returns [] if the contents evals to False
This means env['foo'] = {}; print env['foo'] will print [] not {}
"""

import os, copy, re
from waflib import Logs, Utils
re_imp = re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$', re.M)

class ConfigSet(object):
	"""A dict that honor serialization and parent relationships
	Store and retrieve values easily and in a human-readable format
	it is not possible to serialize functions though
	"""
	__slots__ = ('table', 'parent')
	def __init__(self, filename=None):
		self.table = {}
		#self.parent = None

		if filename:
			self.load(filename)

	def __contains__(self, key):
		"""required to use foo in env"""
		if key in self.table: return True
		try: return self.parent.__contains__(key)
		except AttributeError: return False # parent may not exist

	def __str__(self):
		"""for debugging"""
		keys = set()
		cur = self
		while cur:
			keys.update(cur.table.keys())
			cur = getattr(cur, 'parent', None)
		keys = list(keys)
		keys.sort()
		return "\n".join(["%r %r" % (x, self.__getitem__(x)) for x in keys])

	def __getitem__(self, key):
		try:
			while 1:
				x = self.table.get(key, None)
				if not x is None:
					return x
				self = self.parent
		except AttributeError:
			return []

	def __setitem__(self, key, value):
		self.table[key] = value

	def __delitem__(self, key, value):
		del self.table[key]

	def __getattr__(self, name):
		"""
		access the data by env.value instead of env['value']

		waf was too fast so we had to slow i down a bit
		"""
		if name in self.__slots__:
			return object.__getattr__(self, name)
		else:
			return self[name]

	def __setattr__(self, name, value):
		if name in self.__slots__:
			object.__setattr__(self, name, value)
		else:
			self[name] = value

	def __delattr__(self, name):
		if name in self.__slots__:
			object.__delattr__(self, name)
		else:
			del self[name]

	def derive(self):
		"""shallow copy"""
		newenv = ConfigSet()
		newenv.parent = self
		return newenv

	def detach(self):
		"""modifying the original env will not change the copy"""
		tbl = self.get_merged_dict()
		try:
			delattr(self, 'parent')
		except AttributeError:
			pass
		else:
			keys = tbl.keys()
			for x in keys:
				tbl[x] = copy.deepcopy(tbl[x])
			self.table = tbl

	def get_flat(self, key):
		"""obtain a value as a string"""
		s = self[key]
		if isinstance(s, str): return s
		return ' '.join(s)

	def _get_list_value_for_modification(self, key):
		"""Gets a value that must be a list for further modification.  The
		list may be modified inplace and there is no need to
		"self.table[var] = value" afterwards.

		this is private btw
		"""
		try:
			value = self.table[key]
		except KeyError:
			try: value = self.parent[key]
			except AttributeError: value = []
			if isinstance(value, list):
				value = value[:]
			else:
				value = [value]
		else:
			if not isinstance(value, list):
				value = [value]
		self.table[key] = value
		return value

	def append_value(self, var, val):
		"""The value must be a list or a tuple"""
		current_value = self._get_list_value_for_modification(var)
		if isinstance(val, str): # if there were string everywhere we could optimize this
			val = [val]
		current_value.extend(val)

	def prepend_value(self, var, val):
		"""The value must be a list or a tuple"""
		if isinstance(val, str):
			val = [val]
		self.table[var] =  val + self._get_list_value_for_modification(var)

	def append_unique(self, var, val):
		"""
		The value must be a list or a tuple

		Note that there is no prepend_unique
		"""
		if isinstance(val, str):
			val = [val]
		current_value = self._get_list_value_for_modification(var)

		for x in val:
			if x not in current_value:
				current_value.append(x)

	def get_merged_dict(self):
		"""compute a merged table"""
		table_list = []
		env = self
		while 1:
			table_list.insert(0, env.table)
			try: env = env.parent
			except AttributeError: break
		merged_table = {}
		for table in table_list:
			merged_table.update(table)
		return merged_table

	def store(self, filename):
		"Write the variables into a file"
		f = None
		try:
			f = open(filename, 'w')
			merged_table = self.get_merged_dict()
			keys = list(merged_table.keys())
			keys.sort()
			for k in keys:
				if k != 'undo_stack':
					f.write('%s = %r\n' % (k, merged_table[k]))
		finally:
			if f:
				f.close()

	def load(self, filename):
		"Retrieve the variables from a file"
		tbl = self.table
		code = Utils.readf(filename)
		for m in re_imp.finditer(code):
			g = m.group
			tbl[g(2)] = eval(g(3))
		Logs.debug('env: %s' % str(self.table))

	def update(self, d):
		"""like dict.update, replace values from another dict"""
		for k, v in d.items():
			self[k] = v

	def stash(self):
		"""store the object state, to use with 'revert' below"""
		self.undo_stack = self.undo_stack + [self.table]
		self.table = self.table.copy()

	def revert(self):
		"""revert the object to a previous state, to use with 'stash' above"""
		self.table = self.undo_stack.pop(-1)

