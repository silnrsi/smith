#!/usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)
# Thomas Nagy, 2006-2010 (ita)

"""
Support for waf command-line options

Provides default command-line options,
as well as custom ones, used by the ``options`` wscript function.

"""

import os, types, tempfile, optparse, sys
from waflib import Logs, Utils, Context

cmds = 'distclean configure build install clean uninstall check dist distcheck'.split()
"""
Constant representing the default waf commands displayed in::

	$ waf --help

"""

options = {}
"""
A dictionary representing the command-line options::

	$ waf --foo=bar

"""

commands = []
"""
List of commands to execute extracted from the command-line. This list is consumed during the execution, see :py:func:`waflib.Scripting.run_commands`.
"""

lockfile = os.environ.get('WAFLOCK', '.lock-wafbuild')
try: cache_global = os.path.abspath(os.environ['WAFCACHE'])
except KeyError: cache_global = ''
platform = Utils.unversioned_sys_platform()


class opt_parser(optparse.OptionParser):
	"""
	Command-line option parser
	"""
	def __init__(self, ctx):
		optparse.OptionParser.__init__(self, conflict_handler="resolve", version='waf %s (%s)' % (Context.WAFVERSION, Context.WAFREVISION))

		self.formatter.width = Logs.get_term_cols()
		p = self.add_option
		self.ctx = ctx

		jobs = ctx.jobs()
		p('-j', '--jobs',     dest='jobs',    default=jobs, type='int', help='amount of parallel jobs (%r)' % jobs)
		p('-k', '--keep',     dest='keep',    default=False, action='store_true', help='keep running happily on independent task groups')
		p('-v', '--verbose',  dest='verbose', default=0,     action='count', help='verbosity level -v -vv or -vvv [default: 0]')
		p('--nocache',        dest='nocache', default=False, action='store_true', help='ignore the WAFCACHE (if set)')
		p('--zones',          dest='zones',   default='',    action='store', help='debugging zones (task_gen, deps, tasks, etc)')

		gr = optparse.OptionGroup(self, 'configure options')
		self.add_option_group(gr)

		gr.add_option('-o', '--out', action='store', default='', help='build dir for the project', dest='out')
		gr.add_option('-t', '--top', action='store', default='', help='src dir for the project', dest='top')

		default_prefix = os.environ.get('PREFIX')
		if not default_prefix:
			if platform == 'win32':
				d = tempfile.gettempdir()
				default_prefix = d[0].upper() + d[1:]
				# win32 preserves the case, but gettempdir does not
			else:
				default_prefix = '/usr/local/'
		gr.add_option('--prefix', dest='prefix', default=default_prefix, help='installation prefix [default: %r]' % default_prefix)
		gr.add_option('--download', dest='download', default=False, action='store_true', help='try to download the tools if missing')


		gr = optparse.OptionGroup(self, 'build and install options')
		self.add_option_group(gr)

		gr.add_option('-p', '--progress', dest='progress_bar', default=0, action='count', help= '-p: progress bar; -pp: ide output')
		gr.add_option('--targets',        dest='targets', default='', action='store', help='task generators, e.g. "target1,target2"')

		gr = optparse.OptionGroup(self, 'step options')
		self.add_option_group(gr)
		gr.add_option('--files',          dest='files', default='', action='store', help='files to process, by regexp, e.g. "*/main.c,*/test/main.o"')

		default_destdir = os.environ.get('DESTDIR', '')
		gr = optparse.OptionGroup(self, 'install/uninstall options')
		self.add_option_group(gr)
		gr.add_option('--destdir', help='installation root [default: %r]' % default_destdir, default=default_destdir, dest='destdir')
		gr.add_option('-f', '--force', dest='force', default=False, action='store_true', help='force file installation')

	def get_usage(self):
		"""
		Return the message to print on ``waf --help``
		"""
		cmds_str = {}
		for cls in Context.classes:
			if not cls.cmd:
				continue

			s = cls.__doc__ or ''
			cmds_str[cls.cmd] = s

		if Context.g_module:
			for (k, v) in Context.g_module.__dict__.items():
				if k in ['options', 'init', 'shutdown']:
					continue

				if type(v) is type(Context.create_context):
					if v.__doc__ and not k.startswith('_'):
						cmds_str[k] = v.__doc__

		just = 0
		for k in cmds_str:
			just = max(just, len(k))

		lst = ['  %s: %s' % (k.ljust(just), v) for (k, v) in cmds_str.items()]
		lst.sort()
		ret = '\n'.join(lst)

		return '''waf [commands] [options]

Main commands (example: ./waf build -j4)
%s
''' % ret


class OptionsContext(Context.Context):
	"""
	Collects custom options from wscript files and parses the command line.

	Sets the global Options.commands and Options.options attributes.
	
	"""

	cmd = ''
	fun = 'options'

	def __init__(self, **kw):
		"""
		Holds an instance of opt_parser in self.parser
		"""
		super(self.__class__, self).__init__(**kw)
		self.parser = opt_parser(self)

	def jobs(self):
		"""
		Finds the amount of threads to use

		Unless specified, waf tries to use the number of CPU cores.

		"""
		count = int(os.environ.get('JOBS', 0))
		if count < 1:
			if sys.platform == 'win32':
				# on Windows, use the NUMBER_OF_PROCESSORS environment variable
				count = int(os.environ.get('NUMBER_OF_PROCESSORS', 1))
			else:
				# on everything else, first try the POSIX sysconf values
				if hasattr(os, 'sysconf_names'):
					if 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
						count = int(os.sysconf('SC_NPROCESSORS_ONLN'))
					elif 'SC_NPROCESSORS_CONF' in os.sysconf_names:
						count = int(os.sysconf('SC_NPROCESSORS_CONF'))
				elif os.name != 'java':
					tmp = self.cmd_and_log(['sysctl', '-n', 'hw.ncpu'])
					if re.match('^[0-9]+$', tmp):
						count = int(tmp)
		if count < 1:
			count = 1
		elif count > 1024:
			count = 1024
		return count

	def add_option(self, *k, **kw):
		"""
		Wrapper for optparse.add_option::

			def options(ctx):
				ctx.add_option('-u', '--use', dest='use', default=False, action='store_true',
					help='a boolean option')
		"""
		self.parser.add_option(*k, **kw)

	def add_option_group(self, *k, **kw):
		"""
		Wrapper for optparse.add_option_group::

			def options(ctx):
				gr = optparse.OptionGroup(self, 'special options')
				ctx.add_option_group(gr)
				gr.add_option('-u', '--use', dest='use', default=False, action='store_true')
		"""
		return self.parser.add_option_group(*k, **kw)

	def get_option_group(self, opt_str):
		"""
		Wrapper for optparse.get_option_group::

			def options(ctx):
				gr = get_option_group('configure options')
				gr.add_option('-o', '--out', action='store', default='',
					help='build dir for the project', dest='out')

		"""
		return self.parser.get_option_group(opt_str)

	def parse_args(self, _args=None):
		"""
		Parse arguments from a list (not bound to the command-line).

		:param _args: arguments
		:type _args: list of strings
		"""
		global options, commands
		(options, leftover_args) = self.parser.parse_args(args=_args)
		commands = leftover_args

		if options.destdir:
			options.destdir = os.path.abspath(os.path.expanduser(options.destdir))

		if options.verbose >= 2:
			self.load('errcheck')

	def execute(self):
		"""
		See :py:func:`waflib.Context.Context.execute`
		"""
		super(OptionsContext, self).execute()
		self.parse_args()

