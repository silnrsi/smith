from waflib.Task import Task
class src2cpp(Task):
	run_str = '${COMP} ${SRC} ${TGT}'
	color   = 'PINK'

from waflib.TaskGen import extension

@extension('.src')
def process_src(self, node):
	tg = self.bld.get_tgen_by_name('comp')
	tg.post()

	tsk = self.create_task('src2cpp', node, node.change_ext('.cpp'))

	tsk.env.COMP = tg.link_task.outputs[0].abspath()

