#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
Base classes (mostly abstract)
"""

import traceback, os, imp, sys
from waflib import Utils, Errors, Logs
import waflib.Node

# the following 3 constants are updated on each new release (do not touch)
HEXVERSION=0x106000
"""constant updated on new releases"""

WAFVERSION="1.6.0"
"""constant updated on new releases"""

WAFREVISION="9879"
"""constant updated on new releases"""

ABI = 98
"""project constant"""

DBFILE = '.wafpickle-%d' % ABI
"""constant"""

APPNAME = 'APPNAME'
"""constant"""

VERSION = 'VERSION'
"""constant"""

TOP  = 'top'
"""constant"""

OUT  = 'out'
"""constant"""

WSCRIPT_FILE = 'wscript'
"""constant"""


launch_dir = ''
"""Where Waf was executed"""
run_dir = ''
"""The wscript file to use as the entry point"""
top_dir = ''
"""project directory (top), if the project was configured"""
out_dir = ''
"""build directory (out), if the project was configured"""
waf_dir = ''
"""directory for the waf modules"""

local_repo = ''
"""local repository for the plugins"""
remote_repo = 'http://waf.googlecode.com/svn/'
"""remote directory for the plugins"""
remote_locs = ['branches/waf-%s/waflib/extras' % WAFVERSION, 'trunk/waflib/extras']

g_module = None
"""
wscript file representing the entry point of the project
"""

STDOUT = 1
STDERR = -1
BOTH   = 0

classes = []
def create_context(cmd_name, *k, **kw):
	"""TODO warn if more than one context is provided for a given command?"""
	global classes
	for x in classes:
		if x.cmd == cmd_name:
			return x(*k, **kw)
	ctx = Context(*k, **kw)
	ctx.fun = cmd_name
	return ctx

class store_context(type):
	"""metaclass: store the command classes into a global list"""
	def __init__(cls, name, bases, dict):
		super(store_context, cls).__init__(name, bases, dict)
		name = cls.__name__

		if name == 'ctx' or name == 'Context':
			return

		try:
			cls.cmd
		except AttributeError:
			raise Errors.WafError('Missing command for the context class %r (cmd)' % name)

		if not getattr(cls, 'fun', None):
			cls.fun = cls.cmd

		global classes
		classes.insert(0, cls)

# metaclass
ctx = store_context('ctx', (object,), {})

class Context(ctx):
	"""
	Base class for command contexts. Those objects are passed as the arguments
	of user functions (commands) defined in Waf scripts.
	"""

	errors = Errors
	"Alias provided for convenience"

	tools = {}
	"a cache for modules"

	def __init__(self, **kw):
		try:
			rd = kw['run_dir']
		except KeyError:
			global run_dir
			rd = run_dir

		# binds the context to the nodes in use to avoid a context singleton
		class node_class(waflib.Node.Node):
			pass
		self.node_class = node_class
		self.node_class.__module__ = "waflib.Node"
		self.node_class.__name__ = "Nod3"
		self.node_class.ctx = self

		self.root = self.node_class('', None)
		self.cur_script = None
		self.path = self.root.find_dir(rd)

		self.stack_path = []
		self.exec_dict = {'ctx':self, 'conf':self, 'bld':self, 'opt':self}
		self.logger = None

	def __hash__(self):
		"hash value for storing context objects in dicts or sets"
		return id(self)

	def load(self, tool_list, *k, **kw):
		"""
		load the options that a waf tool provides (or not)
		@type tool_list: list of string or string representing the space-separated tool list
		@param tool_list: list of waf tools to use
		"""
		tools = Utils.to_list(tool_list)
		path = Utils.to_list(kw.get('tooldir', ''))

		for t in tools:
			module = load_tool(t, path)
			fun = getattr(module, self.fun, None)
			if fun:
				fun(self)

	def execute(self):
		"""executes the command represented by this context - subclasses must override this method"""
		global g_module
		self.recurse([os.path.dirname(g_module.root_path)])

	def pre_recurse(self, node):
		"""from the context class"""
		self.stack_path.append(self.cur_script)

		self.cur_script = node
		self.path = node.parent

	def post_recurse(self, node):
		"""from the context class"""
		self.cur_script = self.stack_path.pop()
		if self.cur_script:
			self.path = self.cur_script.parent

	def recurse(self, dirs, name=None):
		"""
		Run user code from the supplied list of directories.
		The directories can be either absolute, or relative to the directory
		of the wscript file.
		@param dirs: List of directories to visit
		@type  name: string
		@param name: Name of function to invoke from the wscript
		"""
		for d in Utils.to_list(dirs):

			if not os.path.isabs(d):
				# absolute paths only
				d = os.path.join(self.path.abspath(), d)

			WSCRIPT     = os.path.join(d, WSCRIPT_FILE)
			WSCRIPT_FUN = WSCRIPT + '_' + self.fun

			node = self.root.find_node(WSCRIPT_FUN)
			if node:
				self.pre_recurse(node)
				function_code = node.read('rU')

				try:
					exec(function_code, self.exec_dict)
				except Exception as e:
					raise Errors.WafError(ex=e, pyfile=d)
				self.post_recurse(node)

			else:
				node = self.root.find_node(WSCRIPT)
				if not node:
					raise Errors.WafError('No wscript file in directory %s' % d)
				self.pre_recurse(node)
				wscript_module = load_module(node.abspath())
				user_function = getattr(wscript_module, self.fun, None)
				if not user_function:
					raise Errors.WafError('No function %s defined in %s' % (self.fun, node.abspath()))
				user_function(self)
				self.post_recurse(node)

	def fatal(self, msg, ex=None):
		"""raise a configuration error"""
		if self.logger:
			self.logger.info('from %s: %s' % (self.path.abspath(), msg))
		try:
			msg = '%s\n(complete log in %s)' % (msg, self.logger.handlers[0].baseFilename)
		except:
			pass
		raise self.errors.ConfigurationError(msg, ex=ex, pyfile=self.path.abspath())

	def to_log(self, var):
		"""log some information to the logger (if present)"""
		if not var:
			return
		if self.logger:
			self.logger.info(var)
		else:
			sys.stderr.write(var)

	def exec_command(self, cmd, **kw):
		"""
		execute a command, return the exit status
		if the context has the attribute 'log', capture and log the process stderr/stdout

		this method should be used whenever possible for proper logging

		@param cmd: args for subprocess.Popen
		@param kw: keyword arguments for subprocess.Popen
		"""
		subprocess = Utils.subprocess
		kw['shell'] = isinstance(cmd, str)
		Logs.debug('runner: %r' % cmd)

		if Utils.is_win32 and isinstance(cmd, str) and len(cmd) > 2000:
			# win32 stuff
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			kw['startupinfo'] = startupinfo

		try:
			if self.logger:
				# warning: may deadlock with a lot of output (subprocess limitation)

				self.logger.info(cmd)

				kw['stdout'] = kw['stderr'] = subprocess.PIPE
				p = subprocess.Popen(cmd, **kw)
				(out, err) = p.communicate()
				if out:
					self.logger.debug('out: %s' % out.decode('utf-8'))
				if err:
					self.logger.error('err: %s' % err.decode('utf-8'))
				return p.returncode
			else:
				p = subprocess.Popen(cmd, **kw)
				return p.wait()
		except OSError:
			return -1

	def cmd_and_log(self, cmd, **kw):
		"""
		execute a command, return the stdout
		this method should be used whenever possible for proper logging

		to obtain stdout+stderr, pass output=BOTH in the arguments (or output=0)
		to obtain just stderr, pass output=STDERR in the arguments (or output=-1)

		@param cmd: args for subprocess.Popen
		@param kw: keyword arguments for subprocess.Popen
		"""
		subprocess = Utils.subprocess
		kw['shell'] = isinstance(cmd, str)
		Logs.debug('runner: %r' % cmd)

		if Utils.is_win32 and isinstance(cmd, str) and len(cmd) > 2000:
			# win32 stuff
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			kw['startupinfo'] = startupinfo

		if 'quiet' in kw:
			quiet = kw['quiet']
			del kw['quiet']
		else:
			quiet = None

		if 'output' in kw:
			to_ret = kw['output']
			del kw['output']
		else:
			to_ret = STDOUT

		kw['stdout'] = kw['stderr'] = subprocess.PIPE
		if not quiet:
			self.to_log(cmd)
		try:
			p = subprocess.Popen(cmd, **kw)
			(out, err) = p.communicate()
		except Exception as e:
			try:
				self.to_log(str(err))
			except:
				pass
			raise Errors.WafError('Execution failure', ex=e)

		if not isinstance(out, str):
			out = out.decode('utf-8')
		if not isinstance(err, str):
			err = err.decode('utf-8')

		if out and quiet != STDOUT and quiet != BOTH:
			self.to_log('out: %s' % out)
		if err and quiet != STDERR and quiet != BOTH:
			self.to_log('err: %s' % err)

		if p.returncode:
			e = Errors.WafError('command %r returned %r' % (cmd, p.returncode))
			e.returncode = p.returncode
			raise e

		if to_ret == BOTH:
			return (out, err)
		elif to_ret == STDERR:
			return err
		return out

	def msg(self, msg, result, color=None):
		"""Prints a configuration message 'Checking for xxx: ok'"""
		self.start_msg(msg)

		if not isinstance(color, str):
			color = result and 'GREEN' or 'YELLOW'

		self.end_msg(result, color)

	def start_msg(self, msg):
		"""Prints the beginning of a 'Checking for xxx' message"""
		try:
			if self.in_msg:
				self.in_msg += 1
				return
		except:
			self.in_msg = 0
		self.in_msg += 1

		try:
			self.line_just = max(self.line_just, len(msg))
		except AttributeError:
			self.line_just = max(40, len(msg))
		for x in (self.line_just * '-', msg):
			self.to_log(x)
		Logs.pprint('NORMAL', "%s :" % msg.ljust(self.line_just), sep='')

	def end_msg(self, result, color=None):
		"""Prints the end of a 'Checking for' message"""
		self.in_msg -= 1
		if self.in_msg:
			return

		defcolor = 'GREEN'
		if result == True:
			msg = 'ok'
		elif result == False:
			msg = 'not found'
			defcolor = 'YELLOW'
		else:
			msg = str(result)

		self.to_log(msg)
		Logs.pprint(color or defcolor, msg)


cache_modules = {}
"""
Dictionary holding already loaded modules, keyed by their absolute path.
private cache
"""

def load_module(file_path):
	"""
	Load a Python source file containing user code.
	@type file_path: string
	@param file_path: file path
	@return: Loaded Python module
	"""
	try:
		return cache_modules[file_path]
	except KeyError:
		pass

	module = imp.new_module(WSCRIPT_FILE)
	try:
		code = Utils.readf(file_path, m='rU')
	except (IOError, OSError):
		raise Errors.WafError('Could not read the file %r' % file_path)

	module_dir = os.path.dirname(file_path)
	sys.path.insert(0, module_dir)

	try:
		exec(code, module.__dict__)
	except Exception as e:
		raise Errors.WafError(ex=e, pyfile=file_path)
	sys.path.remove(module_dir)

	cache_modules[file_path] = module

	return module

def load_tool(tool, tooldir=None):
	"""
	Import the Python module that contains the specified tool from
	the tools directory. Store the tool in the dict Context.tools

	@type  tool: string
	@param tool: Name of the tool
	@type  tooldir: list
	@param tooldir: List of directories to search for the tool module
	"""
	tool = tool.replace('++', 'xx')
	tool = tool.replace('java', 'javaw')
	tool = tool.replace('compiler_cc', 'compiler_c')

	if tooldir:
		assert isinstance(tooldir, list)
		sys.path = tooldir + sys.path
		try:
			__import__(tool)
			ret = sys.modules[tool]
			Context.tools[tool] = ret
			return ret
		finally:
			for d in tooldir:
				sys.path.remove(d)
	else:
		global waf_dir
		try:
			os.stat(os.path.join(waf_dir, 'waflib', 'Tools', tool + '.py'))
			d = 'waflib.Tools.%s' % tool
		except:
			try:
				os.stat(os.path.join(waf_dir, 'waflib', 'extras', tool + '.py'))
				d = 'waflib.extras.%s' % tool
			except:
				d = tool # user has messed with sys.path

		__import__(d)
		ret = sys.modules[d]
		Context.tools[tool] = ret
		return ret

