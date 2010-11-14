Waf tutorial
============

.. como le encanta la gasolina

Waf is a piece of software used to help building software projects.
The goal of this tutorial is to provide a quick overview of how to set up
the scripts for a project using Waf.

Waf scripts and commands
------------------------

A software typically has *source files* which are kept in a version control system (git, subversion, etc),
and *build scripts* (Makefiles, ..) which describe what to do with those files. A few *build files* are usually
obtained after transforming the *source files*, but they are optional. In Waf, the build script are files named 'wscript'.

In general, a project will consist of several phases:

* configure: configure the project, find the location of the prerequisites
* build: transform the source files into build files
* install: install the build files
* uninstall: uninstall the build files
* dist: create an archive of the source files
* clean: remove the build files

Each phase is modelled in the wscript file as a python function which takes as argument an instance of :py:class:`waflib.Context.Context`.
Let's start with a new wscript file in the directory '/tmp/myproject'::

	def configure(conf):
		print("configure!")

	def build(bld):
		print("build")

We will also use a Waf binary file, for example http://waf.googlecode.com/files/waf-1.6.1, which we will copy in the project directory::

	$ cd /tmp/myproject
	$ wget http://waf.googlecode.com/files/waf-1.6.1

To execute the project, we will simply call the command as an argument to ``waf``::

	$ ./waf-1.6.1 configure build
	configure!
	build!

Targets
-------

An important part of the build system is to declare the creation of targets. Here is a very simple example::

	def build(bld):
		tg = bld(rule='cp ${SRC} ${TGT}', source='wscript', target='foo.txt')
		bld(rule='cp ${SRC} ${TGT}', source='foo.txt', target='bar.txt')

The call ``bld(..)`` creates an object called *task generator*, which is used to create *tasks* which will actually
call the command ``cp``. The commands are not executed unless all the scripts have been read, which is important
for computing the build order.

The expressions *${SRC}* and *${TGT}* are shortcuts to avoid repeating the file names. More shortcuts can be defined
by using the *${}* symbol, which reads the values from the attribute bld.env::

	def build(bld):
		bld.env.MESSAGE = 'Hello, world!'
		bld(rule='echo ${MESSAGE}', always=True)

The bld object is an instance of :py:class:`waflib.Build.BuildContext`, its *env* attribute is an instance :py:class:`waflib.ConfigSet.ConfigSet`.
The values are set in this object to be shared/stored/loaded easily. Here is how to do the same thing by sharing data between the configuration and build::

	def configure(cnf):
		cnf.env.MESSAGE = 'Hello, world!'

	def build(bld):
		bld(rule='echo ${MESSAGE}', always=True)

Scripts and Tools
-----------------

To let a script use a script from a subdirectory, the method :py:meth:`waflib.Context.Context.recurse` has to be used with
the relative path to the folder containing the wscript file. For example, to call the function *build* in the script ``src/wscript``,
one should write::

	def build(bld):
		bld.recurse('src')

The support for specific languages and compilers is provided through specific modules called *Waf tools*. The tools are
similar to wscript files and provide functions such as *configure* or *build*. Here is a simple project for the c language::

	def options(opt):
		opt.load('compiler_c')
	def configure(cnf):
		cnf.load('compiler_c')
	def build(bld):
		bld(features='c cprogram', source='main.c', target='app')

The function *options* is another predefined command used for setting command-line options. Its argument is an instance of :py:meth:`waflib.Options.OptionsContext`. The tool *compiler_c* is provided for detecting if a c compiler is present and set various variables such as cnf.env.CFLAGS.

The task generator declared in *bld* does not have a *rule* keyword, but a list of *features* which is used to reference methods that will call the appropriate rules. In this case, a rule is called for compiling the file, and another is used for linking the object files into the binary 'app'. Other tool-dependent features exist such as 'javac', 'cs', or 'tex'.


