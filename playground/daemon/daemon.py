#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn 2006
# rewritten by Thomas Nagy 2009

"""
Start a new build as soon as something changes in the build directory.

PyInotify, Fam, Gamin or time-threshold are used for the detection

For now only PyInotify and time threshold are supported
Watching for new svn revisions could be added too
"""

import select, errno, os, time
import Utils, Scripting, Logs, Build, Node

w_pyinotify = w_fam = w_gamin = None
def check_support():
	global w_pyinotify, w_fam, w_gamin
	try:
		import pyinotify as w_pyinotify
	except ImportError:
		w_pyinotify = None
	else:
		try:
			wm = w_pyinotify.WatchManager()
			wm = w_pyinotify.Notifier(wm)
			wm = None
		except:
			raise
			w_pyinotify = None

	try:
		import gamin as w_gamin
	except ImportError:
		w_gamin = None
	else:
		try:
			test = w_gamin.WatchMonitor()
			test.disconnect()
			test = None
		except:
			w_gamin = None

	try:
		import _fam as w_fam
	except ImportError:
		w_fam = None
	else:
		try:
			test = w_fam.open()
			test.close()
			test = None
		except:
			w_fam = None

def daemon(ctx):
	"""waf command: rebuild as soon as something changes"""
	bld = None
	while True:
		try:
			bld = Utils.g_module.build_context()
			Scripting.build(bld)
		except Build.BuildError, e:
			Logs.warn(e)
		except KeyboardInterrupt:
			Utils.pprint('RED', 'interrupted')
			break

		try:
			x = ctx.state
		except AttributeError:
			setattr(ctx, 'state', DirWatch())
			x = ctx.state

		x.wait(bld)

def set_options(opt):
	"""So this shows how to add new commands from tools"""
	Utils.g_module.__dict__['daemon'] = daemon

class DirWatch(object):
	def __init__(self):
		check_support()
		if w_pyinotify:
			self.sup = 'pyinotify'
		elif w_gamin:
			self.sup = 'gamin'
		elif w_fam:
			self.sup = 'fam'
		else:
			self.sup = 'dumb'
		#self.sup = 'dumb'

	def wait(self, bld):
		return getattr(self.__class__, 'wait_' + self.sup)(self, bld)

	def enumerate(self, node):
		yield node.abspath()
		for x in node.childs.values():
			if x.id & 3 == Node.DIR:
				for k in self.enumerate(x):
					yield k
		raise StopIteration

	def wait_pyinotify(self, bld):

		class PE(w_pyinotify.ProcessEvent):
			def stop(self, event):
				self.notif.ev = True
				self.notif.stop()
				raise ValueError("stop for delete")

			process_IN_DELETE = stop
			process_IN_CLOSE = stop
			process_default = stop

		proc = PE()
		wm = w_pyinotify.WatchManager()
		notif = w_pyinotify.Notifier(wm, proc)
		proc.notif = notif

		# well, we should add all the folders to watch here
		for x in self.enumerate(bld.srcnode):
			wm.add_watch(x, w_pyinotify.IN_DELETE | w_pyinotify.IN_CLOSE_WRITE)

		try:
			# pyinotify uses an infinite loop ... not too nice, so we have to use an exception
			notif.loop()
		except ValueError:
			pass
		if not hasattr(notif, 'ev'):
			raise KeyboardInterrupt

	def wait_dumb(self, bld):
		time.sleep(5)

	def wait_gamin(self, bld):
		time.sleep(5)

	def wait_fam(self, bld):
		time.sleep(5)

