#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Configuration system

A configuration instance is created when "waf configure" is called, it is used to:
* create data dictionaries (ConfigSet instances)
* store the list of modules to import

The old model (copied from Scons) was to store logic (mapping file extensions to functions)
along with the data. In Waf a way was found to separate that logic by adding an indirection
layer (storing the names in the ConfigSet instances)

In the new model, the logic is more object-oriented, and the user scripts provide the
logic. The data files (ConfigSets) must contain configuration data only (flags, ..).

Note: the c/c++ related code is in the module waflib.Tools.c_config
"""

import os, shlex, sys, time
from waflib import ConfigSet, Utils, Options, Logs, Context, Build, Errors

try:
	from urllib import request
except:
	from urllib import urlopen
else:
	urlopen = request.urlopen

BREAK    = 'break'
"""in case of error, break"""

CONTINUE = 'continue'
"""in case of error, continue"""

WAF_CONFIG_LOG = 'config.log'
"""name of the configuration log file"""

autoconfig = False
"""execute the configuration automatically"""

conf_template = '''# project %(app)s configured on %(now)s by
# waf %(wafver)s (abi %(abi)s, python %(pyver)x on %(systype)s)
# using %(args)s
#'''

def download_check(node):
	"""
	hook to check for the tools which are downloaded
	a white list is a possibility (list of sha1 hashes for example)
	"""
	Logs.warn('replace me to check %r' % node)

def download_tool(tool, force=False):
	"""downloads a tool from the waf repository"""
	for x in Utils.to_list(Context.remote_repo):
		for sub in Utils.to_list(Context.remote_locs):
			url = '/'.join((x, sub, tool + '.py'))
			try:
				web = urlopen(url)
				if web.getcode() != 200:
					continue
			except Exception as e:
				# on python3 urlopen throws an exception
				continue
			else:
				tmp = self.root.make_node(os.sep.join((Context.waf_dir, 'waflib', 'extras', tool + '.py')))
				tmp.write(web.read())
				Logs.warn('downloaded %s from %s' % (tool, url))
				download_check(tmp)
				try:
					module = Context.load_tool(tool)
				except:
					Logs.warn('module %s from %s is unusable' % (tool, url))
					try:
						tmp.delete()
					except:
						pass
					continue
				return module
		else:
				break
		raise Errors.WafError('Could not load the Waf tool')

class ConfigurationContext(Context.Context):
	'''configures the project'''

	cmd = 'configure'

	error_handlers = []
	def __init__(self, **kw):
		super(self.__class__, self).__init__(**kw)
		self.environ = dict(os.environ)
		self.all_envs = {}

		self.top_dir = None
		self.out_dir = None

		self.tools = [] # tools loaded in the configuration, and that will be loaded when building

		self.hash = 0
		self.files = []

		self.tool_cache = []

		self.setenv('')

	def setenv(self, name, env=None):
		if not env:
			env = ConfigSet.ConfigSet()
			self.prepare_env(env)
		else:
			env = env.derive()
		self.all_envs[name] = env
		self.current_env = name

	def get_env(self):
		"""getter for the env property"""
		return self.all_envs[self.current_env]
	def set_env(self, val):
		"""setter for the env property"""
		self.all_envs[self.current_env] = val

	env = property(get_env, set_env)

	def init_dirs(self):
		"""Initializes the project directory and the build directory"""

		top = self.top_dir
		if not top:
			top = Options.options.top
		if not top:
			top = getattr(Context.g_module, Context.TOP, None)
		if not top:
			top = self.path.abspath()
		top = os.path.abspath(top)

		self.srcnode = (os.path.isabs(top) and self.root or self.path).find_dir(top)
		assert(self.srcnode)

		out = self.out_dir
		if not out:
			out = Options.options.out
		if not out:
			out = getattr(Context.g_module, Context.OUT, None)
		if not out:
			out = Options.lockfile.replace('.lock-waf', '')

		self.bldnode = (os.path.isabs(out) and self.root or self.path).make_node(out)
		self.bldnode.mkdir()

		if not os.path.isdir(self.bldnode.abspath()):
			conf.fatal('could not create the build directory %s' % self.bldnode.abspath())

	def execute(self):
		"""See Context.prepare"""
		self.init_dirs()

		self.cachedir = self.bldnode.make_node(Build.CACHE_DIR)
		self.cachedir.mkdir()

		path = os.path.join(self.bldnode.abspath(), WAF_CONFIG_LOG)
		self.logger = Logs.make_logger(path, 'cfg')

		app = getattr(Context.g_module, 'APPNAME', '')
		if app:
			ver = getattr(Context.g_module, 'VERSION', '')
			if ver:
				app = "%s (%s)" % (app, ver)

		now = time.ctime()
		pyver = sys.hexversion
		systype = sys.platform
		args = " ".join(sys.argv)
		wafver = Context.WAFVERSION
		abi = Context.ABI
		self.to_log(conf_template % vars())

		self.msg('Setting top to', self.srcnode.abspath())
		self.msg('Setting out to', self.bldnode.abspath())

		if id(self.srcnode) == id(self.bldnode):
			Logs.warn('setting top == out')
		elif id(self.path) != id(self.srcnode):
			if self.srcnode.is_child_of(self.path):
				Logs.warn('Using an uncommon top directory')

		super(ConfigurationContext, self).execute()

		self.store()

		Context.top_dir = self.srcnode.abspath()
		Context.out_dir = self.bldnode.abspath()

		# this will write a configure lock so that subsequent builds will
		# consider the current path as the root directory (see prepare_impl).
		# to remove: use 'waf distclean'
		env = ConfigSet.ConfigSet()
		env['argv'] = sys.argv
		env['options'] = Options.options.__dict__

		env.run_dir = Context.run_dir
		env.top_dir = Context.top_dir
		env.out_dir = Context.out_dir

		# conf.hash & conf.files hold wscript files paths and hash
		# (used only by Configure.autoconfig)
		env['hash'] = self.hash
		env['files'] = self.files
		env['environ'] = dict(self.environ)

		env.store(Context.run_dir + os.sep + Options.lockfile)
		env.store(Context.top_dir + os.sep + Options.lockfile)
		env.store(Context.out_dir + os.sep + Options.lockfile)

	def prepare_env(self, env):
		"""insert various variables in the environment"""
		if not env.PREFIX:
			env.PREFIX = os.path.abspath(os.path.expanduser(Options.options.prefix))
		if not env.BINDIR:
			env.BINDIR = Utils.subst_vars('${PREFIX}/bin', env)
		if not env.LIBDIR:
			env.LIBDIR = Utils.subst_vars('${PREFIX}/lib', env)

	def store(self):
		"""Saves the config results into the cache file"""
		n = self.cachedir.make_node('build.config.py')
		n.write('version = 0x%x\ntools = %r\n' % (Context.HEXVERSION, self.tools))

		if not self.all_envs:
			self.fatal('nothing to store in the configuration context!')

		for key in self.all_envs:
			tmpenv = self.all_envs[key]
			tmpenv.store(os.path.join(self.cachedir.abspath(), key + Build.CACHE_SUFFIX))

	def load(self, input, tooldir=None, funs=None, download=True):
		"loads a waf tool"

		tools = Utils.to_list(input)
		if tooldir: tooldir = Utils.to_list(tooldir)
		for tool in tools:
			# avoid loading the same tool more than once with the same functions
			# used by composite projects

			mag = (tool, id(self.env), funs)
			if mag in self.tool_cache:
				self.to_log('(tool %s is already loaded, skipping)' % tool)
				continue
			self.tool_cache.append(mag)

			module = None
			try:
				module = Context.load_tool(tool, tooldir)
			except ImportError as e:
				if Options.options.download:
					module = download_tool(tool)
					if not module:
						self.fatal('Could not load the Waf tool %r or download a suitable replacement from the repository (sys.path %r)\n%s' % (tool, sys.path, e))
				else:
					self.fatal('Could not load the Waf tool %r from %r (try the --download option?):\n%s' % (tool, sys.path, e))
			except Exception as e:
				self.to_log('imp %r (%r & %r)' % (tool, tooldir, funs))
				self.to_log(Utils.ex_stack())
				raise

			if funs is not None:
				self.eval_rules(funs)
			else:
				func = getattr(module, 'configure', None)
				if func:
					if type(func) is type(Utils.readf): func(self)
					else: self.eval_rules(func)

			self.tools.append({'tool':tool, 'tooldir':tooldir, 'funs':funs})

	def post_recurse(self, node):
		"""records the path and a hash of the scripts visited, see Context.post_recurse"""
		super(ConfigurationContext, self).post_recurse(node)
		self.hash = hash((self.hash, node.read('rb')))
		self.files.append(node.abspath())

	def add_os_flags(self, var, dest=None):
		"""Imports operating system environment values into an env dict"""
		# do not use 'get' to make certain the variable is not defined
		try: self.env.append_value(dest or var, Utils.to_list(self.environ[var]))
		except KeyError: pass

	def cmd_to_list(self, cmd):
		"""Detects if a command is written in pseudo shell like 'ccache g++'"""
		if isinstance(cmd, str) and cmd.find(' '):
			try:
				os.stat(cmd)
			except OSError:
				return shlex.split(cmd)
			else:
				return [cmd]
		return cmd

	def eval_rules(self, rules):
		"""Executes the configuration tests"""
		self.rules = Utils.to_list(rules)
		for x in self.rules:
			f = getattr(self, x)
			if not f: self.fatal("No such method '%s'." % x)
			try:
				f()
			except Exception as e:
				ret = self.err_handler(x, e)
				if ret == BREAK:
					break
				elif ret == CONTINUE:
					continue
				else:
					raise

	def err_handler(self, fun, error):
		"""error handler for the configuration tests, the default is to let the exceptions rise"""
		pass

def conf(f):
	"decorator: attach new configuration functions"
	def fun(*k, **kw):
		mandatory = True
		if 'mandatory' in kw:
			mandatory = kw['mandatory']
			del kw['mandatory']

		try:
			return f(*k, **kw)
		except Errors.ConfigurationError as e:
			if mandatory:
				raise e

	setattr(ConfigurationContext, f.__name__, fun)
	setattr(Build.BuildContext, f.__name__, fun)
	return f

@conf
def check_waf_version(self, mini='1.6.0', maxi='1.7.0'):
	"""
	check for the waf version

	Versions should be supplied as hex. 0x01000000 means 1.0.0,
	0x010408 means 1.4.8, etc.

	@type  mini: number, tuple or string
	@param mini: Minimum required version
	@type  maxi: number, tuple or string
	@param maxi: Maximum allowed version
	"""
	self.start_msg('Checking for waf version in %s-%s' % (str(mini), str(maxi)))
	ver = Context.HEXVERSION
	if Utils.num2ver(mini) > ver:
		conf.fatal('waf version should be at least %r (%r found)' % (mini, ver))

	if Utils.num2ver(maxi) < ver:
		conf.fatal('waf version should be at most %r (%r found)' % (maxi, ver))
	self.end_msg('ok')

@conf
def find_file(self, filename, path_list=[]):
	"""finds a file in a list of paths
	@param filename: name of the file to search for
	@param path_list: list of directories to search
	@return: the first occurrence filename or '' if filename could not be found
	"""
	for n in Utils.to_list(filename):
		for d in Utils.to_list(path_list):
			p = os.path.join(d, n)
			if os.path.exists(p):
				return p
	self.fatal('Could not find %r' % filename)

@conf
def find_program(self, filename, **kw):
	"""
	Search for a program on the operating system
	Additional arguments in kw:
	* path_list: list of paths to look into
	* var: store the result to conf.env[var], by default use filename.upper()
	* ext: list of extensions for the binary (do not forget the empty extension)

	when var is used, you may set os.environ[var] to help finding a specific program version, for example
	$ VALAC=/usr/bin/valac_test waf configure
	"""

	exts = kw.get('exts', Options.platform == 'win32' and '.exe,.com,.bat,.cmd' or ',.sh,.pl,.py')

	environ = kw.get('environ', os.environ)

	ret = ''
	filename = Utils.to_list(filename)

	var = kw.get('var', '')
	if not var:
		var = filename[0].upper()

	if self.env[var]:
		ret = self.env[var]
	elif var in environ:
		ret = environ[var]

	path_list = kw.get('path_list', '')
	if not ret:
		if path_list:
			path_list = Utils.to_list(path_list)
		else:
			path_list = environ.get('PATH', '').split(os.pathsep)

		if not isinstance(filename, list):
			filename = [filename]

		for a in exts.split(','):
			if ret:
				break
			for b in filename:
				if ret:
					break
				for c in path_list:
					if ret:
						break
					x = os.path.join(c, b + a)
					if os.path.isfile(x):
						ret = x

	self.msg('Checking for program ' + ','.join(filename), ret or False)
	self.to_log('find program=%r paths=%r var=%r -> %r' % (filename, path_list, var, ret))

	if not ret:
		self.fatal(kw.get('errmsg', '') or 'Could not find the program %s' % ','.join(filename))

	if var:
		self.env[var] = ret
	return ret


@conf
def find_perl_program(self, filename, path_list=[], var=None, environ=None, exts=''):
	"""Search for a program on the operating system"""

	try:
		app = self.find_program(filename, path_list=path_list, var=var, environ=environ, exts=exts)
	except:
		perl = self.find_program('perl', var='PERL')
		app = self.find_file(filename, os.environ['PATH'].split(os.pathsep))
		if not app:
			raise
		if var:
			self.env[var] = Utils.to_list(self.env['PERL']) + [app]
	self.msg('Checking for %r' % filename, app)

