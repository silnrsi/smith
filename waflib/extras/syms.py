#! /usr/bin/env python
# encoding: utf-8

"""
this tool supports the export_symbols_regex to export the symbols in a shared library.
by default, all symbols are exported by gcc, and nothing by msvc.
to use the tool, do something like:

def build(ctx):
	ctx(features='c cshlib syms', source='a.c b.c', export_symbols_regex='mylib_.*', target='testlib')

only the symbols starting with 'mylib_' will be exported.
"""

import re
from waflib.Context import STDOUT
from waflib.Task import Task
from waflib.Errors import WafError
class generate_sym_task(Task):
	def run(self):
		syms = {}
		for x in self.inputs:
			if 'msvc' in (self.env.CC_NAME, self.env.CXX_NAME):
				re_nm = re.compile(r'External\s+\|\s+_(' + self.generator.export_symbols_regex + r')\b')
				cmd = ['dumpbin', '/symbols', x.abspath()]
			else:
				if self.generator.bld.get_dest_binfmt() == 'pe': #gcc uses nm, and has a preceding _ on windows
					re_nm = re.compile(r'T\s+_(' + self.generator.export_symbols_regex + r')\b')
				else:
					re_nm = re.compile(r'T\s+(' + self.generator.export_symbols_regex + r')\b')
				cmd = ['nm', '-g', x.abspath()]
			for s in re_nm.findall(self.generator.bld.cmd_and_log(cmd, quiet=STDOUT)):
				syms[s] = 1
		lsyms = syms.keys()
		lsyms.sort()
		if self.generator.bld.get_dest_binfmt() == 'pe':
			self.outputs[0].write('EXPORTS\n' + '\n'.join(lsyms))
		elif self.generator.bld.get_dest_binfmt() == 'elf':
			self.outputs[0].write('{ global:\n' + ';\n'.join(lsyms) + ";\nlocal: *; };\n")
		else:
			raise Exception('NotImplemented')

from waflib.TaskGen import before, feature, after

@feature('syms')
@after('process_source', 'process_use', 'apply_link', 'process_uselib_local')
def do_the_symbol_stuff(self):
	ins = [x.outputs[0] for x in self.compiled_tasks]
	tsk = self.create_task('generate_sym', ins, self.path.find_or_declare('foo.def'))
	self.link_task.set_run_after(tsk)
	self.link_task.dep_nodes = [tsk.outputs[0]]
	if 'msvc' in (self.env.CC_NAME, self.env.CXX_NAME):
		self.link_task.env.append_value('LINKFLAGS', ['/def:' + tsk.outputs[0].bldpath()])
	elif self.bld.get_dest_binfmt() == 'pe':
		self.link_task.inputs.append(tsk.outputs[0])
	elif self.bld.get_dest_binfmt() == 'elf':
		self.link_task.env.append_value('LINKFLAGS', ['-Wl,-version-script', '-Wl,' + tsk.outputs[0].bldpath()])
	else:
		raise Exception('NotImplemented')

