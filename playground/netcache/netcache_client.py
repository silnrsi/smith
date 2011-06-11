#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2011 (ita)

import os, socket, asyncore, tempfile
import Task, Constants

BUF = 8192 * 16
HEADER_SIZE = 128
Task.net_cache = (socket.gethostname(), 51200)

GET = 'GET'
PUT = 'PUT'
LST = 'LST'
BYE = 'BYE'

def get_connection():
	# return a new connection... do not forget to close it!
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(Task.net_cache)

def close_connection(conn):
	if conn:
		try:
			conn.send(BYE.ljust(HEADER_SIZE))
		except:
			pass
		try:
			conn.close()
		except:
			pass

def recv_file(conn, ssig, cnt, p):
	params = (GET, ssig, str(cnt))
	conn.send(','.join(params).ljust(HEADER_SIZE))
	data = conn.recv(HEADER_SIZE)
	size = int(data.split()[0])

	if size == -1:
		raise ValueError('no file %s - %s in cache' % (ssig, cnt))

	# get the file, writing immediately
	# TODO for static libraries we should use a tmp file
	f = open(p, 'wb')
	cnt = 0
	while cnt < size:
		data = conn.recv(min(BUF, size-cnt))
		if not data:
			raise ValueError('connection ended %r %r' % (cnt, size))
		f.write(data)
		cnt += len(data)
	f.close()

def put_data(conn, ssig, cnt, p):
	#print "pushing %r %r %r" % (ssig, cnt, p)
	size = os.stat(p).st_size
	params = (PUT, ssig, str(cnt), str(size))
	conn.send(','.join(params).ljust(HEADER_SIZE))
	f = open(p, 'rb')
	cnt = 0
	while cnt < size:
		r = f.read(min(BUF, size-cnt))
		while r:
			k = conn.send(r)
			if not k:
				raise ValueError('connection ended')
			cnt += k
			r = r[k:]

def can_retrieve_cache(self):
	if not Task.net_cache:
		return False
	if not self.outputs:
		return False

	self.got_cached = False
	cnt = 0
	sig = self.signature()
	ssig = self.unique_id().encode('hex') + sig.encode('hex')

	conn = None
	try:
		conn = get_connection()
		for node in self.outputs:
			variant = node.variant(self.env)
			p = node.abspath(self.env)
			recv_file(conn, ssig, cnt, p)
			cnt += 1
	except Exception, e:
		close_connection(conn)
		return False

	self.got_cached = True
	return True
Task.Task.can_retrieve_cache = can_retrieve_cache

def post_run(self):
	bld = self.generator.bld
	env = self.env
	sig = self.signature()
	ssig = self.unique_id().encode('hex') + sig.encode('hex')

	conn = None

	cnt = 0
	variant = env.variant()

	try:
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
					if not conn:
						conn = get_connection()
					put_data(conn, ssig, cnt, node.abspath(env))
			except Exception, e:
				#print "Could not restore the files", e
				pass
			cnt += 1
	finally:
		close_connection(conn)

	bld.task_sigs[self.unique_id()] = self.cache_sig
Task.Task.post_run = post_run

