#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Tasks are small objects encapsulating a state of execution

The task base (TaskBase) only has to provide the following methods:
* unique id
* signature
* runnable_status
* run
* post_run

The task class (Task) deals with the filesystem (Node) uses the following
in the computation of the signature:
* explicit dependencies (given files)
* implicit dependencies (nodes given by an optional scanner method)
* hashed data (from the data set associated)

Custom task clases may be created by subclassing or factories
"""

import os, shutil, re, tempfile
from waflib import Utils, Logs, Errors

# task states
NOT_RUN = 0
MISSING = 1
CRASHED = 2
EXCEPTION = 3
SKIPPED = 8
SUCCESS = 9

ASK_LATER = -1
SKIP_ME = -2
RUN_ME = -3

COMPILE_TEMPLATE_SHELL = '''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	wd = getattr(tsk, 'cwd', None)
	p = env.get_flat
	tsk.last_cmd = cmd = \'\'\' %s \'\'\' % s
	return tsk.exec_command(cmd, cwd=wd, env=env.env or None)
'''

COMPILE_TEMPLATE_NOSHELL = '''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	wd = getattr(tsk, 'cwd', None)
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	tsk.last_cmd = lst = []
	%s
	lst = [x for x in lst if x]
	return tsk.exec_command(lst, cwd=wd, env=env.env or None)
'''

def cache_outputs(cls):
	"""
	Task class decorator

	If bld.cache_global is defined and if the task instances produces output nodes,
	the files will be copied into a folder in the cache directory

	the files may also be retrieved from that folder, if it exists
	"""
	m1 = cls.run
	def run(self):
		bld = self.generator.bld
		if bld.cache_global and not bld.nocache:
			if self.can_retrieve_cache():
				return 0
		return m1(self)
	cls.run = run

	m2 = cls.post_run
	def post_run(self):
		bld = self.generator.bld
		ret = m2(self)
		if bld.cache_global and not bld.nocache:
			self.put_files_cache()
		return ret
	cls.post_run = post_run

	return cls


classes = {}
"class tasks created by user scripts or Waf tools are kept in this dict name -> class object"

class store_task_type(type):
	"""
	store the task types that have a name ending in _task into a map (remember the existing task types)
	the attribute 'run_str' will be processed to compute a method 'run' on the task class
	"""
	def __init__(cls, name, bases, dict):
		super(store_task_type, cls).__init__(name, bases, dict)
		name = cls.__name__

		if name.endswith('_task'):
			name = name.replace('_task', '')
		if name != 'evil' and name != 'TaskBase':
			global classes

			if getattr(cls, 'run_str', None):
				# if a string is provided, convert it to a method
				(f, dvars) = compile_fun(cls.run_str, cls.shell)
				cls.hcode = cls.run_str
				cls.run_str = None
				cls.run = f
				cls.vars.extend(dvars)
			elif getattr(cls, 'run', None) and not 'hcode' in cls.__dict__:
				# getattr(cls, 'hcode') would look in the upper classes
				cls.hcode = Utils.h_fun(cls.run)

			if not getattr(cls, 'nocache', None):
				cls = cache_outputs(cls)

			classes[name] = cls

evil = store_task_type('evil', (object,), {})
"this variable is used to avoid writing a metaclass, so the code can run in python 2.6 and 3.x unmodified"

class TaskBase(evil):
	"""Base class for all Waf tasks

	The most important methods are (by usual order of call):
	1 runnable_status: ask the task if it should be run, skipped, or if we have to ask later
	2 __str__: string to display to the user
	3 run: execute the task
	4 post_run: after the task is run, update the cache about the task

	This class should be seen as an interface, it provides the very minimum necessary for the scheduler
	so it does not do much.

	For illustration purposes, TaskBase instances try to execute self.fun (if provided)
	"""

	color = "GREEN"

	ext_in = []
	"""file extensions that objects of this task class might need"""

	ext_out = []
	"""file extensions that objects of this task class might create"""

	before = []
	"""list of task class names to execute before instances of this class"""

	after = []
	"""list of task class names to execute after instances of this class"""

	hcode = ''
	"""string representing an additional hash for the class representation"""

	def __init__(self, *k, **kw):
		"""
		The base task class requires a task generator, which will be itself if missing
		"""
		self.hasrun = NOT_RUN
		try:
			self.generator = kw['generator']
		except KeyError:
			self.generator = self

	def __repr__(self):
		"for debugging purposes"
		return '\n\t{task %r: %s %s}' % (self.__class__.__name__, id(self), str(getattr(self, "fun", "")))

	def __str__(self):
		"string to display to the user"
		if hasattr(self, 'fun'):
			return 'executing: %s\n' % self.fun.__name__
		return self.__class__.__name__ + '\n'

	def __hash__(self):
		"very fast hashing scheme but not persistent (replace/implement in subclasses and see Task.uid)"
		return id(self)

	def exec_command(self, cmd, **kw):
		"""
		'runner' zone is printed out for waf -v, see waflib/Options.py
		also, ensure that a command is always run from somewhere
		"""
		bld = self.generator.bld
		try:
			if not kw.get('cwd', None):
				kw['cwd'] = bld.cwd
		except AttributeError:
			bld.cwd = kw['cwd'] = bld.variant_dir
		return bld.exec_command(cmd, **kw)

	def runnable_status(self):
		"RUN_ME SKIP_ME or ASK_LATER"
		return RUN_ME

	def process(self):
		"""
		process a task and then put it back in the queue "master.out"
		TODO find a better name for this method
		"""
		m = self.master
		if m.stop:
			m.out.put(self)
			return

		self.generator.bld.returned_tasks.append(self)
		self.log_display(self.generator.bld)

		try:
			ret = self.run()
		except Exception as e:
			self.err_msg = Utils.ex_stack()
			self.hasrun = EXCEPTION

			# TODO cleanup
			m.error_handler(self)
			m.out.put(self)
			return

		if ret:
			self.err_code = ret
			self.hasrun = CRASHED
		else:
			try:
				self.post_run()
			except Errors.WafError:
				pass
			except Exception:
				self.err_msg = Utils.ex_stack()
				self.hasrun = EXCEPTION
			else:
				self.hasrun = SUCCESS
		if self.hasrun != SUCCESS:
			m.error_handler(self)

		m.out.put(self)

	def run(self):
		"called to execute the task"
		if hasattr(self, 'fun'):
			return self.fun(self)
		return 0

	def post_run(self):
		"update the dependency tree (node stats)"
		pass

	def log_display(self, bld):
		"write the execution status on the context logger"
		bld.to_log(self.display())

	def display(self):
		"print either the description (using __str__) or the progress bar or the ide output"
		col1 = Logs.colors(self.color)
		col2 = Logs.colors.NORMAL

		if self.generator.bld.progress_bar == 1:
			return self.generator.bld.progress_line(len(self.generator.bld.returned_tasks), self.position[1], col1, col2)

		if self.generator.bld.progress_bar == 2:
			ela = str(self.generator.bld.timer)
			try:
				ins  = ','.join([n.name for n in self.inputs])
			except AttributeError:
				ins = ''
			try:
				outs = ','.join([n.name for n in self.outputs])
			except AttributeError:
				outs = ''
			return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (self.position[1], len(self.generator.bld.returned_tasks), ins, outs, ela)

		s = str(self)
		if not s:
			return None

		total = self.position[1]
		n = len(str(total))
		fs = '[%%%dd/%%%dd] %%s%%s%%s' % (n, n)
		return fs % (len(self.generator.bld.returned_tasks), self.position[1], col1, s, col2)

	def attr(self, att, default=None):
		"retrieve an attribute from the instance or from the class (microoptimization here)"
		ret = getattr(self, att, self)
		if ret is self: return getattr(self.__class__, att, default)
		return ret

	def hash_constraints(self):
		"identify a task type for all the constraints relevant for the scheduler: precedence, file production"
		cls = self.__class__
		tup = (str(cls.before), str(cls.after), str(cls.ext_in), str(cls.ext_out))
		h = hash(tup)
		return h

	def format_error(self):
		"error message to display to the user (when a build fails)"
		msg = getattr(self, 'last_cmd', '')
		if getattr(self, "err_msg", None):
			return self.err_msg
		elif self.hasrun == CRASHED:
			try:
				return ' -> task failed (exit status %r): %r\n%r' % (self.err_code, self, msg)
			except AttributeError:
				return ' -> task failed: %r\n%r' % (self, msg)
		elif self.hasrun == MISSING:
			return ' -> missing files: %r\n%r' % (self, msg)
		else:
			return '?'

class Task(TaskBase):
	"""The parent class is quite limited, in this version:
	* file system interaction: input and output nodes
	* persistence: do not re-execute tasks that have already run
	* caching: same files can be saved and retrieved from a cache directory
	* dependencies:
	   implicit, like .c files depending on .h files
       explicit, like the input nodes or the dep_nodes
       environment variables, like the CXXFLAGS in self.env
	"""
	vars = []
	shell = False
	def __init__(self, *k, **kw):
		"""
		a task is (still) associated with a ConfigSet object, so make sure to pass an 'env'
		"""
		TaskBase.__init__(self, *k, **kw)
		self.env = kw['env']

		# inputs and outputs are nodes
		# use setters when possible
		self.inputs  = []
		self.outputs = []

		self.dep_nodes = []
		self.run_after = set([])

		# Additionally, you may define the following
		#self.dep_vars  = 'PREFIX DATADIR'

	def __str__(self):
		"string to display to the user"
		env = self.env
		src_str = ' '.join([a.nice_path(env) for a in self.inputs])
		tgt_str = ' '.join([a.nice_path(env) for a in self.outputs])
		if self.outputs: sep = ' -> '
		else: sep = ''
		return '%s: %s%s%s\n' % (self.__class__.__name__.replace('_task', ''), src_str, sep, tgt_str)

	def __repr__(self):
		"for debugging purposes"
		return "".join(['\n\t{task %r: ' % id(self), self.__class__.__name__, " ", ",".join([x.name for x in self.inputs]), " -> ", ",".join([x.name for x in self.outputs]), '}'])

	def uid(self):
		"get a unique id: hash the node paths, the class, the function"
		try:
			return self.uid_
		except AttributeError:
			"this is not a real hot zone, but we want to avoid surprizes here"
			m = Utils.md5()
			up = m.update
			up(self.__class__.__name__.encode())
			for x in self.inputs + self.outputs:
				up(x.abspath().encode())
			self.uid_ = m.digest()
			return self.uid_

	def set_inputs(self, inp):
		"access the input attribute"
		if isinstance(inp, list): self.inputs += inp
		else: self.inputs.append(inp)

	def set_outputs(self, out):
		"access the output attribute"
		if isinstance(out, list): self.outputs += out
		else: self.outputs.append(out)

	def set_run_after(self, task):
		"set (scheduler) order on another task"
		# TODO: handle list or object
		assert isinstance(task, TaskBase)
		self.run_after.add(task)

	def signature(self):
		"""
		Task signatures are stored between build executions, they are use to track the changes
		made to the input nodes (not to the outputs!). The signature hashes data from various sources:
		* files listed in the inputs (list of node objects)
		* list of nodes returned by scanner methods (when present)
		* variables/values read from task.__class__.vars/task.env

		if the signature is expected to give a different result, clear the result stored in self.cache_sig
		"""
		try: return self.cache_sig
		except AttributeError: pass

		self.m = Utils.md5()
		self.m.update(self.hcode.encode())

		# explicit deps
		self.sig_explicit_deps()

		# env vars
		self.sig_vars()

		# implicit deps / scanner results
		if self.scan:
			try:
				imp_sig = self.sig_implicit_deps()
			except Errors.TaskRescan:
				return self.signature()

		ret = self.cache_sig = self.m.digest()
		return ret

	def runnable_status(self):
		"return a status to tell if the task must be executed or not, see the constants SKIP_ME RUN_ME or ASK_LATER"
		#return 0 # benchmarking

		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER

		env = self.env
		bld = self.generator.bld

		# first compute the signature
		try:
			new_sig = self.signature()
		except Errors.TaskNotReady:
			return ASK_LATER

		# compare the signature to a signature computed previously
		key = self.uid()
		try:
			prev_sig = bld.task_sigs[key]
		except KeyError:
			Logs.debug("task: task %r must run as it was never run before or the task code changed" % self)
			return RUN_ME

		# compare the signatures of the outputs
		for node in self.outputs:
			try:
				if node.sig != new_sig:
					return RUN_ME
			except AttributeError:
				Logs.debug("task: task %r must run as the output nodes do not exist" % self)
				return RUN_ME

		if new_sig != prev_sig:
			return RUN_ME
		return SKIP_ME

	def post_run(self):
		"""
		The method post_run is called after the task is executed successfully
		It stores the task signature as signature for the output nodes
		the output nodes may also get the signature of the file contents (a bit slower),
		a decorator method is provided to provide this behaviour to classes
		"""
		bld = self.generator.bld
		env = self.env
		sig = self.signature()

		for node in self.outputs:
			# check if the node exists ..
			try:
				os.stat(node.abspath())
			except OSError:
				self.hasrun = MISSING
				self.err_msg = '-> missing file: %r' % node.abspath()
				raise Errors.WafError(self.err_msg)

			# important, store the signature for the next run
			node.sig = sig

		bld.task_sigs[self.uid()] = self.cache_sig

	def sig_explicit_deps(self):
		"""
		Used by Task.signature, hash the input nodes, and perhaps other direct dependencies
		"""
		bld = self.generator.bld
		upd = self.m.update

		# the inputs
		for x in self.inputs + self.dep_nodes:
			try:
				upd(x.get_bld_sig())
			except (AttributeError, TypeError):
				raise Errors.WafError('Missing node signature for %r (required by %r)' % (x, self))

		# manual dependencies, they can slow down the builds
		if bld.deps_man:
			additional_deps = bld.deps_man
			for x in self.inputs + self.outputs:
				try:
					d = additional_deps[id(x)]
				except KeyError:
					continue

				for v in d:
					if isinstance(v, bld.root.__class__):
						try:
							v = v.get_bld_sig()
						except AttributeError:
							raise Errors.WafError('Missing node signature for %r (required by %r)' % (v, self))
					elif hasattr(v, '__call__'):
						v = v() # dependency is a function, call it
					upd(v)

		return self.m.digest()

	def sig_vars(self):
		"""
		Used by Task.signature, hash self.env variables/values
		"""
		bld = self.generator.bld
		env = self.env
		upd = self.m.update

		# dependencies on the environment vars
		act_sig = bld.hash_env_vars(env, self.__class__.vars)
		upd(act_sig)

		# additional variable dependencies, if provided
		dep_vars = getattr(self, 'dep_vars', None)
		if dep_vars:
			upd(bld.hash_env_vars(env, dep_vars))

		return self.m.digest()

	scan = None
	"""this method, when provided, returns a tuple containing:
	* a list of nodes corresponding to real files
	* a list of names for files not found in path_lst
	example:

	def scan(self, node):
		return ((), ())
	"""

	def sig_implicit_deps(self):
		"""
		Used by Task.signature.
		A special exception is thrown if a file has changed. When this occurs, Task.signature is called
		once again, and this method will be executed once again to execute Task.scan for dependencies
		"""

		bld = self.generator.bld

		# get the task signatures from previous runs
		key = self.uid()
		prev = bld.task_sigs.get((key, 'imp'), [])

		# for issue #379
		if prev:
			try:
				if prev == self.compute_sig_implicit_deps():
					return prev
			except IOError: # raised if a file was renamed
				pass
			del bld.task_sigs[(key, 'imp')]
			raise Errors.TaskRescan('rescan')

		# no previous run or the signature of the dependencies has changed, rescan the dependencies
		(nodes, names) = self.scan()
		if Logs.verbose:
			Logs.debug('deps: scanner for %s returned %s %s' % (str(self), str(nodes), str(names)))

		# store the dependencies in the cache
		bld.node_deps[key] = nodes
		bld.raw_deps[key] = names

		# might happen
		self.are_implicit_nodes_ready()

		# recompute the signature and return it
		bld.task_sigs[(key, 'imp')] = sig = self.compute_sig_implicit_deps()
		return sig

	def compute_sig_implicit_deps(self):
		"""
		it is intended for .cpp and inferred .h files
		there is a single list (no tree traversal)
		this is a hot spot so ... do not touch
		"""

		upd = self.m.update

		bld = self.generator.bld
		env = self.env

		self.are_implicit_nodes_ready()

		try:
			for k in bld.node_deps.get(self.uid(), []):
				# can do an optimization here
				upd(k.get_bld_sig())
		except AttributeError:
			# do it again to display a meaningful error message
			nodes = []
			for k in bld.node_deps.get(self.uid(), []):
				try:
					k.get_bld_sig()
				except AttributeError:
					nodes.append(k)
			raise Errors.WafError('Missing node signature for %r (for implicit dependencies %r)' % (nodes, self))

		return self.m.digest()

	def are_implicit_nodes_ready(self):
		"""
		For each node returned by the scanner, see if there is a task behind it, and force the build order

		The performance impact on null builds is nearly invisible (1.66s->1.86s)
		yet, it would not work without caching (1.86s->28s)

		On a full build, the consequence of leaving waf figure out the build order can be visible,
		for example, the preprocesor time can increase the build from 1m36s -> 2m13s
		"""
		bld = self.generator.bld
		try:
			cache = bld.dct_implicit_nodes
		except:
			bld.dct_implicit_nodes = cache = {}

		try:
			dct = cache[bld.cur]
		except KeyError:
			dct = cache[bld.cur] = {}
			for tsk in bld.cur_tasks:
				for x in tsk.outputs:
					dct[x] = tsk

		modified = False
		for x in bld.node_deps.get(self.uid(), []):
			if x in dct:
				self.run_after.add(dct[x])
				modified = True

		if modified:
			for tsk in self.run_after:
				if not tsk.hasrun:
					#print "task is not ready..."
					raise Errors.TaskNotReady('not ready')

	def can_retrieve_cache(self):
		"""
		used by cache_outputs, see above

		Retrieve build nodes from the cache
		update the file timestamps to help cleaning the least used entries from the cache
		additionally, set an attribute 'cached' to avoid re-creating the same cache files

		suppose there are files in cache/dir1/file1 and cache/dir2/file2
		first, read the timestamp of dir1
		then try to copy the files
		then look at the timestamp again, if it has changed, the data may have been corrupt (cache update by another process)
		should an exception occur, ignore the data
		"""

		if not getattr(self, 'outputs', None):
			return None

		env = self.env
		sig = self.signature()
		ssig = Utils.to_hex(sig)

		# first try to access the cache folder for the task
		dname = os.path.join(self.generator.bld.cache_global, ssig)
		try:
			t1 = os.stat(dname).st_mtime
		except OSError:
			return None

		for node in self.outputs:
			orig = os.path.join(dname, node.name)
			try:
				shutil.copy2(orig, node.abspath())
				# mark the cache file as used recently (modified)
				os.utime(orig, None)
			except (OSError, IOError):
				Logs.debug('task: failed retrieving file')
				return None

		# is it the same folder?
		try:
			t2 = os.stat(dname).st_mtime
		except OSError:
			return None

		if t1 != t2:
			return None

		for node in self.outputs:
			node.sig = sig
			if self.generator.bld.progress_bar < 1:
				self.generator.bld.to_log('restoring from cache %r\n' % node.abspath())

		self.cached = True
		return True

	def put_files_cache(self):
		"""used by cache_outputs, see above"""

		# file caching, if possible
		# try to avoid data corruption as much as possible
		if getattr(self, 'cached', None):
			return None

		sig = self.signature()
		ssig = Utils.to_hex(sig)
		dname = os.path.join(self.generator.bld.cache_global, ssig)
		tmpdir = tempfile.mkdtemp(prefix=self.generator.bld.cache_global + os.sep + 'waf')

		try:
			shutil.rmtree(dname)
		except:
			pass

		try:
			for node in self.outputs:
				dest = os.path.join(tmpdir, node.name)
				shutil.copy2(node.abspath(), dest)
		except (OSError, IOError):
			try:
				shutil.rmtree(tmpdir)
			except:
				pass
		else:
			try:
				os.rename(tmpdir, dname)
			except OSError:
				try:
					shutil.rmtree(tmpdir)
				except:
					pass
			else:
				try:
					os.chmod(dname, Utils.O755)
				except:
					pass

def is_before(t1, t2):
	"""
	return non-zero if task class t1 is to be executed before task class t2
	t1.ext_out = '.h' and t2.ext_in = '.h'
	t2.after = ['t1']
	t1.before = ['t2']
	"""
	to_list = Utils.to_list
	for k in to_list(t2.ext_in):
		if k in to_list(t1.ext_out):
			return 1

	if t1.__class__.__name__ in to_list(t2.after):
		return 1

	if t2.__class__.__name__ in to_list(t1.before):
		return 1

	return 0

def set_file_constraints(tasks):
	"adds tasks to the task 'run_after' attribute based on the task inputs and outputs"
	ins = Utils.defaultdict(set)
	outs = Utils.defaultdict(set)
	for x in tasks:
		for a in getattr(x, 'inputs', []) + getattr(x, 'dep_nodes', []):
			ins[id(a)].add(x)
		for a in getattr(x, 'outputs', []):
			outs[id(a)].add(x)

	links = set(ins.keys()).intersection(outs.keys())
	for k in links:
		for a in ins[k]:
			a.run_after.update(outs[k])

def set_precedence_constraints(tasks):
	"adds tasks to the task 'run_after' attribute based on the after/before/ext_out/ext_in attributes"
	cstr_groups = Utils.defaultdict(list)
	for x in tasks:
		h = x.hash_constraints()
		cstr_groups[h].append(x)

	keys = list(cstr_groups.keys())
	maxi = len(keys)

	# this list should be short
	for i in range(maxi):
		t1 = cstr_groups[keys[i]][0]
		for j in range(i + 1, maxi):
			t2 = cstr_groups[keys[j]][0]

			# add the constraints based on the comparisons
			if is_before(t1, t2):
				a = i
				b = j
			elif is_before(t2, t1):
				a = j
				b = i
			else:
				continue
			for x in cstr_groups[keys[b]]:
				x.run_after.update(cstr_groups[keys[a]])

def funex(c):
	"""compile a function by 'exec', return the result"""
	dc = {}
	exec(c, dc)
	return dc['f']

reg_act = re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})", re.M)
def compile_fun_shell(line):
	"""
	create a compiled function to execute a process without the shell
	WARNING: this method may disappear anytime, so use compile_fun instead
	"""

	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('backslash'): return '\\\\'
		elif g('subst'): extr.append((g('var'), g('code'))); return "%s"
		return None

	line = reg_act.sub(repl, line) or line

	parm = []
	dvars = []
	app = parm.append
	for (var, meth) in extr:
		if var == 'SRC':
			if meth: app('tsk.inputs%s' % meth)
			else: app('" ".join([a.path_from(bld.bldnode) for a in tsk.inputs])')
		elif var == 'TGT':
			if meth: app('tsk.outputs%s' % meth)
			else: app('" ".join([a.path_from(bld.bldnode) for a in tsk.outputs])')
		elif meth:
			if meth.startswith(':'):
				app('" ".join([env[%r] %% x for x in env[%r]])' % (var, meth[1:]))
				dvars.extend([var, meth[1:]])
			else:
				app('%s%s' % (var, meth))
		else:
			if not var in dvars: dvars.append(var)
			app("p('%s')" % var)
	if parm: parm = "%% (%s) " % (',\n\t\t'.join(parm))
	else: parm = ''

	c = COMPILE_TEMPLATE_SHELL % (line, parm)

	Logs.debug('action: %s' % c)
	return (funex(c), dvars)

def compile_fun_noshell(line):
	"""
	create a compiled function to execute a process without the shell
	WARNING: this method may disappear anytime, so use compile_fun instead
	"""
	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('subst'): extr.append((g('var'), g('code'))); return "<<|@|>>"
		return None

	line2 = reg_act.sub(repl, line)
	params = line2.split('<<|@|>>')
	assert(extr)

	buf = []
	dvars = []
	app = buf.append
	for x in range(len(extr)):
		params[x] = params[x].strip()
		if params[x]:
			app("lst.extend(%r)" % params[x].split())
		(var, meth) = extr[x]
		if var == 'SRC':
			if meth: app('lst.append(tsk.inputs%s)' % meth)
			else: app("lst.extend([a.path_from(bld.bldnode) for a in tsk.inputs])")
		elif var == 'TGT':
			if meth: app('lst.append(tsk.outputs%s)' % meth)
			else: app("lst.extend([a.path_from(bld.bldnode) for a in tsk.outputs])")
		elif meth:
			if meth.startswith(':'):
				app('lst.extend([env[%r] %% x for x in env[%r]])' % (var, meth[1:]))
				dvars.extend([var, meth[1:]])
			else:
				app('lst.extend(gen.to_list(%s%s))' % (var, meth))
		else:
			app('lst.extend(to_list(env[%r]))' % var)
			if not var in dvars: dvars.append(var)

	if extr:
		if params[-1]:
			app("lst.extend(%r)" % params[-1].split())

	fun = COMPILE_TEMPLATE_NOSHELL % "\n\t".join(buf)
	Logs.debug('action: %s' % fun)
	return (funex(fun), dvars)

def compile_fun(line, shell=False):
	"""
	parse a string expression such as "${CC} ${SRC} -o ${TGT}" and return a pair containing
	* the function created as python code
	* the list of variables that imply a dependency from self.env

	example:
	compile_fun('cxx', '${CXX} -o ${TGT[0]} ${SRC} -I ${SRC[0].parent.bldpath()}')

	The env variables (CXX, ..) on the task must not hold dicts (order)
	The reserved keywords TGT and SRC represent the task input and output nodes

	quick test:
	bld(source='wscript', rule='echo "foo\\${SRC[0].name}\\bar"')

	"""
	if line.find('<') > 0 or line.find('>') > 0 or line.find('&&') > 0:
		shell = True

	if shell:
		return compile_fun_shell(line)
	else:
		return compile_fun_noshell(line)

def task_factory(name, func=None, vars=[], color='GREEN', ext_in=[], ext_out=[], before=[], after=[], shell=False, scan=None):
	"""
	return a new Task subclass with the function run compiled from the line given
	provided for compatibility with waf 1.5
	"""

	params = {
		'vars': vars,
		'color': color,
		'name': name,
		'ext_in': Utils.to_list(ext_in),
		'ext_out': Utils.to_list(ext_out),
		'before': Utils.to_list(before),
		'after': Utils.to_list(after),
		'shell': shell,
		'scan': scan,
	}

	if isinstance(func, str):
		params['run_str'] = func
	else:
		params['run'] = func

	cls = type(Task)(name, (Task,), params)
	global classes
	classes[name] = cls
	return cls


def always_run(cls):
	"""
	Task class decorator

	Set all task instances of this class to be executed whenever a build is started
	The task signature is calculated, but the result of the comparation between
	task signatures is bypassed
	"""
	old = cls.runnable_status
	def always(self):
		ret = old(self)
		if ret == SKIP_ME:
			ret = RUN_ME
		return ret
	cls.runnable_status = always
	return cls

def update_outputs(cls):
	"""
	decorator for Task classes

	Used to avoid unnecessary recompilations, but consumes more resources
	(hashing the output files) so it should be enabled only on the classes that need it
	"""
	old_post_run = cls.post_run
	def post_run(self):
		old_post_run(self)
		for node in self.outputs:
			node.sig = Utils.h_file(node.abspath())
	cls.post_run = post_run


	old_runnable_status = cls.runnable_status
	def runnable_status(self):
		status = old_runnable_status(self)
		if status != RUN_ME:
			return status

		try:
			# by default, we check that the output nodes have the signature of the task
			# perform a second check, returning 'SKIP_ME' as we are expecting that
			# the signatures do not match
			bld = self.generator.bld
			new_sig  = self.signature()
			prev_sig = bld.task_sigs[self.uid()]
			if prev_sig == new_sig:
				for x in self.outputs:
					if not x.sig:
						return RUN_ME
				return SKIP_ME
		except KeyError:
			pass
		except IndexError:
			pass
		return RUN_ME
	cls.runnable_status = runnable_status

	return cls


