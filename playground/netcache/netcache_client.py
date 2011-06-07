#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2011 (ita)

import os, socket, asyncore, tempfile
import Task, Constants

BUF = 8192
SIZE = 99
Task.net_cache = (socket.gethostname(), 51200)

def recv_file(ssig, cnt, p):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(Task.net_cache)
	params = (ssig, str(cnt))
	s.send(','.join(params).ljust(SIZE))
	data = s.recv(SIZE)
	size = int(data.split()[0])

	if size == -1:
		raise ValueError('no file %s - %s in cache' % (ssig, cnt))

	# get the file, writing immediately
	# TODO for static libraries we should use a tmp file
	f = open(p, 'wb')
	cnt = 0
	while cnt < size:
		data = s.recv(min(BUF, size-cnt))
		if not data:
			raise ValueError('connection ended %r %r' % (cnt, size))
		f.write(data)
		cnt += len(data)
	f.close()
	s.close()

def put_data(ssig, cnt, p):
	#print "pushing %r %r %r" % (ssig, cnt, p)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(Task.net_cache)
	size = os.stat(p).st_size
	params = (ssig, str(cnt), str(size))
	s.send(','.join(params).ljust(SIZE))
	f = open(p, 'rb')
	cnt = 0
	while cnt < size:
		r = f.read(min(BUF, size-cnt))
		while r:
			k = s.send(r)
			if not k:
				raise ValueError('connection ended')
			cnt += k
			r = r[k:]
	s.close()

def can_retrieve_cache(self):
	if not Task.net_cache:
		return False
	if not self.outputs:
		return False

	self.got_cached = False
	cnt = 0
	sig = self.signature()
	ssig = self.unique_id().encode('hex') + sig.encode('hex')

	try:
		for node in self.outputs:
			variant = node.variant(self.env)
			p = node.abspath(self.env)
			recv_file(ssig, cnt, p)
			cnt += 1
	except Exception, e:
		return False

	self.got_cached = True
	return True
Task.Task.can_retrieve_cache = can_retrieve_cache

def post_run(self):
	bld = self.generator.bld
	env = self.env
	sig = self.signature()
	ssig = self.unique_id().encode('hex') + sig.encode('hex')

	cnt = 0
	variant = env.variant()
	for node in self.outputs:
		try:
			os.stat(node.abspath(env))
		except OSError:
			self.has_run = MISSING
			self.err_msg = '-> missing file: %r' % node.abspath(env)
			raise Utils.WafError

		# important, store the signature for the next run
		bld.node_sigs[variant][node.id] = sig

		# We could re-create the signature of the task with the signature of the outputs
		# in practice, this means hashing the output files
		# this is unnecessary
		try:
			if Task.net_cache and not self.got_cached:
				put_data(ssig, cnt, node.abspath(env))
		except Exception, e:
			#print "Could not restore the files", e
			pass
		cnt += 1

	bld.task_sigs[self.unique_id()] = self.cache_sig
Task.Task.post_run = post_run

