#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Node: filesystem structure, contains lists of nodes

#. Each file/folder is represented by exactly one node.

#. Some potential class properties are stored in Build: nodes to depend on...
   unused class members increase the .wafpickle file size sensibly with lots of objects.

#. The build is launched from the top of the build dir (for example, in build/).

#. Although Node objects should not be created directly,
   the methods :py:func:`Node.make_node` or :py:func:`Node.find_node`
   may be used for exceptional circumstances

Each instance of :py:class:`Build.BuildContext` has a unique :py:class:`Node` subclass.
(aka: 'Nod3', see BuildContext initializer)
The BuildContext is referenced here as self.ctx
Its Node class is referenced here as self.__class__
"""

import os, re, sys, shutil
from waflib import Utils, Errors

prune_pats = '.git .bzr .hg .svn _MTN _darcs CVS SCCS'.split()
"""
These fnmatch expressions are used by default to prune the directory tree
while doing the recursive traversal in the find_iter method of the Node class.
"""

exclude_pats = prune_pats + '*~ #*# .#* %*% ._* .gitignore .cvsignore vssver.scc .DS_Store'.split()
"""
These fnmatch expressions are used by default to exclude files and dirs
while doing the recursive traversal in the find_iter method of the Node class.
"""

exclude_regs = '''
**/*~
**/#*#
**/.#*
**/%*%
**/._*
**/CVS
**/CVS/**
**/.cvsignore
**/SCCS
**/SCCS/**
**/vssver.scc
**/.svn
**/.svn/**
**/BitKeeper
**/.git
**/.git/**
**/.gitignore
**/.bzr
**/.bzrignore
**/.bzr/**
**/.hg
**/.hg/**
**/_MTN
**/_MTN/**
**/.arch-ids
**/{arch}
**/_darcs
**/_darcs/**
**/.DS_Store'''
"""
These Utils.jar_regexp expressions are used by default to exclude files and dirs and also prune the directory tree
while doing the recursive traversal in the ant_glob method of the Node class.
"""

# TODO optimize split_path by performing a replacement when unpacking?

def split_path(path):
	"""
	split a path, but faster than os.path.split
	"""
	return path.split('/')

def split_path_cygwin(path):
	if path.startswith('//'):
		ret = path.split('/')[2:]
		ret[0] = '/' + ret[0]
		return ret
	return path.split('/')

re_sp = re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret = re.split(re_sp, path)[2:]
		ret[0] = '\\' + ret[0]
		return ret
	return re.split(re_sp, path)

if sys.platform == 'cygwin':
	split_path = split_path_cygwin
elif sys.platform == 'win32':
	split_path = split_path_win32

class Node(object):
	"""
	This class is divided into two parts, the basic methods meant for filesystem access, and
	the ones which are bound to a context (the build context). The imports do not reflect this.
	"""

	__slots__ = ('name', 'sig', 'children', 'parent', 'cache_abspath', 'cache_isdir')
	def __init__(self, name, parent):
		self.name = name
		self.parent = parent

		if parent:
			if name in parent.children:
				raise Errors.WafError('node %s exists in the parent files %r already' % (name, parent))
			parent.children[name] = self

	def __setstate__(self, data):
		"serialization stuff"
		self.name = data[0]
		self.parent = data[1]
		if data[2] is not None:
			self.children = data[2]
		if data[3] is not None:
			self.sig = data[3]

	def __getstate__(self):
		"serialization stuff"
		return (self.name, self.parent, getattr(self, 'children', None), getattr(self, 'sig', None))

	def __str__(self):
		"for debugging purposes"
		return self.name

	def __repr__(self):
		"for debugging purposes"
		return self.abspath()

	def __hash__(self):
		"this hash is not persistent"
		return id(self)

	def __eq__(self, node):
		"there can be only one node for a path so we compare with the ids"
		return id(self) == id(node)

	def __copy__(self):
		"nodes are not supposed to be copied"
		raise Errors.WafError('nodes are not supposed to be copied')

	def read(self, flags='r'):
		"get the contents, assuming the node is a file"
		return Utils.readf(self.abspath(), flags)

	def write(self, data, flags='w'):
		"write some text to the physical file, assuming the node is a file"
		f = None
		try:
			f = open(self.abspath(), flags)
			f.write(data)
		finally:
			if f:
				f.close()

	def chmod(self, val):
		"change file/dir permissions"
		os.chmod(self.abspath(), val)

	def delete(self):
		"delete the file physically, do not destroy the nodes (meant for FILES)"
		try:
			if getattr(self, 'children', None):
				shutil.rmtree(self.abspath())
			else:
				os.unlink(self.abspath())
		except:
			pass

		try:
			delattr(self, 'children')
		except:
			pass

	def suffix(self):
		"scons-like - hot zone so do not touch"
		k = max(0, self.name.rfind('.'))
		return self.name[k:]

	def height(self):
		"amount of parents"
		d = self
		val = -1
		while d:
			d = d.parent
			val += 1
		return val

	def listdir(self):
		"list the directory contents"
		return Utils.listdir(self.abspath())

	def mkdir(self):
		"write a directory for the node"
		if getattr(self, 'cache_isdir', None):
			return

		try:
			self.parent.mkdir()
		except:
			pass

		if self.name:
			try:
				os.mkdir(self.abspath())
			except OSError as e:
				pass

			if not os.path.isdir(self.abspath()):
				raise Errors.WafError('%s is not a directory' % self)

			try:
				self.children
			except:
				self.children = {}

		self.cache_isdir = True

	def find_node(self, lst):
		"read the file system, make the nodes as needed"

		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		cur = self
		for x in lst:
			if x == '..':
				cur = cur.parent
				continue

			try:
				if x in cur.children:
					cur = cur.children[x]
					continue
			except:
				cur.children = {}

			# optimistic: create the node first then look if it was correct to do so
			cur = self.__class__(x, cur)
			try:
				os.stat(cur.abspath())
			except:
				del cur.parent.children[x]
				return None

		ret = cur

		try:
			while not getattr(cur.parent, 'cache_isdir', None):
				cur = cur.parent
				cur.cache_isdir = True
		except AttributeError:
			pass

		return ret

	def make_node(self, lst):
		"make a branch of nodes"
		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		cur = self
		for x in lst:
			if x == '..':
				cur = cur.parent
				continue

			if getattr(cur, 'children', {}):
				if x in cur.children:
					cur = cur.children[x]
					continue
			else:
				cur.children = {}
			cur = self.__class__(x, cur)
		return cur

	def search(self, lst):
		"dumb search for existing nodes"
		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		cur = self
		try:
			for x in lst:
				if x == '..':
					cur = cur.parent
				else:
					cur = cur.children[x]
			return cur
		except:
			pass

	def path_from(self, node):
		"""path of this node seen from the other
			self = foo/bar/xyz.txt
			node = foo/stuff/
			-> ../bar/xyz.txt
		"""
		# common root in rev 7673

		c1 = self
		c2 = node

		c1h = c1.height()
		c2h = c2.height()

		lst = []
		up = 0

		while c1h > c2h:
			lst.append(c1.name)
			c1 = c1.parent
			c1h -= 1

		while c2h > c1h:
			up += 1
			c2 = c2.parent
			c2h -= 1

		while id(c1) != id(c2):
			lst.append(c1.name)
			up += 1

			c1 = c1.parent
			c2 = c2.parent

		for i in range(up):
			lst.append('..')
		lst.reverse()
		return os.sep.join(lst) or '.'

	def abspath(self):
		"""
		absolute path
		cache into the build context, cache_node_abspath
		"""
		try:
			return self.cache_abspath
		except:
			pass
		# think twice before touching this (performance + complexity + correctness)
		if not self.parent:
			val = os.sep == '/' and os.sep or ''
		elif not self.parent.name:
			# drive letter for win32
			val = (os.sep == '/' and os.sep or '') + self.name
		else:
			val = self.parent.abspath() + os.sep + self.name

		self.cache_abspath = val
		return val

	def is_child_of(self, node):
		"does this node belong to the subtree node"
		p = self
		diff = self.height() - node.height()
		while diff > 0:
			diff -= 1
			p = p.parent
		return id(p) == id(node)

	def ant_iter(self, accept=None, maxdepth=25, pats=[], dir=False, src=True, remove=True):
		"semi-private method used by ant_glob"
		dircont = self.listdir()
		dircont.sort()

		try:
			lst = set(self.children.keys())
			if remove:
				for x in lst - set(dircont):
					del self.children[x]
		except:
			self.children = {}

		for name in dircont:

			npats = accept(name, pats)
			if npats and npats[0]:
				accepted = [] in npats[0]

				node = self.make_node([name])

				isdir = os.path.isdir(node.abspath())
				if accepted:
					if isdir:
						if dir:
							yield node
					else:
						if src:
							yield node

				if getattr(node, 'cache_isdir', None) or isdir:
					node.cache_isdir = True
					if maxdepth:
						for k in node.ant_iter(accept=accept, maxdepth=maxdepth - 1, pats=npats, dir=dir, src=src):
							yield k
		raise StopIteration

	def ant_glob(self, *k, **kw):
		"""
		This method is used for finding files across folders. It behaves like ant patterns:
		
		* ``**/*`` find all files recursively
		* ``**/*.class`` find all files ending by .class
		* ``..`` find all files having two characters such as 'aa' or 'bb'
		
		For more information see http://ant.apache.org/manual/dirtasks.html
		
		GOTCHA: the nodes that correspond to files and folders that do not exist will be removed

		:param dir: return folders too (False by default)
		:param src: return files (True by default)
		:param remove: remove files (True by default)
		"""

		src = kw.get('src', True)
		dir = kw.get('dir', False)

		excl = kw.get('excl', exclude_regs)
		incl = k and k[0] or kw.get('incl', '**')

		def to_pat(s):
			lst = Utils.to_list(s)
			ret = []
			for x in lst:
				x = x.replace('\\', '/').replace('//', '/')
				if x.endswith('/'):
					x += '**'
				lst2 = x.split('/')
				accu = []
				for k in lst2:
					if k == '**':
						accu.append(k)
					else:
						k = k.replace('.', '[.]').replace('*','.*').replace('?', '.').replace('+', '\\+')
						k = '^%s$' % k
						try:
							#print "pattern", k
							accu.append(re.compile(k))
						except Exception, e:
							raise Errors.WafError("Invalid pattern: %s" % k, e)
				ret.append(accu)
			return ret

		def filtre(name, nn):
			ret = []
			for lst in nn:
				if not lst:
					pass
				elif lst[0] == '**':
					ret.append(lst)
					if len(lst) > 1:
						if lst[1].match(name):
							ret.append(lst[2:])
					else:
						ret.append([])
				elif lst[0].match(name):
					ret.append(lst[1:])
			return ret

		def accept(name, pats):
			nacc = filtre(name, pats[0])
			nrej = filtre(name, pats[1])
			if [] in nrej:
				nacc = []
			return [nacc, nrej]

		ret = [x for x in self.ant_iter(accept=accept, pats=[to_pat(incl), to_pat(excl)], maxdepth=25, dir=dir, src=src, remove=kw.get('remove', 'True'))]
		if kw.get('flat', False):
			return ' '.join([x.path_from(self) for x in ret])

		return ret

	# --------------------------------------------------------------------------------
	# the following methods require the source/build folders (bld.srcnode/bld.bldnode)
	# using a subclass is a possibility, but is that really necessary?
	# --------------------------------------------------------------------------------

	def is_src(self):
		"""note: !is_src does not imply is_bld()"""
		cur = self
		x = id(self.ctx.srcnode)
		y = id(self.ctx.bldnode)
		while cur.parent:
			if id(cur) == y:
				return False
			if id(cur) == x:
				return True
			cur = cur.parent
		return False

	def is_bld(self):
		"""note: !is_bld does not imply is_src"""
		cur = self
		y = id(self.ctx.bldnode)
		while cur.parent:
			if id(cur) == y:
				return True
			cur = cur.parent
		return False

	def get_src(self):
		"""for a build node, will return the equivalent src node (or self if not possible)"""
		cur = self
		x = id(self.ctx.srcnode)
		y = id(self.ctx.bldnode)
		lst = []
		while cur.parent:
			if id(cur) == y:
				lst.reverse()
				return self.ctx.srcnode.make_node(lst)
			if id(cur) == x:
				return self
			lst.append(cur.name)
			cur = cur.parent
		return self

	def get_bld(self):
		"""for a src node, will return the equivalent bld node (or self if not possible)"""
		cur = self
		x = id(self.ctx.srcnode)
		y = id(self.ctx.bldnode)
		lst = []
		while cur.parent:
			if id(cur) == y:
				return self
			if id(cur) == x:
				lst.reverse()
				return self.ctx.bldnode.make_node(lst)
			lst.append(cur.name)
			cur = cur.parent
		return self

	def find_resource(self, lst):
		"""
		try to find a declared build node or a source file
		"""
		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		node = self.get_bld().search(lst)
		if not node:
			self = self.get_src()
			node = self.search(lst)
			if not node:
				node = self.find_node(lst)
		try:
			pat = node.abspath()
			if os.path.isdir(pat):
				return None
		except:
			pass
		return node

	def find_or_declare(self, lst):
		"""
		if 'self' is in build directory, try to return an existing node
		if no node is found, go to the source directory
		try to find an existing node in the source directory
		if no node is found, create it in the build directory
		"""
		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		node = self.get_bld().search(lst)
		if node:
			if not os.path.isfile(node.abspath()):
				node.sig = None
				try:
					node.parent.mkdir()
				except:
					pass
			return node
		self = self.get_src()
		node = self.find_node(lst)
		if node:
			if not os.path.isfile(node.abspath()):
				node.sig = None
				try:
					node.parent.mkdir()
				except:
					pass
			return node
		node = self.get_bld().make_node(lst)
		node.parent.mkdir()
		return node

	def find_dir(self, lst):
		"""
		search for a folder in the filesystem
		"""
		if isinstance(lst, str):
			lst = [x for x in split_path(lst) if x and x != '.']

		node = self.find_node(lst)
		try:
			if not os.path.isdir(node.abspath()):
				return None
		except (OSError, AttributeError):
			# the node might be None, and raise an AttributeError
			return None
		return node

	# helpers for building things
	def change_ext(self, ext, ext_in=None):
		"node of the same path, but with a different extension"
		name = self.name
		if ext_in is None:
			k = name.rfind('.')
			if k >= 0:
				name = name[:k] + ext
			else:
				name = name + ext
		else:
			name = name[:- len(ext_in)] + ext

		return self.parent.find_or_declare([name])

	def nice_path(self, env=None):
		"printed in the console, open files easily from the launch directory"
		return self.path_from(self.ctx.launch_node())

	def bldpath(self):
		"path seen from the build directory default/src/foo.cpp"
		return self.path_from(self.ctx.bldnode)

	def srcpath(self):
		"path seen from the source directory ../src/foo.cpp"
		return self.path_from(self.ctx.srcnode)

	def relpath(self):
		"if a build node, bldpath, else srcpath"
		cur = self
		x = id(self.ctx.bldnode)
		while cur.parent:
			if id(cur) == x:
				return self.ctx.path()
			cur = cur.parent
		return self.srcpath()

	def bld_dir(self):
		"build path without the file name"
		return self.parent.bldpath()

	def bld_base(self):
		"build path without the extension: src/dir/foo(.cpp)"
		s = os.path.splitext(self.name)[0]
		return self.bld_dir() + os.sep + s

	def get_bld_sig(self):
		try:
			ret = self.ctx.hash_cache[id(self)]
		except KeyError:
			pass
		except AttributeError:
			self.ctx.hash_cache = {}
		else:
			return ret

		if not self.is_bld() or self.ctx.bldnode is self.ctx.srcnode:
			self.sig = Utils.h_file(self.abspath())
		self.ctx.hash_cache[id(self)] = ret = self.sig
		return ret



pickle_lock = Utils.threading.Lock()
"""lock mandatory for thread-safe node serialization"""

class Nod3(Node):
	"""mandatory subclass for thread-safe node serialization"""
	pass # do not remove


if sys.platform == 'win32':
	def listdir(self):
		if not self.parent:
			return list(self.children.keys())
		return Utils.listdir(self.abspath())
	Node.listdir = listdir

