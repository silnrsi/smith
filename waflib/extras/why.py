#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
# TODO

a waf tool that modifies the task signature scheme to store and obtain
information about the task execution (why it must run, etc)
"""

def signature(self):
	# compute the result one time, and suppose the scan_signature will give the good result
	try: return self.cache_sig[0]
	except AttributeError: pass

	m = md5()

	# explicit deps
	exp_sig = self.sig_explicit_deps()
	m.update(exp_sig)

	# implicit deps
	imp_sig = self.scan and self.sig_implicit_deps() or Utils.SIG_NIL
	m.update(imp_sig)

	# env vars
	var_sig = self.sig_vars()
	m.update(var_sig)

	# we now have the signature (first element) and the details (for debugging)
	ret = m.digest()
	self.cache_sig = (ret, exp_sig, imp_sig, var_sig)
	return ret


def debug_why(self, old_sigs):
	"explains why a task is run"

	new_sigs = self.cache_sig
	def v(x):
		return Utils.to_hex(x)

	debug("Task %r" % self)
	msgs = ['Task must run', '* Source file or manual dependency', '* Implicit dependency', '* Configuration data variable']
	tmp = 'task: -> %s: %s %s'
	for x in range(len(msgs)):
		if (new_sigs[x] != old_sigs[x]):
			debug(tmp % (msgs[x], v(old_sigs[x]), v(new_sigs[x])))

from waflib import Task
Task.Task.debug_why = debug_why

