#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

"""
fortran support
"""

import re

from waflib import Utils, Task, TaskGen, Logs
from waflib.Tools import ccroot
from waflib.extras import fc_config, fc_scan
from waflib.TaskGen import feature, before, after, extension
from waflib.Configure import conf

ccroot.USELIB_VARS['fc'] = set(['FCFLAGS', 'DEFINES'])
ccroot.USELIB_VARS['fcprogram_test'] = ccroot.USELIB_VARS['fcprogram'] = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS'])
ccroot.USELIB_VARS['fcshlib'] = set(['LIB', 'STLIB', 'LIBPATH', 'STLIBPATH', 'LINKFLAGS', 'RPATH', 'LINKDEPS'])
ccroot.USELIB_VARS['fcstlib'] = set(['ARFLAGS', 'LINKDEPS'])

@feature('fcprogram', 'fcshlib', 'fcstlib', 'fcprogram_test')
def dummy(self):
	pass

@TaskGen.extension('.f', '.f90')
def fc_hook(self, node):
	return self.create_compiled_task('fc', node)

def get_fortran_tasks(tsk):
	"""
	other fortran tasks from the same group
	"""
	tasks = []
	bld = tsk.generator.bld
	gp = bld.groups[bld.get_group_idx(tsk.generator)]
	for tg in gp:
		try: tasks.extend(tg.tasks)
		except TypeError: tasks.append(tg)
	return [x for x in tasks if isinstance(x, fc) and not getattr(x, 'nomod', None) and not getattr(x, 'mod_fortran_done', None)]

class fc(Task.Task):
	"""
	the fortran tasks can only run if all the tasks in the current group are ready to be executed
	there may be a deadlock if another fortran task is waiting for something that won't happen (circular dependency)
	in this case, set the 'nomod=True' on the task instance to break the loop
	"""

	color = 'GREEN'
	run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${_FCMODOUTFLAGS} ${FC_TGT_F}${TGT[0].abspath()} ${FC_SRC_F}${SRC[0].abspath()}'
	vars = ["FORTRANMODPATHFLAG"]
	scan = fc_scan.scan

	def runnable_status(self):
		"""
		set the mod file outputs and the dependencies on the mod files over all the fortran tasks
		executed by the main thread so there are no concurrency issues
		"""
		if getattr(self, 'mod_fortran_done', None):
			return super(fc, self).runnable_status()

		# now, if we reach this part it is because this fortran task is the first in the list
		bld = self.generator.bld

		# obtain the fortran tasks
		lst = get_fortran_tasks(self)

		# disable this method for other tasks
		for tsk in lst:
			tsk.mod_fortran_done = True

		# wait for all the .f tasks to be ready for execution
		# and ensure that the scanners are called at least once
		for tsk in lst:
			ret = tsk.runnable_status()
			if ret == Task.ASK_LATER:
				# we have to wait for one of the other fortran tasks to be ready
				# this may deadlock if there are dependencies between the fortran tasks
				# but this should not happen (we are setting them here!)
				for x in lst:
					x.mod_fortran_done = None

				# TODO sort the list of tasks in bld.producer.outstanding to put all fortran tasks at the end
				return Task.ASK_LATER

		ins = Utils.defaultdict(set)
		outs = Utils.defaultdict(set)

		# the .mod files to create
		for tsk in lst:
			key = tsk.uid()
			for x in bld.raw_deps[key]:
				if x.startswith('MOD@'):
					name = x.replace('MOD@', '') + '.mod'
					node = bld.srcnode.find_or_declare(name)
					tsk.set_outputs(node)
					outs[id(node)].add(tsk)

		# the .mod files to use
		for tsk in lst:
			key = tsk.uid()
			for x in bld.raw_deps[key]:
				if x.startswith('USE@'):
					name = x.replace('USE@', '') + '.mod'
					node = bld.srcnode.find_resource(name)
					if node and node not in tsk.outputs:
						if not node in bld.node_deps[key]:
							bld.node_deps[key].append(node)
						ins[id(node)].add(tsk)

		# if the intersection matches, set the order
		for k in ins.keys():
			for a in ins[k]:
				a.run_after.update(outs[k])

		# the task objects have changed: clear the signature cache
		for tsk in lst:
			try:
				delattr(tsk, 'cache_sig')
			except AttributeError:
				pass

		return super(fc, self).runnable_status()

@extension('.F', '.F90')
def fcpp_hook(self, node):
	return self.create_compiled_task('fc', node)

class fcprogram(ccroot.link_task):
	color = 'YELLOW'
	run_str = '${FC} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT} ${FCSTLIB_MARKER} ${FCSTLIBPATH_ST:STLIBPATH} ${FCSTLIB_ST:STLIB} ${FCSHLIB_MARKER} ${FCLIBPATH_ST:LIBPATH} ${FCLIB_ST:LIB} ${LINKFLAGS}'
	inst_to = '${BINDIR}'

class fcshlib(fcprogram):
	inst_to = '${LIBDIR}'

class fcprogram_test(fcprogram):
	"""custom link task to obtain the compiler outputs"""

	def runnable_status(self):
		"""make sure the link task is always executed"""
		ret = super(fcprogram_test, self).runnable_status()
		if ret == Task.SKIP_ME:
			ret = Task.RUN_ME
		return ret

	def exec_command(self, cmd, **kw):
		"""store the compiler std our/err onto the build context, to bld.out + bld.err"""
		bld = self.generator.bld

		kw['shell'] = isinstance(cmd, str)
		kw['stdout'] = kw['stderr'] = Utils.subprocess.PIPE
		kw['cwd'] = bld.variant_dir
		bld.out = bld.err = ''

		bld.to_log('command: %s\n' % cmd)

		kw['output'] = 0
		try:
			(bld.out, bld.err) = bld.cmd_and_log(cmd, **kw)
		except Exception as e:
			return -1

		if bld.out:
			bld.to_log("out: %s\n" % bld.out)
		if bld.err:
			bld.to_log("err: %s\n" % bld.err)

class fcstlib(ccroot.stlink_task):
	"""just use ar normally"""
	pass # do not remove the pass statement

