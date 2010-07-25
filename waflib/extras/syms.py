#! /usr/bin/env python
# encoding: utf-8

import re
from waflib.Context import STDOUT
from waflib.Task import Task
from waflib.Errors import WafError
class nom_nom_nom(Task):

	def filter(self, x):
		lst = self.re_nm.findall(x)
		if self.generator.bld.get_dest_binfmt() == 'pe':
			lst = [x[1:].strip()[1:] for x in lst] #x is like "T _foo", but we need only "foo"
		elif self.generator.bld.get_dest_binfmt() == 'elf':
			lst = [x[1:].strip() for x in lst]
		else:
			raise NotImplemented
		return ' '.join(lst)

	def run(self):
		syms = []
		for x in self.inputs:
			if 'msvc' in (self.env.CC_NAME, self.env.CXX_NAME):
				self.re_nm = re.compile(r'\|\s+_' + self.generator.export_symbols_regex + r'\b')
				s = self.filter(self.generator.bld.cmd_and_log(['dumpbin', '/symbols', x.abspath()], quiet=STDOUT))
			else:
				if self.generator.bld.get_dest_binfmt() == 'pe': #gcc uses nm, and has a preceding _ on windows
					self.re_nm = re.compile(r'T\s+_' + self.generator.export_symbols_regex + r'\b')
				else:
					self.re_nm = re.compile(r'T\s+' + self.generator.export_symbols_regex + r'\b')
				s = self.filter(self.generator.bld.cmd_and_log(['nm', x.abspath()], quiet=STDOUT))
			syms.append(s)
		if self.generator.bld.get_dest_binfmt() == 'pe':
			self.outputs[0].write('EXPORTS\n' + '\n'.join(syms))
		elif self.generator.bld.get_dest_binfmt() == 'elf':
			self.outputs[0].write('{ global:\n' + ';\n'.join(syms) + ";\nlocal: *; };\n")
		else:
			raise NotImplemented

from waflib.TaskGen import before, feature, after

@feature('syms')
@after('process_source', 'process_use', 'apply_link', 'process_uselib_local')
def do_the_symbol_stuff(self):
	ins = [x.outputs[0] for x in self.compiled_tasks]
	tsk = self.create_task('nom_nom_nom', ins, self.path.find_or_declare('foo.def'))
	self.link_task.set_run_after(tsk)
	self.link_task.dep_nodes = [tsk.outputs[0]]
	if 'msvc' in (self.env.CC_NAME, self.env.CXX_NAME):
		self.link_task.env.append_value('LINKFLAGS', ['/def:' + tsk.outputs[0].bldpath()])
	elif self.bld.get_dest_binfmt() == 'pe':
		self.link_task.inputs.append(tsk.outputs[0])
	elif self.bld.get_dest_binfmt() == 'elf':
		self.link_task.env.append_value('LINKFLAGS', ['-Wl,-version-script', '-Wl,' + tsk.outputs[0].bldpath()])
	else:
		raise NotImplemented
	
