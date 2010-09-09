#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007-2010 (ita)

"""
debugging helpers for parallel compilation, outputs
a svg file in the build directory
"""

import os, time, Queue, sys
from waflib import Runner, Options, Utils, Task, Logs

#import random
#random.seed(100)

def options(opt):
	opt.add_option('--dtitle', action='store', default='Parallel build representation for %r' % ' '.join(sys.argv),
		help='title for the svg diagram', dest='dtitle')
	opt.add_option('--dwidth', action='store', type='int', help='diagram width', default=5000, dest='dwidth')
	opt.add_option('--dtime', action='store', type='float', help='recording interval in seconds', default=0.009, dest='dtime')
	opt.add_option('--dband', action='store', type='int', help='band width', default=22, dest='dband')
	opt.add_option('--dmaxtime', action='store', type='float', help='maximum time, for drawing fair comparisons', default=0, dest='dmaxtime')

# red   #ff4d4d
# green #4da74d
# lila  #a751ff

color2code = {
	'GREEN'  : '#4da74d',
	'YELLOW' : '#fefe44',
	'PINK'   : '#a751ff',
	'RED'    : '#cc1d1d',
	'BLUE'   : '#6687bb',
}

mp = {}
info = [] # list of (text,color)

def map_to_color(name):
	if name in mp:
		return mp[name]
	cls = Task.classes[name]
	if cls.color in mp:
		return mp[cls.color]
	if cls.color in color2code:
		return color2code[cls.color]
	return color2code['RED']

def process_task(tsk):
	m = tsk.master
	if m.stop:
		m.out.put(tsk)
		return

	tsk.master.set_running(1, id(Utils.threading.current_thread()), tsk)

	try:
		tsk.generator.bld.to_log(tsk.display())
		if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
		# actual call to task's run() function
		else: ret = tsk.call_run()
	except Exception as e:
		tsk.err_msg = Utils.ex_stack()
		tsk.hasrun = Task.EXCEPTION

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

	tsk.master.set_running(-1, id(Utils.threading.current_thread()), tsk)
	m.out.put(tsk)

Runner.process_task = process_task

old_start = Runner.Parallel.start
def do_start(self):
	try:
		Options.options.dband
	except AttributeError:
		self.bld.fatal('use def options(opt): opt.load("parallel_debug")!')

	self.taskinfo = Queue.Queue()
	old_start(self)
	if self.dirty:
		process_colors(self)
Runner.Parallel.start = do_start

def set_running(self, by, i, tsk):
	self.taskinfo.put( (i, id(tsk), time.time(), tsk.__class__.__name__, self.processed, self.count, by)  )
Runner.Parallel.set_running = set_running

def process_colors(producer):
	# first, cast the parameters
	tmp = []
	try:
		while True:
			tup = producer.taskinfo.get(False)
			tmp.append(list(tup))
	except:
		pass

	try:
		ini = float(tmp[0][2])
	except:
		return

	if not info:
		seen = []
		for x in tmp:
			name = x[3]
			if not name in seen:
				seen.append(name)
			else:
				continue

			info.append((name, map_to_color(name)))
		info.sort(cmp= lambda x, y: cmp(x[0], y[0]))

	thread_count = 0
	acc = []
	for x in tmp:
		thread_count += x[6]
		acc.append("%d %d %f %r %d %d %d" % (x[0], x[1], x[2] - ini, x[3], x[4], x[5], thread_count))
	data_node = producer.bld.path.make_node('pdebug.dat')
	data_node.write('\n'.join(acc))

	tmp = [lst[:2] + [float(lst[2]) - ini] + lst[3:] for lst in tmp]

	st = {}
	for l in tmp:
		if not l[0] in st:
			st[l[0]] = len(st.keys())
	tmp = [  [st[lst[0]]] + lst[1:] for lst in tmp ]
	THREAD_AMOUNT = len(st.keys())

	st = {}
	for l in tmp:
		if not l[1] in st:
			st[l[1]] = len(st.keys())
	tmp = [  [lst[0]] + [st[lst[1]]] + lst[2:] for lst in tmp ]


	BAND = Options.options.dband

	seen = {}
	acc = []
	for x in xrange(len(tmp)):
		line = tmp[x]
		id = line[1]

		if id in seen:
			continue
		seen[id] = True

		begin = line[2]
		thread_id = line[0]
		for y in xrange(x + 1, len(tmp)):
			line = tmp[y]
			if line[1] == id:
				end = line[2]
				#print id, thread_id, begin, end
				#acc.append(  ( 10*thread_id, 10*(thread_id+1), 10*begin, 10*end ) )
				acc.append( (BAND * begin, BAND*thread_id, BAND*end - BAND*begin, BAND, line[3]) )
				break

	if Options.options.dmaxtime < 0.1:
		gwidth = 1
		for x in tmp:
			m = BAND * x[2]
			if m > gwidth:
				gwidth = m
	else:
		gwidth = BAND * Options.options.dmaxtime

	ratio = float(Options.options.dwidth) / gwidth
	gwidth = Options.options.dwidth

	gheight = BAND * (THREAD_AMOUNT + len(info) + 1.5)

	out = []

	out.append("""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>
<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.0//EN\"
\"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd\">
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" version=\"1.0\"
   x=\"%r\" y=\"%r\" width=\"%r\" height=\"%r\"
   id=\"svg602\" xml:space=\"preserve\">
<defs id=\"defs604\" />\n

<!-- inkscape requires a big rectangle or it will not export the pictures properly -->
<rect
   x='%r' y='%r'
   width='%r' height='%r'
   style=\"font-size:10;fill:#ffffff;fill-opacity:0.01;fill-rule:evenodd;stroke:#ffffff;\"
   />\n

""" % (0, 0, gwidth + 4, gheight + 4,   0, 0, gwidth + 4, gheight + 4))

	# main title
	if Options.options.dtitle:
		out.append("""<text x="%d" y="%d" style="font-size:15px; text-anchor:middle; font-style:normal;font-weight:normal;fill:#000000;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;font-family:Bitstream Vera Sans">%s</text>
""" % (gwidth/2, gheight - 5, Options.options.dtitle))

	# the rectangles
	for (x, y, w, h, clsname) in acc:
		out.append("""<rect
   x='%r' y='%r'
   width='%r' height='%r'
   style=\"font-size:10;fill:%s;fill-opacity:1.0;fill-rule:evenodd;stroke:#000000;\"
   />\n""" % (2 + x*ratio, 2 + y, w*ratio, h, map_to_color(clsname)))

	# output the caption
	cnt = THREAD_AMOUNT

	for (text, color) in info:
		# caption box
		b = BAND/2
		out.append("""<rect
		x='%r' y='%r'
		width='%r' height='%r'
		style=\"font-size:10;fill:%s;fill-opacity:1.0;fill-rule:evenodd;stroke:#000000;\"
  />\n""" %                       (2 + BAND,     5 + (cnt + 0.5) * BAND, b, b, color))

		# caption text
		out.append("""<text
   style="font-size:12px;font-style:normal;font-weight:normal;fill:#000000;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;font-family:Bitstream Vera Sans"
   x="%r" y="%d">%s</text>\n""" % (2 + 2 * BAND, 5 + (cnt + 0.5) * BAND + 10, text))
		cnt += 1

	out.append("\n</svg>")

	node = producer.bld.path.make_node('pdebug.svg')
	node.write("".join(out))
	Logs.warn('Created the diagram %r' % node.abspath())

	p = node.parent.abspath()
	producer.bld.exec_command(['convert', p + os.sep + 'pdebug.svg', p + os.sep + 'pdebug.png'])

