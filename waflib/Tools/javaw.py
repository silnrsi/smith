#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
Java support

Javac is one of the few compilers that behaves very badly:
* it outputs files where it wants to (-d is only for the package root)
* it recompiles files silently behind your back
* it outputs an undefined amount of files (inner classes)

Fortunately, the convention makes it possible to use the build dir without
too many problems for the moment

Inner classes must be located and cleaned when a problem arise,
for the moment waf does not track the production of inner classes.

Adding all the files to a task and executing it if any of the input files
change is only annoying for the compilation times

Compilation can be run using Jython[1] rather than regular Python. Instead of
running one of the following commands:
    ./waf configure
    python waf configure
You would have to run:
    java -jar /path/to/jython.jar waf configure

[1] http://www.jython.org/
"""

import os, re
from waflib.Configure import conf
from waflib import TaskGen, Task, Utils, Options, Build
from waflib.TaskGen import feature, before

SOURCE_RE = '**/*.java'
JAR_RE = '**/*'

class_check_source = '''
public class Test {
	public static void main(String[] argv) {
		Class lib;
		if (argv.length < 1) {
			System.err.println("Missing argument");
			System.exit(77);
		}
		try {
			lib = Class.forName(argv[0]);
		} catch (ClassNotFoundException e) {
			System.err.println("ClassNotFoundException");
			System.exit(1);
		}
		lib = null;
		System.exit(0);
	}
}
'''

@feature('jar')
@before('process_source')
def jar_files(self):
	basedir = getattr(self, 'basedir', '.')
	destfile = getattr(self, 'destfile', 'test.jar')
	jaropts = getattr(self, 'jaropts', [])
	jarcreate = getattr(self, 'jarcreate', 'cf')

	d = self.path.find_dir(basedir)
	if not d: raise

	tsk = self.create_task('jar_create')
	tsk.set_outputs(self.path.find_or_declare(destfile))
	tsk.basedir = d

	jaropts.append('-C')
	jaropts.append(d.bldpath())
	jaropts.append('.')

	tsk.env['JAROPTS'] = jaropts
	tsk.env['JARCREATE'] = jarcreate

@feature('javac')
@before('process_source')
def apply_java(self):
	Utils.def_attrs(self, jarname='', jaropts='', classpath='',
		sourcepath='.', srcdir='.',
		jar_mf_attributes={}, jar_mf_classpath=[])

	nodes_lst = []

	if not self.classpath:
		if not self.env['CLASSPATH']:
			self.env['CLASSPATH'] = '..' + os.pathsep + '.'
	else:
		self.env['CLASSPATH'] = self.classpath

	if isinstance(self.srcdir, self.path.__class__):
		srcdir_node = self.srcdir
	else:
		srcdir_node = self.path.find_dir(self.srcdir)
	if not srcdir_node:
		raise Errors.WafError('could not find srcdir %r' % self.srcdir)

	self.env['OUTDIR'] = [srcdir_node.srcpath()]

	tsk = self.create_task('javac')
	tsk.srcdir = srcdir_node

	if getattr(self, 'compat', None):
		tsk.env.append_value('JAVACFLAGS', ['-source', self.compat])

	if hasattr(self, 'sourcepath'):
		fold = [isinstance(x, self.path.__class__) and x or self.path.find_dir(x) for x in self.to_list(self.sourcepath)]
		names = os.pathsep.join([x.srcpath() for x in fold])
	else:
		names = srcdir_node.srcpath()

	if names:
		tsk.env.append_value('JAVACFLAGS', ['-sourcepath', names])

	if self.jarname:
		tsk = self.create_task('jar_create')
		tsk.set_outputs(self.path.find_or_declare(self.jarname))

		if not self.env['JAROPTS']:
			if self.jaropts:
				self.env['JAROPTS'] = self.jaropts
			else:
				dirs = '.'
				self.env['JAROPTS'] = ['-C', ''.join(self.env['OUTDIR']), dirs]

class jar_create(Task.Task):
	color   = 'GREEN'
	run_str = '${JAR} ${JARCREATE} ${TGT} ${JAROPTS}'
	quiet   = True

	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER

		if not self.inputs:
			global JAR_RE
			self.inputs = [x for x in self.basedir.get_bld().ant_glob(JAR_RE, dir=False) if id(x) != id(self.outputs[0])]
		return super(jar_create, self).runnable_status()

class javac(Task.Task):
	color   = 'BLUE'
	run_str = '${JAVAC} -classpath ${CLASSPATH} -d ${OUTDIR} ${JAVACFLAGS} ${SRC}'
	quiet   = True

	def runnable_status(self):
		"""
		the javac task will have its complete inputs only after the other tasks are done
		"""
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER

		if not self.inputs:
			global SOURCE_RE
			self.inputs  = self.srcdir.ant_glob(SOURCE_RE)
		if not self.outputs:
			self.outputs = [x.change_ext('.class') for x in self.inputs]
		return super(javac, self).runnable_status()

	def post_run(self):
		"""record the inner class files created (Class$Foo) - for cleaning the folders mostly
		it is not possible to know which inner classes in advance"""

		lst = set([x.parent for x in self.outputs])

		inner = []
		for k in lst:
			lst = k.listdir()
			for u in lst:
				if u.find('$') >= 0:
					node = k.find_or_declare(u)
					inner.append(node)

		to_add = set(inner) - set(self.outputs)
		self.outputs.extend(list(to_add))
		self.cached = True # disable the cache for this task
		return super(javac, self).post_run()

def configure(self):
	# If JAVA_PATH is set, we prepend it to the path list
	java_path = self.environ['PATH'].split(os.pathsep)
	v = self.env

	if 'JAVA_HOME' in self.environ:
		java_path = [os.path.join(self.environ['JAVA_HOME'], 'bin')] + java_path
		self.env['JAVA_HOME'] = [self.environ['JAVA_HOME']]

	for x in 'javac java jar'.split():
		self.find_program(x, var=x.upper(), path_list=java_path)
		self.env[x.upper()] = self.cmd_to_list(self.env[x.upper()])

	if 'CLASSPATH' in self.environ:
		v['CLASSPATH'] = self.environ['CLASSPATH']

	if not v['JAR']: self.fatal('jar is required for making java packages')
	if not v['JAVAC']: self.fatal('javac is required for compiling java classes')
	v['JARCREATE'] = 'cf' # can use cvf

@conf
def check_java_class(self, classname, with_classpath=None):
	"""Check if the specified java class is installed"""

	import shutil

	javatestdir = '.waf-javatest'

	classpath = javatestdir
	if self.env['CLASSPATH']:
		classpath += os.pathsep + self.env['CLASSPATH']
	if isinstance(with_classpath, str):
		classpath += os.pathsep + with_classpath

	shutil.rmtree(javatestdir, True)
	os.mkdir(javatestdir)

	java_file = open(os.path.join(javatestdir, 'Test.java'), 'w')
	java_file.write(class_check_source)
	java_file.close()

	# Compile the source
	self.exec_command(self.env['JAVAC'] + [os.path.join(javatestdir, 'Test.java')], shell=False)

	# Try to run the app
	cmd = self.env['JAVA'] + ['-cp', classpath, 'Test', classname]
	self.to_log("%s\n" % str(cmd))
	found = self.exec_command(cmd, shell=False)

	self.msg('Checking for java class %s' % classname, not found)

	shutil.rmtree(javatestdir, True)

	return found

@conf
def check_jni_headers(conf):
	"""
	Check for jni headers and libraries

	On success the environment variable xxx_JAVA is added for uselib
	"""

	if not conf.env.CC_NAME and not conf.env.CXX_NAME:
		conf.fatal('load a compiler first (gcc, g++, ..)')

	if not conf.env.JAVA_HOME:
		conf.fatal('set JAVA_HOME in the system environment')

	# jni requires the jvm
	javaHome = conf.env['JAVA_HOME'][0]

	b = Build.BuildContext(top=conf.srcnode.abspath(), out=conf.bldnode.abspath())
	b.init_dirs()
	dir = b.root.find_dir(conf.env.JAVA_HOME[0] + '/include')
	f = dir.ant_glob('**/(jni|jni_md).h')
	incDirs = [x.parent.abspath() for x in f]

	dir = b.root.find_dir(conf.env.JAVA_HOME[0])
	f = dir.ant_glob('**/*jvm.(so|dll)')
	libDirs = [x.parent.abspath() for x in f] or [javaHome]

	for i, d in enumerate(libDirs):
		if conf.check(header_name='jni.h', define_name='HAVE_JNI_H', lib='jvm',
				libpath=d, includes=incDirs, uselib_store='JAVA', uselib='JAVA'):
			break
	else:
		conf.fatal('could not find lib jvm in %r (see config.log)' % libDirs)

