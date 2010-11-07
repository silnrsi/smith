#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"TeX/LaTeX/PDFLaTeX/XeLaTeX support"

import os, re
from waflib import Utils, Task, Runner, Build
from waflib.TaskGen import feature, before
from waflib.Logs import error, warn, debug

re_tex = re.compile(r'\\(?P<type>include|bibliography|includegraphics|input|import|bringin|lstinputlisting)(\[[^\[\]]*\])?{(?P<file>[^{}]*)}',re.M)
def scan(self):
	"""
	A simple regex-based scanner for latex dependencies, uses re_tex from above
	Depending on your needs you might want to change re_tex
	from waflib.Tools import tex
	tex.re_tex = myregex
	or to change
	the method scan from the latex tasks:
	from waflib.Task import classes
	classes['latex'].scan = myscanfunction
	"""
	node = self.inputs[0]
	env = self.env

	nodes = []
	names = []
	if not node: return (nodes, names)

	code = Utils.readf(node.abspath())

	global re_tex
	for match in re_tex.finditer(code):
		path = match.group('file')
		if path:
			for k in ['', '.tex', '.ltx', '.bib']:
				# add another loop for the tex include paths?
				debug('tex: trying %s%s' % (path, k))
				fi = node.parent.find_resource(path + k)
				if fi:
					nodes.append(fi)
					# no break, people are crazy
			else:
				debug('tex: could not find %s' % path)
				names.append(path)

	debug("tex: found the following : %s and names %s" % (nodes, names))
	return (nodes, names)

latex_fun, _ = Task.compile_fun('${LATEX} ${LATEXFLAGS} ${SRCFILE}', shell=False)
pdflatex_fun, _ = Task.compile_fun('${PDFLATEX} ${PDFLATEXFLAGS} ${SRCFILE}', shell=False)
xelatex_fun, _ = Task.compile_fun('${XELATEX} ${XELATEXFLAGS} ${SRCFILE}', shell=False)
bibtex_fun, _ = Task.compile_fun('${BIBTEX} ${BIBTEXFLAGS} ${SRCFILE}', shell=False)
makeindex_fun, _ = Task.compile_fun('${MAKEINDEX} ${MAKEINDEXFLAGS} ${SRCFILE}', shell=False)

g_bibtex_re = re.compile('bibdata', re.M)
def tex_build(task, command='LATEX'):
	env = task.env
	bld = task.generator.bld

	if not env['PROMPT_LATEX']:
		env.append_value('LATEXFLAGS', '-interaction=batchmode')
		env.append_value('PDFLATEXFLAGS', '-interaction=batchmode')
		env.append_value('XELATEXFLAGS', '-interaction=batchmode')

	fun = latex_fun
	if command == 'PDFLATEX':
		fun = pdflatex_fun
	elif command == 'XELATEX':
		fun = xelatex_fun

	node = task.inputs[0]
	srcfile = node.abspath()
	sr2 = node.parent.get_bld().abspath() + os.pathsep + node.parent.get_src().abspath() + os.pathsep

	aux_node = node.change_ext('.aux')
	idx_node = node.change_ext('.idx')

	docuname = aux_node.name[:-4] # 4 is the size of ".aux"

	# important, set the cwd for everybody
	task.cwd = task.inputs[0].parent.get_bld().abspath()

	warn('first pass on %s' % command)

	task.env.env = {}
	task.env.env.update(os.environ)
	task.env.env.update({'TEXINPUTS': sr2})
	task.env.SRCFILE = srcfile
	ret = fun(task)
	if ret:
		return ret

	# look in the .aux file if there is a bibfile to process
	try:
		ct = Utils.readf(aux_node.abspath())
	except (OSError, IOError):
		error('error bibtex scan')
	else:
		fo = g_bibtex_re.findall(ct)

		# there is a .aux file to process
		if fo:
			warn('calling bibtex')

			task.env.env = {'BIBINPUTS': sr2, 'BSTINPUTS': sr2}
			task.env.SRCFILE = docuname
			ret = bibtex_fun(task)
			if ret:
				error('error when calling bibtex %s' % docuname)
				return ret

	# look on the filesystem if there is a .idx file to process
	try:
		idx_path = idx_node.abspath()
		os.stat(idx_path)
	except OSError:
		warn('index file %s absent, not calling makeindex' % idx_path)
	else:
		warn('calling makeindex')

		task.env.SRCFILE = idx_node.name
		task.env.env = {}
		ret = makeindex_fun(task)
		if ret:
			error('error when calling makeindex %s' % idx_path)
			return ret


	hash = ''
	i = 0
	while i < 10:
		# prevent against infinite loops - one never knows
		i += 1

		# watch the contents of file.aux
		prev_hash = hash
		try:
			hash = Utils.h_file(aux_node.abspath())
		except KeyError:
			error('could not read aux.h -> %s' % aux_node.abspath())
			pass

		# debug
		#print "hash is, ", hash, " ", old_hash

		# stop if file.aux does not change anymore
		if hash and hash == prev_hash:
			break

		# run the command
		warn('calling %s' % command)

		task.env.env = {}
		task.env.env.update(os.environ)
		task.env.env.update({'TEXINPUTS': sr2 + os.pathsep})
		task.env.SRCFILE = srcfile
		ret = fun(task)
		if ret:
			error('error when calling %s %s' % (command, task))
			return ret

	return None # ok

latex_vardeps  = ['LATEX', 'LATEXFLAGS']
def latex_build(task):
	return tex_build(task, 'LATEX')

pdflatex_vardeps  = ['PDFLATEX', 'PDFLATEXFLAGS']
def pdflatex_build(task):
	return tex_build(task, 'PDFLATEX')

xelatex_vardeps  = ['XELATEX', 'XELATEXFLAGS']
def xelatex_build(task):
	return tex_build(task, 'XELATEX')

@feature('tex')
@before('process_source')
def apply_tex(self):
	if not getattr(self, 'type', None) in ['latex', 'pdflatex', 'xelatex']:
		self.type = 'pdflatex'

	tree = self.bld
	outs = Utils.to_list(getattr(self, 'outs', []))

	# prompt for incomplete files (else the batchmode is used)
	self.env['PROMPT_LATEX'] = getattr(self, 'prompt', 1)

	deps_lst = []

	if getattr(self, 'deps', None):
		deps = self.to_list(self.deps)
		for filename in deps:
			n = self.path.find_resource(filename)
			if not n in deps_lst: deps_lst.append(n)

	for node in self.to_nodes(self.source):

		if self.type == 'latex':
			task = self.create_task('latex', node, node.change_ext('.dvi'))
		elif self.type == 'pdflatex':
			task = self.create_task('pdflatex', node, node.change_ext('.pdf'))
		elif self.type == 'xelatex':
			task = self.create_task('xelatex', node, node.change_ext('.pdf'))

		task.env = self.env

		# add the manual dependencies
		if deps_lst:
			try:
				lst = tree.node_deps[task.uid()]
				for n in deps_lst:
					if not n in lst:
						lst.append(n)
			except KeyError:
				tree.node_deps[task.uid()] = deps_lst

		if self.type == 'latex':
			if 'ps' in outs:
				tsk = self.create_task('dvips', task.outputs, node.change_ext('.ps'))
				tsk.env.env = {'TEXINPUTS' : node.parent.abspath() + os.pathsep + self.path.abspath() + os.pathsep + self.path.get_bld().abspath()}
			if 'pdf' in outs:
				tsk = self.create_task('dvipdf', task.outputs, node.change_ext('.pdf'))
				tsk.env.env = {'TEXINPUTS' : node.parent.abspath() + os.pathsep + self.path.abspath() + os.pathsep + self.path.get_bld().abspath()}
		elif self.type == 'pdflatex':
			if 'ps' in outs:
				self.create_task('pdf2ps', task.outputs, node.change_ext('.ps'))
	self.source = []

def configure(self):
	v = self.env
	for p in 'tex latex pdflatex xelatex bibtex dvips dvipdf ps2pdf makeindex pdf2ps'.split():
		try:
			self.find_program(p, var=p.upper())
		except self.errors.ConfigurationError:
			pass
	v['DVIPSFLAGS'] = '-Ppdf'

b = Task.task_factory
b('dvips', '${DVIPS} ${DVIPSFLAGS} ${SRC} -o ${TGT}', color='BLUE', after=["latex", "pdflatex", "tex", "bibtex"], shell=False)
b('dvipdf', '${DVIPDF} ${DVIPDFFLAGS} ${SRC} ${TGT}', color='BLUE', after=["latex", "pdflatex", "tex", "bibtex"], shell=False)
b('pdf2ps', '${PDF2PS} ${PDF2PSFLAGS} ${SRC} ${TGT}', color='BLUE', after=["dvipdf", "xelatex", "pdflatex"], shell=False)
b('latex', latex_build, vars=latex_vardeps, scan=scan)
b('pdflatex', pdflatex_build, vars=pdflatex_vardeps, scan=scan)
b('xelatex', xelatex_build, vars=xelatex_vardeps, scan=scan)

