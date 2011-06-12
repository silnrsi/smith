#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2011 (ita)

import os, socket, asyncore, tempfile
from waflib import Task, Logs, Utils

BUF = 8192 * 16
HEADER_SIZE = 128
Task.net_cache = (socket.gethostname(), 51200)

GET = 'GET'
PUT = 'PUT'
LST = 'LST'
BYE = 'BYE'

all_sigs_in_cache = []

def get_connection():
	# return a new connection... do not forget to close it!
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(Task.net_cache)
	return s

def close_connection(conn, msg=''):
	if conn:
		try:
			conn.send(BYE.ljust(HEADER_SIZE))
		except:
			pass
		try:
			conn.close()
		except:
			pass

def read_header(conn):
	cnt = 0
	buf = []
	while cnt < HEADER_SIZE:
		data = conn.recv(HEADER_SIZE - cnt)
		if not data:
			#import traceback
			#traceback.print_stack()
			raise ValueError('connection ended when reading a header %r' % buf)
		buf.append(data)
		cnt += len(data)
	return ''.join(buf)

def check_cache(conn, ssig):
	global all_sigs_in_cache
	if not all_sigs_in_cache:

		params = (LST,'')
		conn.send(','.join(params).ljust(HEADER_SIZE))

		# read what is coming back
		ret = read_header(conn)
		size = int(ret.split(',')[0])

		buf = []
		cnt = 0
		while cnt < size:
			data = conn.recv(min(BUF, size-cnt))
			if not data:
				raise ValueError('connection ended %r %r' % (cnt, size))
			buf.append(data)
			cnt += len(data)
		all_sigs_in_cache = ''.join(buf).split('\n')
		Logs.debug('netcache: server cache has %r entries' % len(all_sigs_in_cache))

	if not ssig in all_sigs_in_cache:
		raise ValueError('no file %s in cache' % ssig)

def recv_file(conn, ssig, count, p):
	check_cache(conn, ssig)

	params = (GET, ssig, str(count))
	conn.send(','.join(params).ljust(HEADER_SIZE))
	data = read_header(conn)

	size = int(data.split(',')[0])

	if size == -1:
		raise ValueError('no file %s - %s in cache' % (ssig, count))

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

#def put_data(conn, ssig, cnt, p):
#	size = os.stat(p).st_size
#	params = (PUT, ssig, str(cnt), str(size))
#	conn.send(','.join(params).ljust(HEADER_SIZE))
#	conn.send(','*size)
#	params = (BYE, 'he')
#	conn.send(','.join(params).ljust(HEADER_SIZE))

def can_retrieve_cache(self):
	if not Task.net_cache:
		return False
	if not self.outputs:
		return False
	self.got_cached = False

	cnt = 0
	sig = self.signature()
	ssig = self.uid().encode('hex') + sig.encode('hex')

	conn = None
	try:
		if not conn:
			conn = get_connection()
		for node in self.outputs:
			p = node.abspath()
			recv_file(conn, ssig, cnt, p)
			cnt += 1
	except Exception, e:
		print e
		close_connection(conn, ',ddddddd')
		return False
	finally:
		close_connection(conn, ',eeeeee')

	for node in self.outputs:
		node.sig = sig
		if self.generator.bld.progress_bar < 1:
			self.generator.bld.to_log('restoring from cache %r\n' % node.abspath())

	self.got_cached = True
	return True
Task.Task.can_retrieve_cache = can_retrieve_cache

@Utils.run_once
def put_files_cache(self):
	#print "called put_files_cache", id(self)
	bld = self.generator.bld
	sig = self.signature()
	ssig = self.uid().encode('hex') + sig.encode('hex')

	conn = None
	cnt = 0
	try:
		for node in self.outputs:
			# We could re-create the signature of the task with the signature of the outputs
			# in practice, this means hashing the output files
			# this is unnecessary
			try:
				if Task.net_cache and not self.got_cached:
					if not conn:
						conn = get_connection()
					put_data(conn, ssig, cnt, node.abspath())
			except Exception, e:
				print "Could not restore the files", e
				pass
			cnt += 1
	finally:
		close_connection(conn)

	bld.task_sigs[self.uid()] = self.cache_sig
Task.Task.put_files_cache = put_files_cache

