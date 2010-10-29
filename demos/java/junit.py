#! /usr/bin/env python
# encoding: utf-8

"""
JUnit test system

 - executes all junit tests in the specified subtree (junitsrc)
   - only if --junit is given on the commandline
   - method:
	 - add task to compile junitsrc after compiling srcdir
	   - additional junit_classpath specifiable
		 - defaults to classpath + destdir
	 - add task to run junit tests after they're compiled.
"""

from waflib import Task, TaskGen, Utils, Options
from waflib.TaskGen import feature, before, after
from waflib.Configure import conf

JUNIT_RUNNER = 'org.junit.runner.JUnitCore'

def options(opt):
	opt.add_option('--junit', action='store_true', default=False,
		help='Run all junit tests', dest='junit')
	opt.add_option('--junitpath', action='store', default='',
		help='Give a path to the junit jar')

@conf
def configure(ctx):
	cp = ctx.options.junitpath
	val = ctx.env.JUNIT_RUNNER or JUNIT_RUNNER
	try:
		ctx.check_java_class(val, with_classpath=cp)
	except:
		ctx.fatal('Could not run junit from %r' % val)
	else:
		ctx.env.CLASSPATH_JUNIT = cp

@feature('junit')
@after('apply_java', 'use_javac_files')
def make_test(self):
	"""make the unit test task"""
	if not getattr(self, 'junitsrc', None):
		return
	junit_task = self.create_task('junit_test')
	#junit_task.set_outputs(self.path.find_or_declare(destdir))

class junit_test(Task.Task):
	run_str = '${JAVA} -classpath ${CLASSPATH} ${JUNIT_RUNNER} ${JUNIT_TESTS}'

	def runnable_status(self):
		# Only run if --junit was set as an option
		ret = super(junit_test, self).runnable_status()
		if ret == Task.SKIP_ME:
			if getattr(Options.options, 'junit', False):
				return Task.RUN_ME
		return ret
	"""
	def post_run(self):
		junit_src = getattr(self.generator.bld, 'junitsrc', None)
		if not junit_src:
			return
	"""

