#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Module called for configuring, compiling and installing targets"

import sys
if sys.hexversion<0x206000f:
	raise ImportError('Waf 1.6 requires Python >= 2.6 (the source directory)')

import os, shutil, traceback, datetime, inspect, errno, subprocess
from waflib import Utils, Configure, Logs, Options, ConfigSet, Context, Errors, Build

g_gz = 'bz2'

build_dir_override = None

no_climb_commands = ['configure']

def waf_entry_point(current_directory, version, wafdir):
	"""This is the main entry point, all Waf execution starts here."""

	Logs.init_log()

	if Context.WAFVERSION != version:
		Logs.error('Waf script %r and library %r do not match (directory %r)' % (version, WAFVERSION, wafdir))
		sys.exit(1)

	Context.waf_dir = wafdir
	Context.launch_dir = current_directory

	# try to find a lock file (if the project was configured)
	# at the same time, store the first wscript file seen
	cur = current_directory
	while cur:
		lst = os.listdir(cur)
		if Options.lockfile in lst:
			env = ConfigSet.ConfigSet()
			try:
				env.load(os.path.join(cur, Options.lockfile))
			except Exception:
				continue

			Context.run_dir = env.run_dir
			Context.top_dir = env.top_dir
			Context.out_dir = env.out_dir

			break

		if not Context.run_dir:
			if Context.WSCRIPT_FILE in lst:
				Context.run_dir = cur

		next = os.path.dirname(cur)
		if next == cur:
			break
		cur = next

		# if 'configure' is in the commands, do not search any further
		for k in no_climb_commands:
			if k in sys.argv:
				break
		else:
			continue
		break


	if not Context.run_dir:
		if '-h' in sys.argv or '--help' in sys.argv:
			Logs.warn('No wscript file found: the help message may be incomplete')
			opt_obj = Options.OptionsContext()
			opt_obj.curdir = current_directory
			opt_obj.parse_args()
			sys.exit(0)
		elif '--version' in sys.argv:
			opt_obj = Options.OptionsContext()
			opt_obj.curdir = current_directory
			opt_obj.parse_args()
			sys.exit(0)
		Logs.error('Waf: Run from a directory containing a file named %r' % Context.WSCRIPT_FILE)
		sys.exit(1)

	try:
		os.chdir(Context.run_dir)
	except OSError:
		Logs.error('Waf: The folder %r is unreadable' % Context.run_dir)
		sys.exit(1)

	try:
		set_main_module(Context.run_dir + os.sep + Context.WSCRIPT_FILE)
	except Errors.WafError as e:
		Logs.pprint('RED', e.verbose_msg)
		Logs.error(str(e))
		sys.exit(1)
	except Exception as e:
		Logs.error('Waf: The wscript in %r is unreadable' % Context.run_dir, e)
		traceback.print_exc(file=sys.stdout)
		sys.exit(2)

	parse_options()

	"""
	import cProfile, pstats
	cProfile.runctx("import Scripting; Scripting.run_commands()", {}, {}, 'profi.txt')
	p = pstats.Stats('profi.txt')
	p.sort_stats('time').print_stats(25)
	"""
	try:
		run_commands()
	except Errors.WafError as e:
		if Logs.verbose:
			Logs.pprint('RED', e.verbose_msg)
		Logs.error(e.msg)
		sys.exit(1)
	except Exception as e:
		traceback.print_exc(file=sys.stdout)
		sys.exit(2)
	except KeyboardInterrupt:
		Logs.pprint('RED', 'Interrupted')
		sys.exit(68)
	#"""

def set_main_module(file_path):
	"Load custom options, if defined"
	Context.g_module = Context.load_module(file_path)
	Context.g_module.root_path = file_path

	# note: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

	def set_def(obj):
		name = obj.__name__
		if not name in Context.g_module.__dict__:
			setattr(Context.g_module, name, obj)
	for k in [update, dist, distclean, distcheck]:
		set_def(k)
	# add dummy init and shutdown functions if they're not defined
	if not 'init' in Context.g_module.__dict__:
		Context.g_module.init = Utils.nada
	if not 'shutdown' in Context.g_module.__dict__:
		Context.g_module.shutdown = Utils.nada
	if not 'options' in Context.g_module.__dict__:
		Context.g_module.options = Utils.nada

def parse_options():
	opt = Options.OptionsContext().call_execute()

	if not Options.commands:
		Options.commands = ['build']

	# process some internal Waf options
	Logs.verbose = Options.options.verbose
	Logs.init_log()

	if Options.options.zones:
		Logs.zones = Options.options.zones.split(',')
		if not Logs.verbose:
			Logs.verbose = 1
	elif Logs.verbose > 0:
		Logs.zones = ['runner']

	if Logs.verbose > 2:
		Logs.zones = ['*']

def run_command(cmd_name):
	"""Run a command like it was invoked from the command line."""
	ctx = Context.create_context(cmd_name)
	ctx.options = Options.options # provided for convenience
	ctx.cmd = cmd_name
	ctx.call_execute()
	return ctx

def run_commands():
	run_command('init')
	while Options.commands:
		cmd_name = Options.commands.pop(0)

		timer = Utils.Timer()
		run_command(cmd_name)
		if not Options.options.progress_bar:
			elapsed = ' (%s)' % str(timer)
			Logs.info('%r finished successfully%s' % (cmd_name, elapsed))
	run_command('shutdown')

###########################################################################################

excludes = '.bzr .bzrignore .git .gitignore .svn CVS .cvsignore .arch-ids {arch} SCCS BitKeeper .hg _MTN _darcs Makefile Makefile.in config.log'.split()
dist_exts = '~ .rej .orig .pyc .pyo .bak .tar.bz2 tar.gz .zip .swp'.split()
def dont_dist(name, src, build_dir):
	global excludes, dist_exts

	if (name.startswith(',,')
		or name.startswith('++')
		or name.startswith('.waf-1.')
		or (src == '.' and name == Options.lockfile)
		or name in excludes
		or name == build_dir
		):
		return True

	for ext in dist_exts:
		if name.endswith(ext):
			return True

	return False

# like shutil.copytree
# exclude files and to raise exceptions immediately
def copytree(src, dst, build_dir):
	names = os.listdir(src)
	os.makedirs(dst)
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)

		if dont_dist(name, src, build_dir):
			continue

		if os.path.isdir(srcname):
			copytree(srcname, dstname, build_dir)
		else:
			shutil.copy2(srcname, dstname)

def _can_distclean(name):
	"""
	this method can change anytime and without prior notice
	"""
	for k in '.o .moc .exe'.split():
		if name.endswith(k):
			return True
	return False

def distclean_dir(dirname):
	"""
	called when top==out
	"""
	for (root, dirs, files) in os.walk(dirname):
		for f in files:
			if _can_distclean(f):
				fname = root + os.sep + f
				try:
					os.unlink(fname)
				except:
					Logs.warn('could not remove %r' % fname)

	for x in [DBFILE, 'config.log']:
		try:
			os.unlink(x)
		except:
			pass

	try:
		shutil.rmtree('c4che')
	except:
		pass

def distclean(ctx):
	'''removes the build directory'''
	lst = os.listdir('.')
	for f in lst:
		if f == Options.lockfile:
			try:
				proj = ConfigSet.ConfigSet(f)
			except:
				Logs.warn('could not read %r' % f)
				continue

			if proj['out_dir'] != proj['top_dir']:
				try:
					shutil.rmtree(proj['out_dir'])
				except IOError:
					pass
				except OSError as e:
					if e.errno != errno.ENOENT:
						Logs.warn('project %r cannot be removed' % proj[Context.OUT])
			else:
				distclean_dir(proj['out_dir'])

			for k in (proj['out_dir'], proj['top_dir'], proj['run_dir']):
				try:
					os.remove(os.path.join(k, Options.lockfile))
				except OSError as e:
					if e.errno != errno.ENOENT:
						Logs.warn('file %r cannot be removed' % f)

		# remove the local waf cache
		if f.startswith('.waf-') and not Options.commands:
			shutil.rmtree(f, ignore_errors=True)

def dist(ctx):
	'''makes a tarball for redistributing the sources'''
	import tarfile

	appname = getattr(Context.g_module, Context.APPNAME, 'noname')
	version = getattr(Context.g_module, Context.VERSION, '1.0')

	tmp_folder = appname + '-' + version
	arch_name = tmp_folder+'.tar.'+g_gz

	# remove the previous dir
	try:
		shutil.rmtree(tmp_folder)
	except (OSError, IOError):
		pass

	# remove the previous archive
	try:
		os.remove(arch_name)
	except (OSError, IOError):
		pass

	# copy the files into the temporary folder
	copytree('.', tmp_folder, getattr(Context.g_module, Context.OUT, None))

	# undocumented hook for additional cleanup
	dist_hook = getattr(Context.g_module, 'dist_hook', None)
	if dist_hook:
		back = os.getcwd()
		os.chdir(tmp_folder)
		try:
			dist_hook()
		finally:
			# go back to the root directory
			os.chdir(back)

	tar = tarfile.open(arch_name, 'w:' + g_gz)
	tar.add(tmp_folder)
	tar.close()

	from hashlib import sha1
	try:
		digest = " (sha=%r)" % sha1(Utils.readf(arch_name)).hexdigest()
	except:
		digest = ''

	Logs.info('New archive created: %s%s' % (arch_name, digest))

	if os.path.exists(tmp_folder): shutil.rmtree(tmp_folder)
	return arch_name

def distcheck(ctx):
	'''checks if the project compiles (tarball from 'dist')'''
	import tempfile, tarfile

	appname = getattr(Context.g_module, Context.APPNAME, 'noname')
	version = getattr(Context.g_module, Context.VERSION, '1.0')

	waf = os.path.abspath(sys.argv[0])
	tarball = Context.g_module.dist(ctx)
	t = tarfile.open(tarball)
	for x in t: t.extract(x)
	t.close()

	path = appname + '-' + version

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	ret = subprocess.Popen([waf, 'configure', 'install', 'uninstall', '--destdir=' + instdir], cwd=path).wait()
	if ret:
		raise Errors.WafError('distcheck failed with code %i' % ret)

	if os.path.exists(instdir):
		raise Errors.WafError('distcheck succeeded, but files were left in %s' % instdir)

	shutil.rmtree(path)

def update(ctx):

	lst = os.listdir(Context.waf_dir + '/waflib/extras')
	for x in lst:
		if not x.endswith('.py'):
			continue
		tool = x.replace('.py', '')
		Configure.download_tool(tool, force=True)

def autoconfigure(execute_method):
	"""decorator, sets the commands that can be autoconfigured automatically"""
	def execute(self):
		if not Configure.autoconfig:
			return execute_method(self)

		env = ConfigSet.ConfigSet()
		do_config = False
		try:
			env.load(os.path.join(Context.top_dir, Options.lockfile))
		except Exception as e:
			Logs.warn('Configuring the project')
			do_config = True
		else:
			h = 0
			for f in env['files']:
				h = hash((h, Utils.readf(f, 'rb')))
			do_config = h != env.hash

		if do_config:
			Options.commands.insert(0, self.cmd)
			Options.commands.insert(0, 'configure')
			return

		return execute_method(self)
	return execute

Build.BuildContext.execute = autoconfigure(Build.BuildContext.execute)

