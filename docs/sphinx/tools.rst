Waf Tools
=========

C/C++ compiler detection
------------------------

The following Waf tools are used for loading specific C or C++ compilers. They may
be used directly, for example::

	def options(opt):
		opt.load('compiler_c')
	def configure(conf):
		conf.load('compiler_c')

.. toctree::

	tools/compiler_c
	tools/compiler_cxx
	tools/ar
	tools/gcc
	tools/gxx
	tools/icc
	tools/icpc
	tools/suncc
	tools/suncxx
	tools/xlc
	tools/xlcxx
	tools/msvc
	tools/winres

C/C++ support
-------------

The following modules contain the functions and classes required for building C and C++ applications. They
are almost always loaded by other Waf tools.

.. toctree::

	tools/ccroot
	tools/c
	tools/cxx
	tools/c_config
	tools/c_osx
	tools/c_preproc
	tools/c_tests
	tools/c_aliases


Assembly
--------

The following tools provide support for assembly. The module :py:mod:`waflib.Tools.asm` is loaded automatically by :py:mod:`waflib.Tools.nasm` or :py:mod:`waflib.Tools.gas`.

.. toctree::

	tools/gas
	tools/nasm
	tools/asm

D language and compilers
------------------------

The first three tools in the following list may be used for detecting a D compiler. The remaining contain the support functions and classes.

.. toctree::

	tools/compiler_d
	tools/dmd
	tools/gdc
	tools/d_config
	tools/d
	tools/d_scan

C/C++-related applications
--------------------------

The next tools provide support for code generators used in C and C++ projects.

.. toctree::

	tools/bison
	tools/flex
	tools/dbus
	tools/qt4
	tools/kde4
	tools/glib2
	tools/vala
	tools/perl
	tools/python
	tools/ruby
	tools/waf_unit_test

Other compilers and tools
-------------------------

The following tools provide support for specific compilers or configurations.

.. toctree::

	tools/tex
	tools/java
	tools/cs
	tools/gnu_dirs
	tools/intltool
	tools/lua

