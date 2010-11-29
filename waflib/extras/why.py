#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
# TODO

a waf tool that modifies the task signature scheme to store and obtain
information about the task execution (why it must run, etc)
"""

from waflib import Task, Utils, Logs, Errors

def signature(self):
	# compute the result one time, and suppose the scan_signature will give the good result
	try: return self.cache_sig
	except AttributeError: pass

	self.m = Utils.md5()
	self.m.update(self.hcode.encode())
	id_sig = self.m.digest()

	# explicit deps
	self.sig_explicit_deps()
	exp_sig = self.m.digest()

	# env vars
	self.sig_vars()
	var_sig = self.m.digest()

	# implicit deps / scanner results
	if self.scan:
		try:
			imp_sig = self.sig_implicit_deps()
		except Errors.TaskRescan:
			return self.signature()

	ret = self.cache_sig = self.m.digest()
	return ret


Task.Task.signature = signature

old = Task.Task.runnable_status
def runnable_status(self):
	ret = old(self)
	if ret == Task.RUN_ME:
		try:
			old_sigs = self.generator.bld.task_sigs[self.uid()]
		except:
			Logs.debug("task: task must run as no previous signature exists")
		else:
			new_sigs = self.cache_sig
			def v(x):
				return Utils.to_hex(x)

			Logs.debug("Task %r" % self)
			msgs = ['Task must run', '* Source file or manual dependency', '* Implicit dependency', '* Configuration data variable']
			tmp = 'task: -> %s: %s %s'
			for x in range(len(msgs)):
				if (new_sigs[x] != old_sigs[x]):
					Logs.debug(tmp % (msgs[x], v(old_sigs[x]), v(new_sigs[x])))
	return ret
Task.Task.runnable_status = runnable_status

