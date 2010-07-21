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
ccroot.USELIB_VARS['fcprogram_test'] = ccroot.USELIB_VARS['fcprogram'] = set(['LINKFLAGS'])
ccroot.USELIB_VARS['fcshlib'] = set(['LINKFLAGS'])
ccroot.USELIB_VARS['fcstlib'] = set(['LINKFLAGS'])

@feature('fcprogram', 'fcshlib', 'fcstlib', 'fcprogram_test')
def dummy(self):
	pass



# FIXME what was this for??????
#def fortran_compile(task):
#	env = task.env
#	def tolist(xx):
#		if isinstance(xx, str):
#			return [xx]
#		return xx
#	cmd = []
#	cmd.extend(tolist(env["FC"]))
#	cmd.extend(tolist(env["FCFLAGS"]))
#	cmd.extend(tolist(env["_FCINCFLAGS"]))
#	cmd.extend(tolist(env["_FCMODOUTFLAGS"]))
#	for a in task.outputs:
#		cmd.extend(tolist(env["FC_TGT_F"] + tolist(a.bldpath(env))))
#	for a in task.inputs:
#		cmd.extend(tolist(env["FC_SRC_F"]) + tolist(a.srcpath(env)))
#	cmd = [x for x in cmd if x]
#	cmd = [cmd]
#
#	ret = task.exec_command(*cmd)
#	return ret

@TaskGen.extension('.f')
def fc_hook(self, node):
	return self.create_compiled_task('fc', node)

class fc(Task.Task):
	color = 'GREEN'
	run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${_FCMODOUTFLAGS} ${FC_TGT_F}${TGT[0].abspath()} ${FC_SRC_F}${SRC[0].abspath()}'
	vars = ["FORTRANMODPATHFLAG"]
	scan = fc_scan.scan

	def runnable_status(self):
		"""
		set the mod file outputs and the dependencies on the mod files over all the fortran tasks
		there are no concurrency issues since the method runnable_status is executed by the main thread
		"""
		if getattr(self, 'mod_fortran_done', None):
			return super(fc, self).runnable_status()

		# now, if we reach this part it is because this fortran task is the first in the list
		bld = self.generator.bld

		# obtain the fortran tasks
		lst = [tsk for tsk in bld.producer.outstanding + bld.producer.frozen if isinstance(tsk, fc)]

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
					if node:
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

@extension('.F')
def fcpp_hook(self, node):
	return self.create_compiled_task('fcpp', node)

class fcpp(Task.Task):
	# FIXME why another task? what's the problem?
	color = 'GREEN'
	run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC}'

class fcprogram(ccroot.link_task):
	color = 'YELLOW'
	run_str = '${FC} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT} ${LINKFLAGS}'
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

		try:
			proc = Utils.subprocess.Popen(cmd, **kw)
			(bld.out, bld.err) = proc.communicate()
		except OSError:
			return -1

		if bld.out:
			bld.to_log("out: %s\n" % bld.out)
		if bld.err:
			bld.to_log("err: %s\n" % bld.err)

		return proc.returncode

class fcstlib(ccroot.stlink_task):
	"""just use ar normally"""
	pass # do not remove the pass statement

