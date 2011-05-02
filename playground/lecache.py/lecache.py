#! /usr/bin/env python

import os
import SocketServer

SIZE = 100
BUF = 8192

class req(SocketServer.StreamRequestHandler):
	def handle(self):
		self.rfile.read(SIZE)

		p = '/home/waf/plat.jpg'
		fsize = os.stat(p).st_size
		params = [str(fsize)]
		self.wfile.write(','.join(params).ljust(SIZE))
		f = open(p, 'rb')
		cnt = 0
		while cnt < fsize:
			r = f.read(BUF)
			self.wfile.write(r)
			cnt += len(r)
		print "transfer complete"

server = SocketServer.TCPServer( ('', 51200), req)
server.serve_forever()


