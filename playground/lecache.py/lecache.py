#! /usr/bin/env python

import os, tempfile
import SocketServer

CONN = ('', 51200)
SIZE = 50
BUF = 8192

tmp = '/home/waf/plat.jpg'
GET = 2
PUT = 3

class req(SocketServer.StreamRequestHandler):
	def handle(self):
		query = self.rfile.read(SIZE).strip().split(',')
		if len(query) == GET:
			# get a file from the cache if it exists, else return 0
			tmp = os.path.join(query[0], query[1])
			fsize = 0
			try:
				fsize = os.stat(tmp).st_size
			except:
				pass
			params = [str(fsize)]
			self.wfile.write(','.join(params).ljust(SIZE))

			if not fsize:
				print("file not found in cache %s" % query[0])
				return

			f = open(tmp, 'rb')
			cnt = 0
			while cnt < fsize:
				r = f.read(BUF)
				self.wfile.write(r)
				cnt += len(r)
		elif len(query) == PUT:
			# add a file to the cache, the tird parameter is the file size
			(fd, filename) = tempfile.mkstemp()
			try:
				size = int(query[2])
				cnt = 0
				while cnt < size:
					r = self.rfile.read(BUF)
					if not r:
						raise ValueError('Connection closed')
					os.write(fd, r)
					cnt += len(r)
			except Exception, e:
				print e
				raise
			finally:
				os.close(fd)

			try:
				os.stat(query[0])
			except:
				os.makedirs(query[0])
			os.rename(filename, os.path.join(query[0], query[1]))
		else:
			print "invalid query", query

server = SocketServer.TCPServer(CONN, req)
server.serve_forever()


