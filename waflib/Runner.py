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

GAP = 15
MAXJOBS = 999

class TaskConsumer(Utils.threading.Thread):
	ready = Queue(0)
	pool = []

	def __init__(self):
		Utils.threading.Thread.__init__(self)
		self.setDaemon(1)
		self.start()

	def run(self):
		try:
			self.loop()
		except:
			pass

	def loop(self):
		while 1:
			tsk = TaskConsumer.ready.get()
			process_task(tsk)

def process_task(tsk):
	m = tsk.master
	if m.stop:
		m.out.put(tsk)
		return

	try:
		tsk.generator.bld.to_log(tsk.display())
		if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
		# actual call to task's run() function
		else: ret = tsk.call_run()
	except Exception as e:
		tsk.err_msg = Utils.ex_stack()
		tsk.hasrun = Task.EXCEPTION

		# TODO cleanup
		m.error_handler(tsk)
		m.out.put(tsk)
		return

	if ret:
		tsk.err_code = ret
		tsk.hasrun = Task.CRASHED
	else:
		try:
			tsk.post_run()
		except Errors.WafError:
			pass
		except Exception:
			tsk.err_msg = Utils.ex_stack()
			tsk.hasrun = Task.EXCEPTION
		else:
			tsk.hasrun = Task.SUCCESS
	if tsk.hasrun != Task.SUCCESS:
		m.error_handler(tsk)

	m.out.put(tsk)

class Parallel(object):
	"""
	keep the consumer threads busy, and avoid consuming cpu cycles
	when no more tasks can be added (end of the build, etc)
	"""
	def __init__(self, bld, j=2):

		# number of consumers in the pool
		self.numjobs = j

		self.bld = bld # build context

		self.total = self.bld.total()

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		self.maxjobs = MAXJOBS

		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks waiting to be run by the consumers pool
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

		while self.count > self.numjobs + GAP or self.count >= self.maxjobs:
			self.get_out()

		while not self.outstanding:
			if self.count:
				self.get_out()

			if self.frozen:
				self.outstanding += self.frozen
				self.frozen = []
			elif not self.count:
				self.outstanding.extend(next(self.biter))
				self.total = self.bld.total()
				break

	def add_more_tasks(self, tsk):
		if getattr(tsk, 'more_tasks', None):
			self.outstanding += tsk.more_tasks
			self.total += len(tsk.more_tasks)

	def get_out(self):
		"the tasks that are put to execute are all collected using get_out"
		ret = self.out.get()
		if not self.stop:
			self.add_more_tasks(tsk)
		self.count -= 1
		self.dirty = True

	def error_handler(self, tsk):
		"by default, errors make the build stop (not thread safe so be careful)"
		if not self.bld.keep:
			self.stop = True
		self.error.append(tsk)

	def start(self):
		"execute the tasks"

		if TaskConsumer.pool:
			# the worker pool is usually loaded lazily (see below)
			# in case it is re-used with a different value of numjobs:
			while len(TaskConsumer.pool) < self.numjobs:
				TaskConsumer.pool.append(TaskConsumer())

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

				if self.numjobs == 1:
					process_task(tsk)
				else:
					TaskConsumer.ready.put(tsk)
					# create the consumer threads only if there is something to consume
					if not TaskConsumer.pool:
						TaskConsumer.pool = [TaskConsumer() for i in range(self.numjobs)]


		# self.count represents the tasks that have been made available to the consumer threads
		# collect all the tasks after an error else the message may be incomplete
		while self.error and self.count:
			self.get_out()

		#print loop
		assert (self.count == 0 or self.stop)

