#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Utilities and cross-platform fixes.
"""

import os, sys, errno, traceback, inspect, re, shutil, datetime, gc
try:
	import subprocess
except:
	try:
		import waflib.extras.subprocess as subprocess
	except:
		print("the subprocess module is missing, try to add it to the folder waflib/extras (python 2.3?)")

try:
	from collections import deque
except ImportError: # for python 2.3 :-/
	class deque(list):
		def popleft(self):
			return self.pop(0)

from waflib import Errors

try:
	from collections import UserDict
except:
	from UserDict import UserDict

try:
	from hashlib import md5
except:
	try:
		from md5 import md5
	except:
		# never fail to enable fixes from another module
		pass

try:
	import threading
except:
	# broken platforms, these fixes are only to avoid broken imports
	# use waf -j1 on those platforms
	class threading(object):
		pass
	class Lock(object):
		def acquire(self):
			pass
		def release(self):
			pass
	threading.Lock = threading.Thread = Lock
else:
	run_old = threading.Thread.run
	def run(*args, **kwargs):
		try:
			run_old(*args, **kwargs)
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			sys.excepthook(*sys.exc_info())
	threading.Thread.run = run

SIG_NIL = 'iluvcuteoverload'.encode()
"""if you change the hash type, do not forget to change SIG_NIL"""

O644 = 420
"""permission for regular files"""

O755 = 493
"""permission for executable files"""

try:
	from collections import defaultdict
except ImportError:
	class defaultdict(dict):
		"""
		defaultdict was introduced in python 2.5, so we leave it for python 2.4 and 2.3
		"""
		def __init__(self, default_factory):
			super(defaultdict, self).__init__()
			self.default_factory = default_factory
		def __getitem__(self, key):
			try:
				return super(defaultdict, self).__getitem__(key)
			except KeyError:
				value = self.default_factory()
				self[key] = value
				return value

is_win32 = sys.platform == 'win32'
indicator = is_win32 and '\x1b[A\x1b[K%s%s%s\r' or '\x1b[K%s%s%s\r'

def readf(fname, m='r'):
	"""
	Read an entire file into a string, in practice yuo should rather
	use node.read(..)
	
	:type  fname: string
	:param fname: Path to file
	:type  m: string
	:param m: Open mode
	:rtype: string
	:return: Content of the file
	
	"""
	f = open(fname, m)
	try:
		txt = f.read()
	finally:
		f.close()
	return txt

def h_file(filename):
	"""
	compute a hash file, this method may be replaced if necessary
	"""
	f = open(filename, 'rb')
	m = md5()
	while (filename):
		filename = f.read(100000)
		m.update(filename)
	f.close()
	return m.digest()

try:
	x = ''.encode('hex')
except:
	import binascii
	def to_hex(s):
		ret = binascii.hexlify(s)
		if not isinstance(ret, str):
			ret = ret.decode('utf-8')
		return ret
else:
	def to_hex(s):
		"""
		return the hexadecimal representation of a string
		"""
		return s.encode('hex')

listdir = os.listdir
if is_win32:
	def listdir_win32(s):
		"""
		list the contents of a folder, because the behaviour is platform-dependent
		you should always use Utils.listdir
		"""

		if not s:
			from ctypes import byref, windll, c_ulong, c_wchar_p, create_unicode_buffer
			get = windll.kernel32.GetLogicalDriveStringsW
			buf_len = c_ulong()
			l = c_ulong(0)
			str_drives = c_wchar_p(0)
			buf_len = get(l, str_drives)
			l = buf_len
			buf_len = 0
			str_drives = create_unicode_buffer('\x000', l)
			buf_len = get(l, byref(str_drives))
			drives = [x for x in  str_drives[:-1].split('\\\x00') if x]
			return drives

		if re.match('^[A-Za-z]:$', s):
			# os.path.isdir fails if s contains only the drive name... (x:)
			s += os.sep
		if not os.path.isdir(s):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		return os.listdir(s)
	listdir = listdir_win32

def num2ver(ver):
	"""
	convert a string, tuple or version number into an integer
	"""
	if isinstance(ver, str):
		ver = tuple(ver.split('.'))
	if isinstance(ver, tuple):
		ret = 0
		for i in range(4):
			if i < len(ver):
				ret += 256**(3 - i) * int(ver[i])
		return ret
	return ver

def ex_stack():
	"""
	extract the stack to display exceptions
	"""
	exc_type, exc_value, tb = sys.exc_info()
	exc_lines = traceback.format_exception(exc_type, exc_value, tb)
	return ''.join(exc_lines)

def to_list(sth):
	"""
	Convert a string argument to a list by splitting on spaces, and pass
	through a list argument unchanged.

	:param sth: List or a string of items separated by spaces
	:rtype: list
	:return: Argument converted to list
	
	"""
	if isinstance(sth, str):
		return sth.split()
	else:
		return sth

re_nl = re.compile('\r*\n', re.M)
def str_to_dict(txt):
	"""
	Parse a string with key = value pairs into a dictionary.
	
	:type  s: string
	:param s: String to parse
	:rtype: dict
	:return: Dictionary containing parsed key-value pairs
	"""
	tbl = {}

	lines = re_nl.split(txt)
	for x in lines:
		x = x.strip()
		if not x or x.startswith('#') or x.find('=') < 0:
			continue
		tmp = x.split('=')
		tbl[tmp[0].strip()] = '='.join(tmp[1:]).strip()
	return tbl

rot_chr = ['\\', '|', '/', '-']
"List of characters to use when displaying the throbber"
rot_idx = 0
"Index of the current throbber character"

def split_path(path):
	"""
	split a path on unix platforms, os.path.split
	has a different behaviour so we do not use it
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
elif is_win32:
	split_path = split_path_win32

def check_dir(path):
	"""
	Ensure that a directory exists, and try to avoid thread issues (similar to mkdir -p)
	:type  dir: string
	:param dir: Path to directory
	"""
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except OSError as e:
			if not os.path.isdir(path):
				raise Errors.WafError('Cannot create folder %r' % path, ex=e)

def def_attrs(cls, **kw):
	"""
	set attributes for class.
	
	:type cls: class
	:param cls: the class to update the given attributes in.
	:type kw: dict
	:param kw: dictionary of attributes names and values.

	if the given class hasn't one (or more) of these attributes, add the attribute with its value to the class.
	"""
	for k, v in kw.items():
		if not hasattr(cls, k):
			setattr(cls, k, v)

def quote_define_name(s):
	"""
	Convert a string to an identifier suitable for C defines.
	
	:type  s: string
	:param s: String to convert
	:rtype: string
	:return: Identifier suitable for C defines
	"""
	fu = re.compile("[^a-zA-Z0-9]").sub("_", s)
	fu = fu.upper()
	return fu

def h_list(lst):
	"""Hash the contents of a list."""
	m = md5()
	m.update(str(lst).encode())
	return m.digest()

def h_fun(fun):
	"""
	Get the source of a function for hashing. In cpython, only the functions
	defined in modules can be hashed, so it will not work for functions defined
	in wscript files (but it will for the ones defined in Waf tools)
	"""
	try:
		return fun.code
	except AttributeError:
		try:
			h = inspect.getsource(fun)
		except IOError:
			h = "nocode"
		try:
			fun.code = h
		except AttributeError:
			pass
		return h

reg_subst = re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr, params):
	"""
	Replaces ${VAR} with the value of VAR taken from the dictionary
	:type  expr: string
	:param expr: String to perform substitution on
	:param params: Dictionary to look up variable values.
	"""
	def repl_var(m):
		if m.group(1):
			return '\\'
		if m.group(2):
			return '$'
		try:
			# ConfigSet instances may contain lists
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var, expr)

def destos_to_binfmt(key):
	"""
	Get the binary format based on the unversioned platform name.
	"""
	if key == 'darwin':
		return 'mac-o'
	elif key in ('win32', 'cygwin', 'uwin', 'msys'):
		return 'pe'
	return 'elf'

def unversioned_sys_platform():
	"""
	Get the unversioned platform name.
	Some Python platform names contain versions, that depend on
	the build environment, e.g. linux2, freebsd6, etc.
	This returns the name without the version number. Exceptions are
	os2 and win32, which are returned verbatim.
	:rtype: string
	:return: Unversioned platform name
	"""
	s = sys.platform
	if s == 'java':
		# The real OS is hidden under the JVM.
		from java.lang import System
		s = System.getProperty('os.name')
		# see http://lopica.sourceforge.net/os.html for a list of possible values
		if s == 'Mac OS X':
			return 'darwin'
		elif s.startswith('Windows '):
			return 'win32'
		elif s == 'OS/2':
			return 'os2'
		elif s == 'HP-UX':
			return 'hpux'
		elif s in ('SunOS', 'Solaris'):
			return 'sunos'
		else: s = s.lower()
	if s == 'win32' or s.endswith('os2') and s != 'sunos2': return s
	return re.split('\d+$', s)[0]

def nada(*k, **kw):
	"""A function that does nothing."""
	pass

class Timer(object):
	"""
	Simple object for timing the execution of commands.
	Its string representation is the current time.
	"""
	def __init__(self):
		self.start_time = datetime.datetime.utcnow()

	def __str__(self):
		delta = datetime.datetime.utcnow() - self.start_time
		days = int(delta.days)
		hours = int(delta.seconds / 3600)
		minutes = int((delta.seconds - hours * 3600) / 60)
		seconds = delta.seconds - hours * 3600 - minutes * 60 + float(delta.microseconds) / 1000 / 1000
		result = ''
		if days:
			result += '%dd' % days
		if days or hours:
			result += '%dh' % hours
		if days or hours or minutes:
			result += '%dm' % minutes
		return '%s%.3fs' % (result, seconds)

if is_win32:
	old = shutil.copy2
	def copy2(src, dst):
		"""
		shutil.copy2 does not copy the file attributes on windows, so we
		hack into the shutil module to fix the problem
		"""
		old(src, dst)
		shutil.copystat(src, src)
	setattr(shutil, 'copy2', copy2)

if os.name == 'java':
	# Jython cannot disable the gc but they can enable it ... wtf?
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable = gc.enable

def read_la_file(path):
	"""Untested, used by msvc.py"""
	sp = re.compile(r'^([^=]+)=\'(.*)\'$')
	dc = {}
	for line in readf(path).splitlines():
		try:
			_, left, right, _ = sp.split(line.strip())
			dc[left] = right
		except ValueError:
			pass
	return dc

def nogc(fun):
	"""
	Disable the gc in a particular method execution
	Used with pickle for storing/loading the build cache file
	"""
	def f(*k, **kw):
		try:
			gc.disable()
			ret = fun(*k, **kw)
		finally:
			gc.enable()
		return ret
	return f

def run_once(fun):
	"""
	decorator, make a function cache its results, use like this::

		@run_once
		def foo(k):
			return 345*2343
	"""
	cache = {}
	def wrap(k):
		try:
			return cache[k]
		except KeyError:
			ret = fun(k)
			cache[k] = ret
			return ret
	wrap.__cache__ = cache
	return wrap

