#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

import os
from waflib import TaskGen, Task, Utils, Build
from waflib.TaskGen import taskgen, feature, before, after, extension
from waflib.Logs import debug

@taskgen_method
@after('apply_link')
@extension('.src')
def process_shpip(self, node):
	tsk = shpip_task(self.env, generator=self)
	tsk.task_gen = self
	tsk.set_inputs(node)

class shpip_task(Task.Task):
	"""
	A special task, which finds its outputs once it has run
	It outputs cpp files that must be compiled too
	"""

	color = 'PINK'
	quiet = 1

	# important, no link before all shpip are done
	before = ['cc_link', 'cxx_link', 'ar_link_static', 'cc', 'cxx']

	def __init__(self, *k, **kw):
		Task.Task.__init__(self, *k, **kw)

	def run(self):
		"runs a program that creates cpp files, capture the output to compile them"
		node = self.inputs[0]
		bld = self.generator.bld

		dir = bld.srcnode.bldpath(self.env)
		cmd = 'cd %s && %s %s' % (dir, self.env.SHPIP_COMPILER, node.abspath(self.env))
		try:
			# read the contents of the file and create cpp files from it
			files = os.popen(cmd).read().strip()
		except:
			# comment the following line to disable debugging
			#raise
			return 1 # error

		# the variable lst should contain a list of paths to the files produced
		lst = Utils.to_list(files)

		# Waf does not know "magically" what files are produced
		# In the most general case it may be necessary to run os.listdir() to see them
		# In this demo the command outputs is giving us this list

		# the files exist in the build dir only so we do not use find_or_declare
		build_nodes = [node.parent.exclusive_build_node(x) for x in lst]
		self.outputs = build_nodes

		# create the cpp tasks
		self.more_tasks = self.add_cpp_tasks(build_nodes)

		# cache the file names and the task signature
		sig = self.signature()
		bld.raw_deps[self.unique_id()] = [sig] + lst

		return 0 # no error

	def runnable_status(self):
		# look at the cache, if the shpip task was already run
		# and if the source has not changed, create the corresponding cpp tasks

		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER

		tree = self.generator.bld

		try:
			sig = self.signature()
			key = self.unique_id()
			deps = tree.raw_deps[key]
			prev_sig = tree.task_sigs[key][0]
		except KeyError:
			pass
		else:
			# if the file has not changed, create the cpp tasks
			if prev_sig == sig:
				nodes = [self.task_gen.path.exclusive_build_node(y) for y in deps[1:]]
				self.set_outputs(nodes)
				tsklst = self.add_cpp_tasks(nodes)
				generator = tree.generator
				for tsk in tsklst:
					generator.outstanding.append(tsk)

		if not self.outputs:
			return RUN_ME

		# this is a part of Task.Task:runnable_status: first node does not exist -> run
		# this is necessary after a clean
		env = self.env
		node = self.outputs[0]
		variant = node.variant(env)

		try:
			time = tree.node_sigs[variant][node.id]
		except KeyError:
			debug("task: task #%d should run as the first node does not exist" % self.idx)
			try: new_sig = self.signature()
			except KeyError:
				print "TODO - computing the signature failed"
				return RUN_ME

			ret = self.can_retrieve_cache(new_sig)
			return ret and SKIP_ME or RUN_ME

		return SKIP_ME

	def add_cpp_tasks(self, lst):
		"creates cpp tasks after the build has started"
		tgen = self.task_gen
		tsklst = []

		for node in lst:
			if node.name.endswith('.h'):
				continue

			TaskGen.task_gen.mapped['c_hook'](tgen, node)
			task = tgen.compiled_tasks[-1]
			task.set_run_after(self)

			# important, no link before compilations are all over
			try:
				self.generator.link_task.set_run_after(task)
			except AttributeError:
				pass

			tgen.link_task.inputs.append(task.outputs[0])
			tsklst.append(task)

			# if headers are produced something like this can be done to add the include paths
			dir = task.inputs[0].parent
			cpppath_st = self.env.CPPPATH_ST
			self.env.append_unique('_CXXINCFLAGS', cpppath_st % dir.abspath(self.env)) # include paths for c++
			self.env.append_unique('_CCINCFLAGS', cpppath_st % dir.abspath(self.env)) # include paths for c
			self.env.append_value('INC_PATHS', dir) # for the waf preprocessor

		return tsklst


