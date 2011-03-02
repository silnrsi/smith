#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2011 (ita)

"""
Prevents link tasks from executing in parallel
"""

from waflib.Utils import threading
from waflib import Task
lock = threading.Lock()

def make_exclusive(cls):
	old = cls.runnable_status
	def runnable_status(self):
		ret = Task.ASK_LATER
		if lock.acquire(False):
			try:
				ret = old(self)
			finally:
				lock.release()
		return ret
	cls.runnable_status = runnable_status

for x in 'cprogram cxxprogram cshlib cxxshlib cstlib cxxstlib'.split():
	if x in Task.classes:
		make_exclusive(Task.classes[x])

