#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Execute the tasks"

import os, sys, random
try:
	from queue import Queue
except:
	from Queue import Queue
from waflib import Utils, Logs, Task, Errors

GAP = 10
"""
wait for free tasks if there are at least GAP * njobs in the queue
"""

MAXJOBS = 999
"""
maximum amount of jobs - cpython cannot really spawn more than 100 without crashing
"""

class TaskConsumer(Utils.threading.Thread):
	"""
	task consumers belong to a pool of workers
	they wait for tasks in the queue and then use task.process(...)
	"""
	def __init__(self):
		Utils.threading.Thread.__init__(self)
		self.ready = Queue()
		self.setDaemon(1)
		self.start()

	def run(self):
		try:
			self.loop()
		except:
			pass

	def loop(self):
		while 1:
			tsk = self.ready.get()
			tsk.process()

pool = Queue()
def get_pool():
	try:
		return pool.get(False)
	except:
		return TaskConsumer()

def put_pool(x):
	pool.put(x)


class Parallel(object):
	"""
	keep the consumer threads busy, and avoid consuming cpu cycles
	when no more tasks can be added (end of the build, etc)
	"""
	def __init__(self, bld, j=2):
		"""
		The initialization requires a build context reference for computing the total
		"""
		# number of consumers in the pool
		self.numjobs = j

		self.bld = bld # build context

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		self.maxjobs = MAXJOBS

		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks returned the consumers pool
		self.out = Queue(0)

		self.count = 0 # tasks not in the producer area

		self.processed = 1 # progress indicator

		self.stop = False # error condition to stop the build
		self.error = [] # tasks in error
		self.biter = None # build iterator, must give groups of parallelizable tasks on next()
		self.dirty = False # tasks have been executed, the build cache must be saved

	def get_next_task(self):
		"override this method to schedule the tasks in a particular order"
		if not self.outstanding:
			return None
		return self.outstanding.pop(0)

	def postpone(self, tsk):
		"override this method to schedule the tasks in a particular order"
		# TODO consider using a deque instead
		if random.randint(0, 1):
			self.frozen.insert(0, tsk)
		else:
			self.frozen.append(tsk)

	def refill_task_list(self):
		"called to set the next group of tasks"

		while self.count > self.numjobs * GAP or self.count >= self.maxjobs:
			self.get_out()

		while not self.outstanding:
			if self.count:
				self.get_out()
			elif self.frozen:
				try:
					cond = self.deadlock == self.processed
				except:
					pass
				else:
					if cond:
						msg = 'check the build order for the tasks'
						for tsk in self.frozen:
							if not tsk.run_after:
								msg = 'check the methods runnable_status'
								break
						lst = []
						for tsk in self.frozen:
							lst.append('%s\t-> %r' % (repr(tsk), [id(x) for x in tsk.run_after]))
						raise Errors.WafError("Deadlock detected: %s%s" % (msg, ''.join(lst)))
				self.deadlock = self.processed

			if self.frozen:
				self.outstanding += self.frozen
				self.frozen = []
			elif not self.count:
				self.outstanding.extend(next(self.biter))
				self.total = self.bld.total()
				break

	def add_more_tasks(self, tsk):
		"tasks may be added dynamically during the build by binding to the list attribute 'more_tasks'"
		if getattr(tsk, 'more_tasks', None):
			self.outstanding += tsk.more_tasks
			self.total += len(tsk.more_tasks)

	def get_out(self):
		"the tasks that are put to execute are all collected using get_out"
		tsk = self.out.get()
		if not self.stop:
			self.add_more_tasks(tsk)
		self.count -= 1
		self.dirty = True

	def error_handler(self, tsk):
		"by default, errors make the build stop (not thread safe so be careful)"
		if not self.bld.keep:
			self.stop = True
		self.error.append(tsk)

	def add_task(self, tsk):
		"add a task to one of the consumers"
		try:
			pool = self.pool
		except AttributeError:
			# lazy creation
			pool = self.pool = [get_pool() for i in range(self.numjobs)]

		# better load distribution across the consumers (makes more sense on distributed systems)
		# there are probably ways to have consumers use a unique queue
		a = pool[random.randint(0, len(pool) - 1)]
		siz = a.ready.qsize()
		if not siz:
			a.ready.put(tsk)
			return

		b = pool[random.randint(0, len(pool) - 1)]
		if siz > b.ready.qsize():
			b.ready.put(tsk)
		else:
			a.ready.put(tsk)

	def start(self):
		"execute the tasks"

		self.total = self.bld.total()

		while not self.stop:

			self.refill_task_list()

			# consider the next task
			tsk = self.get_next_task()
			if not tsk:
				if self.count:
					# tasks may add new ones after they are run
					continue
				else:
					# no tasks to run, no tasks running, time to exit
					break

			if tsk.hasrun:
				# if the task is marked as "run", just skip it
				self.processed += 1
				continue

			try:
				st = tsk.runnable_status()
			except Exception as e:
				self.processed += 1
				if self.stop and not self.bld.keep:
					tsk.hasrun = Task.SKIPPED
					continue
				tsk.err_msg = Utils.ex_stack()
				tsk.hasrun = Task.EXCEPTION
				self.error_handler(tsk)
				continue

			if st == Task.ASK_LATER:
				self.postpone(tsk)
				# TODO optimize this
				if self.outstanding:
					for x in tsk.run_after:
						if x in self.outstanding:
							self.outstanding.remove(x)
							self.outstanding.insert(0, x)
			elif st == Task.SKIP_ME:
				self.processed += 1
				tsk.hasrun = Task.SKIPPED
				self.add_more_tasks(tsk)
			else:
				# run me: put the task in ready queue
				tsk.position = (self.processed, self.total)
				self.count += 1
				tsk.master = self
				self.processed += 1

				tsk.log_display(self.bld)

				if self.numjobs == 1:
					tsk.process()
				else:
					self.add_task(tsk)

		# self.count represents the tasks that have been made available to the consumer threads
		# collect all the tasks after an error else the message may be incomplete
		while self.error and self.count:
			self.get_out()

		# free the task pool, if any
		try:
			while self.pool:
				x = self.pool.pop()
				put_pool(x)
		except AttributeError:
			pass

		#print loop
		assert (self.count == 0 or self.stop)

