#! /usr/bin/env python
# Thomas Nagy, 2011 (ita)

from waflib.TaskGen import extension
from waflib import Task
import waflib.Tools.qt4
import waflib.Tools.cxx

@extension(*waflib.Tools.qt4.EXT_QT4)
def cxx_hook(self, node):
	self.create_compiled_task('cxx_qt', node)

class cxx_qt(waflib.Tools.cxx.cxx):
	def runnable_status(self):
		ret = waflib.Tools.cxx.cxx.runnable_status(self)
		if ret != Task.ASK_LATER and not getattr(self, 'moc_done', None):

			deps = self.generator.bld.node_deps[self.uid()]
			for x in [self.inputs[0]] + deps:
				if x.read().find('Q_OBJECT') > 0:

					cxx_node = x.parent.get_bld().make_node(x.name.replace('.', '_') + '_moc.cpp')

					tsk = Task.classes['moc'](env=self.env, generator=self.generator)
					tsk.set_inputs(x)
					tsk.set_outputs(cxx_node)

					if x.name.endswith('.cpp'):
						# moc is trying to be too smart but it is too dumb:
						# why forcing the #include when Q_OBJECT is in the cpp file?
						gen = self.generator.bld.producer
						gen.outstanding.insert(0, tsk)
						gen.total += 1
						self.set_run_after(tsk)
					else:
						cxxtsk = Task.classes['cxx'](env=self.env, generator=self.generator)
						cxxtsk.set_inputs(tsk.outputs)
						cxxtsk.set_outputs(cxx_node.change_ext('.o'))
						cxxtsk.set_run_after(tsk)

						self.more_tasks = [tsk, cxxtsk]

						try:
							link = self.generator.link_task
						except:
							pass
						else:
							link.set_run_after(cxxtsk)
							link.inputs.extend(cxxtsk.outputs)

			self.moc_done = True

		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER

		return ret

