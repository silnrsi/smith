#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy 2011 (ita)

"""
Simple TCP server to cache files over the network
It uses a LRU (least recently used).

TODO:
* retrieve several files at once
* convert into a DHT
"""

import os, tempfile, socket
import SocketServer

CACHEDIR = '/tmp/wafcache'
CONN = (socket.gethostname(), 51200)
HEADER_SIZE = 128
BUF = 8192*16
MAX = 10*1024*1024*1024 # in bytes
CLEANRATIO = 0.8

GET = 'GET'
PUT = 'PUT'
LST = 'LST'
BYE = 'BYE'

flist = {}
def init_flist():
	"""map the cache folder names to the timestamps and sizes"""
	global flist
	try:
		os.makedirs(CACHEDIR)
	except:
		pass
	flist = dict( (x, [os.stat(os.path.join(CACHEDIR, x)).st_mtime, 0]) for x in os.listdir(CACHEDIR) if os.path.isdir(os.path.join(CACHEDIR, x)))
	for (x, v) in flist.items():
		cnt = 0
		d = os.path.join(CACHEDIR, x)
		for k in os.listdir(d):
			cnt += os.stat(os.path.join(d, k)).st_size
		flist[x][1] = cnt

def make_clean(ssig):
	"""update the cache folder and make some space if necessary"""
	global MAX, flist

	# D, T, S : directory, timestamp, size

	# update the contents with the last folder created
	cnt = 0
	d = os.path.join(CACHEDIR, ssig)
	for k in os.listdir(d):
		cnt += os.stat(os.path.join(d, k)).st_size
	try:
		flist[ssig][1] = cnt
	except:
		flist[ssig] = [os.stat(d).st_mtime, cnt]

	# and do some cleanup if necessary
	total = sum([x[1] for x in flist.values()])

	#print("and the total is %d" % total)

	if total >= MAX:
		print("Trimming the cache since %r > %r" % (total, MAX))
		lst = [(p, v[0], v[1]) for (p, v) in flist.items()]
		lst.sort(key=lambda x: x[1]) # sort by timestamp
		lst.reverse()

		while total >= MAX * CLEANRATIO:
			(k, t, s) = lst.pop()
			os.removedirs(k)
			total -= s
			del flist[k]

class req(SocketServer.StreamRequestHandler):
	def handle(self):
		while 1:
			try:
				self.process_command()
			except Exception:
				#print e
				break

	def process_command(self):
		query = self.rfile.read(HEADER_SIZE)
		#print "%r" % query
		query = query.strip().split(',')

		if query[0] == GET:
			self.get_file(query[1:])
		elif query[0] == PUT:
			self.put_file(query[1:])
		elif query[0] == LST:
			self.lst_file(query[1:])
		elif query[0] == BYE:
			raise ValueError('exit')
		else:
			raise ValueError("invalid command %r" % query)

	def lst_file(self, query):
		response = '\n'.join(flist.keys())
		params = [str(len(response)),'']
		self.wfile.write(','.join(params).ljust(HEADER_SIZE))
		self.wfile.write(response)

	def get_file(self, query):
		# get a file from the cache if it exists, else return 0
		tmp = os.path.join(CACHEDIR, query[0], query[1])
		fsize = -1
		try:
			fsize = os.stat(tmp).st_size
		except Exception, e:
			#print(e)
			pass
		else:
			# cache was useful, update the last access
			d = os.path.join(CACHEDIR, query[0])
			os.utime(d, None)
			flist[query[0]][0] = os.stat(d).st_mtime
		params = [str(fsize)]
		self.wfile.write(','.join(params).ljust(HEADER_SIZE))

		if fsize < 0:
			#print("file not found in cache %s" % query[0])
			return
		f = open(tmp, 'rb')
		cnt = 0
		while cnt < fsize:
			r = f.read(BUF)
			self.wfile.write(r)
			cnt += len(r)

	def put_file(self, query):
		# add a file to the cache, the tird parameter is the file size
		(fd, filename) = tempfile.mkstemp(dir=CACHEDIR)
		try:
			size = int(query[2])
			cnt = 0
			while cnt < size:
				r = self.rfile.read(min(BUF, size-cnt))
				if not r:
					raise ValueError('Connection closed')
				os.write(fd, r)
				cnt += len(r)
		finally:
			os.close(fd)


		d = os.path.join(CACHEDIR, query[0])
		try:
			os.stat(d)
		except:
			try:
				# obvious race condition here
				os.makedirs(d)
			except:
				pass
		os.rename(filename, os.path.join(d, query[1]))
		make_clean(query[0])

if __name__ == '__main__':
	init_flist()
	print("ready (%r dirs)" % len(flist.keys()))
	SocketServer.ThreadingTCPServer.allow_reuse_address = True
	server = SocketServer.ThreadingTCPServer(CONN, req)
	server.timeout = 60 # i think it sounds reasonable
	server.serve_forever()

