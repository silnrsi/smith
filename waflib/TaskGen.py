#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
The class task_gen encapsulates the creation of task objects (low-level code)
The instances can have various parameters, but the creation of task nodes (Task.py)
is always postponed. To achieve this, various methods are called from the method "apply"

The class task_gen contains lots of methods, and a configuration table:
* the methods to call (self.meths) can be specified dynamically (removing, adding, ..)
* the order of the methods (self.prec or by default task_gen.prec) is configurable
* new methods can be inserted dynamically without pasting old code

Additionally, task_gen provides the method "process_source"
* file extensions are mapped to methods: def meth(self, name_or_node)
* if a mapping is not found in self.mappings, it is searched in task_gen.mappings
* when called, the functions may modify self.source to append more source to process
* the mappings can map an extension or a filename (see the code below)

WARNING: subclasses must reimplement the clone method
"""

import copy, re
from waflib import Task, Utils, Logs, Errors

feats = Utils.defaultdict(set)
"""remember the methods declaring features"""

class task_gen(object):
	"""
	Generate task objects by calling the method post() from the main thread
	the tasks created should be added to the attribute tasks
	the attribute 'path' is a node representing the location of the task generator
	the attribute 'idx' is a counter of task generators in the same path
	the 'features' are used to add methods to self.meths and then execute them
	the methods are sorted before execution
	"""

	mappings = {}
	prec = Utils.defaultdict(list)

	def __init__(self, *k, **kw):
		"""
		The task generator objects predefine various attributes (source, target) for possible
		processing by process_rule (make-like rules) or process_source (extensions, misc methods)

		The tasks are stored on the attribute 'tasks'. They are created by calling methods
		listed in self.meths *or* referenced in the attribute features
		A topological sort is performed to ease the method re-use.

		The extra key/value elements passed in kw are set as attributes
		"""

		# so we will have to play with directed acyclic graphs
		# detect cycles, etc
		self.source = ''
		self.target = ''

		# list of methods to execute (it is usually a good idea to avoid touching this)
		self.meths = []

		# precedence table for sorting the methods
		self.prec = Utils.defaultdict(list)

		# list of mappings extension -> function
		self.mappings = {}

		# list of methods to execute (by name)
		self.features = []

		# tasks created
		self.tasks = []

		if not 'bld' in kw:
			# task generators without a build context :-/
			self.env = ConfigSet.ConfigSet()
			self.idx = 0
			self.path = None
		else:
			self.bld = kw['bld']
			self.env = self.bld.env.derive()
			self.path = self.bld.path # emulate chdir when reading scripts

			# provide a unique id
			try:
				self.idx = self.bld.idx[id(self.path)] = self.bld.idx.get(id(self.path), 0) + 1
			except AttributeError:
				self.bld.idx = {}
				self.idx = self.bld.idx[id(self.path)] = 0

		for key, val in kw.items():
			setattr(self, key, val)

	def __str__(self):
		"""for debugging purposes"""
		return "<task_gen %r declared in %s>" % (self.name, self.path.abspath())

	def __repr__(self):
		"""for debugging purposes"""
		lst = []
		for x in self.__dict__.keys():
			if x not in ['env', 'bld', 'compiled_tasks', 'tasks']:
				lst.append("%s=%r" % (x, repr(getattr(self, x))))
		return "bld(%s) in %s" % (" ".join(lst), self.path.abspath())

	def get_name(self):
		"""the name is computed from the target name, if possible"""
		try:
			return self._name
		except AttributeError:
			if isinstance(self.target, list):
				lst = [str(x) for x in self.target]
				name = self._name = ','.join(lst)
			else:
				name = self._name = str(self.target)
			return name
	def set_name(self, name):
		self._name = name

	name = property(get_name, set_name)

	def to_list(self, value):
		"""helper: returns a list"""
		if isinstance(value, str): return value.split()
		else: return value

	def post(self):
		"""create the task objects; order the methods to execute using self.prec or task_gen.prec"""

		# we could add a decorator to let the task run once, but then python 2.3 will be difficult to support

		if getattr(self, 'posted', None):
			#error("OBJECT ALREADY POSTED" + str( self))
			return False
		self.posted = True

		keys = set(self.meths)

		# add the methods listed in the features
		self.features = Utils.to_list(self.features)
		for x in self.features + ['*']:
			st = feats[x]
			if not st:
				Logs.warn('feature %r does not exist - bind at least one method to it' % x)
			keys.update(st)

		# copy the precedence table
		prec = {}
		prec_tbl = self.prec or task_gen.prec
		for x in prec_tbl:
			if x in keys:
				prec[x] = prec_tbl[x]

		# elements disconnected
		tmp = []
		for a in keys:
			for x in prec.values():
				if a in x: break
			else:
				tmp.append(a)

		# topological sort
		out = []
		while tmp:
			e = tmp.pop()
			if e in keys: out.append(e)
			try:
				nlst = prec[e]
			except KeyError:
				pass
			else:
				del prec[e]
				for x in nlst:
					for y in prec:
						if x in prec[y]:
							break
					else:
						tmp.append(x)

		if prec:
			raise Errors.WafError('Cycle detected in the method execution %r' % prec)
		out.reverse()
		self.meths = out

		# then we run the methods in order
		Logs.debug('task_gen: posting %s %d' % (self, id(self)))
		for x in out:
			try:
				v = getattr(self, x)
			except AttributeError:
				raise Errors.WafError('%r is not a valid task generator method' % x)
			Logs.debug('task_gen: -> %s (%d)' % (x, id(self)))
			v()

		Logs.debug('task_gen: posted %s' % self.name)
		return True

	def get_hook(self, node):
		"""
		get a function able to process an extension
		"""
		name = node.name
		for k in self.mappings:
			if name.endswith(k):
				return self.mappings[k]
		for k in task_gen.mappings:
			if name.endswith(k):
				return task_gen.mappings[k]
		raise Errors.WafError("File %r has no mapping in %r (did you forget to load a waf tool?)" % (node, task_gen.mappings.keys()))

	def create_task(self, name, src=None, tgt=None):
		"""wrapper for creating task object creation"""
		task = Task.classes[name](env=self.env.derive(), generator=self)
		if src:
			task.set_inputs(src)
		if tgt:
			task.set_outputs(tgt)
		self.tasks.append(task)
		return task

	def clone(self, env):
		"""make a copy of a task generator, make sure to avoid creating the same tasks twice"""
		newobj = self.bld()
		for x in self.__dict__:
			if x in ['env', 'bld']:
				continue
			elif x in ['path', 'features']:
				setattr(newobj, x, getattr(self, x))
			else:
				setattr(newobj, x, copy.copy(getattr(self, x)))

		newobj.posted = False
		if isinstance(env, str):
			newobj.env = self.bld.all_envs[env].derive()
		else:
			newobj.env = env.derive()

		return newobj

def declare_chain(name='', rule=None, reentrant=True, color='BLUE',
	ext_in=[], ext_out=[], before=[], after=[], decider=None, scan=None):
	"""
	see Tools/flex.py for an example
	while i do not like such wrappers, some people really do
	"""
	ext_in = Utils.to_list(ext_in)
	ext_out = Utils.to_list(ext_out)
	cls = Task.task_factory(name, rule, color=color, ext_in=ext_in, ext_out=ext_out, before=before, after=after, scan=scan)

	def x_file(self, node):
		ext = decider and decider(self, node) or cls.ext_out
		if ext_in:
			ext_in = ext_in[0]
		out_source = [node.change_ext(x, ext_in=_ext_in) for x in ext]
		if reentrant:
			for i in range(reentrant):
				self.source.append(out_source[i])
		tsk = self.create_task(name, node, out_source)

	for x in cls.ext_in:
		task_gen.mappings[x] = x_file
	return x_file

def taskgen_method(func):
	"""
	register a method as a task generator method
	"""
	setattr(task_gen, func.__name__, func)
	return func

def feature(*k):
	"""
	declare a task generator method that will be executed when the
	object attribute 'feature' contains the corresponding key(s)
	"""
	def deco(func):
		setattr(task_gen, func.__name__, func)
		for name in k:
			feats[name].update([func.__name__])
		return func
	return deco

def before(*k):
	"""
	declare a task generator method which will be executed
	before the functions of given name(s)
	"""
	def deco(func):
		setattr(task_gen, func.__name__, func)
		for fun_name in k:
			if not func.__name__ in task_gen.prec[fun_name]:
				task_gen.prec[fun_name].append(func.__name__)
		return func
	return deco

def after(*k):
	"""
	declare a task generator method which will be executed
	after the functions of given name(s)
	"""
	def deco(func):
		setattr(task_gen, func.__name__, func)
		for fun_name in k:
			if not fun_name in task_gen.prec[func.__name__]:
				task_gen.prec[func.__name__].append(fun_name)
		return func
	return deco

def extension(*k):
	"""
	declare a task generator method which will be invoked during
	the processing of source files for the extension given
	"""
	def deco(func):
		setattr(task_gen, func.__name__, func)
		for x in k:
			task_gen.mappings[x] = func
		return func
	return deco

# ---------------------------------------------------------------
# The following methods are task generator methods commonly used
# they are almost examples, the rest of waf core does not depend on them

@taskgen_method
def to_nodes(self, lst, path=None):
	"""
	convert @lst to a list of nodes, used by process_source and process_rule
	it will try to return build nodes, so it is not really suitable for folders
	for other purposes see to_incnodes in ccroot.py
	"""
	tmp = []
	path = path or self.path
	find = path.find_resource

	if isinstance(lst, self.path.__class__):
		lst = [lst]

	# either a list or a string, convert to a list of nodes
	for x in Utils.to_list(lst):
		if isinstance(x, str):
			node = find(x)
			if not node:
				raise Errors.WafError("source not found: %r in %r" % (x, path))
		else:
			node = x
		tmp.append(node)
	return tmp

@feature('*')
def process_source(self):
	"""
	Process each element in the attribute 'source', assuming it represents
	a list of source (a node, a string, or a list of nodes or file names)
	process the files by extension

	No error will be raised if 'self.source' is not defined.
	"""
	self.source = self.to_nodes(getattr(self, 'source', []))
	for node in self.source:
		self.get_hook(node)(self, node)

@feature('*')
@before('process_source')
def process_rule(self):
	"""
	Process the attribute rule, when provided the method process_source will be disabled
	"""
	if not getattr(self, 'rule', None):
		return

	# create the task class
	name = str(getattr(self, 'name', None) or self.target or self.rule)
	cls = Task.task_factory(name, self.rule,
		getattr(self, 'vars', []),
		shell=getattr(self, 'shell', True), color=getattr(self, 'color', 'BLUE'))

	# now create one instance
	tsk = self.create_task(name)

	if getattr(self, 'target', None):
		if isinstance(self.target, str):
			self.target = self.target.split()
		if not isinstance(self.target, list):
			self.target = [self.target]
		for x in self.target:
			if isinstance(x, str):
				tsk.outputs.append(self.path.find_or_declare(x))
			else:
				x.parent.mkdir() # if a node was given, create the required folders
				tsk.outputs.append(x)
		if getattr(self, 'install_path', None):
			# from waf 1.5
			# although convenient, it does not 1. allow to name the target file and 2. symlinks
			# TODO remove in waf 1.7
			self.bld.install_files(self.install_path, tsk.outputs)

	if getattr(self, 'source', None):
		tsk.inputs = self.to_nodes(self.source)
		# bypass the execution of process_source by setting the source to an empty list
		self.source = []

	if getattr(self, 'scan', None):
		cls.scan = self.scan

	if getattr(self, 'cwd', None):
		tsk.cwd = self.cwd

	# TODO remove on_results in waf 1.7
	if getattr(self, 'update_outputs', None) or getattr(self, 'on_results', None):
		Task.update_outputs(cls)

	if getattr(self, 'always', None):
		Task.always_run(cls)

	for x in ['after', 'before', 'ext_in', 'ext_out']:
		setattr(cls, x, getattr(self, x, []))

@feature('seq')
def sequence_order(self):
	"""
	Add a strict sequential constraint between the tasks generated by task generators
	It works because task generators are posted in order
	it will not post objects which belong to other folders

	This is more an example than a widely-used solution

	Note that the method is executed in last position

	to use:
	bld(features='javac seq')
	bld(features='jar seq')

	to start a new sequence, set the attribute seq_start, for example:
	obj.seq_start = True
	"""
	if self.meths and self.meths[-1] != 'sequence_order':
		self.meths.append('sequence_order')
		return

	if getattr(self, 'seq_start', None):
		return

	# all the tasks previously declared must be run before these
	if getattr(self.bld, 'prev', None):
		self.bld.prev.post()
		for x in self.bld.prev.tasks:
			for y in self.tasks:
				y.set_run_after(x)

	self.bld.prev = self



re_m4 = re.compile('@(\w+)@', re.M)

class subst_pc(Task.Task):
	"""
	.pc file creation is very common
	bld(source='foo.pc.in') will create foo.pc which will be installed into ${PREFIX}/lib/pkgconfig/
	"""

	def run(self):
		"Substitutes variables in a .in file"

		code = self.inputs[0].read()

		# replace all % by %% to prevent errors by % signs
		code = code.replace('%', '%%')

		# extract the vars foo into lst and replace @foo@ by %(foo)s
		lst = []
		def repl(match):
			g = match.group
			if g(1):
				lst.append(g(1))
				return "%%(%s)s" % g(1)
			return ''
		code = re_m4.sub(repl, code)

		try:
			d = self.generator.dct
		except AttributeError:
			d = {}
			for x in lst:
				d[x] = getattr(self.generator, x, '') or self.env.get_flat(x) or self.env.get_flat(x.upper())
				if not d[x] and not getattr(self.generator, 'quiet', False):
					raise ValueError('variable %r has no value for %r' % (x, self.outputs))

		self.outputs[0].write(code % d)
		self.generator.bld.raw_deps[self.uid()] = self.dep_vars = lst

		# make sure the signature is updated
		try: delattr(self, 'cache_sig')
		except AttributeError: pass

	def sig_vars(self):
		"""
		Compute a hash (signature) of the variables used in the substitution
		"""
		bld = self.generator.bld
		env = self.env
		upd = self.m.update

		# raw_deps: persistent custom values returned by the scanner
		vars = self.generator.bld.raw_deps.get(self.uid(), [])

		# hash both env vars and task generator attributes
		act_sig = bld.hash_env_vars(env, vars)
		upd(act_sig)

		lst = [getattr(self.generator, x, '') for x in vars]
		upd(Utils.h_list(lst))

		return self.m.digest()

@extension('.pc.in')
def add_pcfile(self, node):
	""".pc.in -> .pc + install the .pc file into ${PREFIX}/lib/pkgconfig/"""
	tsk = self.create_task('subst_pc', node, node.change_ext('.pc'))
	self.bld.install_files('${PREFIX}/lib/pkgconfig/', tsk.outputs)

