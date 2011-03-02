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
	old_run = cls.run
	def run(self):
		ret = None
		lock.acquire()
		try:
			ret = old_run(self)
		finally:
			lock.release()
		return ret
	cls.run = run

for x in 'cprogram cxxprogram cshlib cxxshlib cstlib cxxstlib'.split():
	if x in Task.classes:
		make_exclusive(Task.classes[x])

