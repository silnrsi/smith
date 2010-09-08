#!/usr/bin/env python
# encoding: utf-8

import os, sys, imp, types
from waflib import Utils, Configure, Options
from waflib.extras import fc

fc_compiler = {
	'darwin' : ['gfortran', 'ifort'],
	'linux'  : ['gfortran', 'ifort'],
	'default': ['gfortran']
}

def __list_possible_compiler(platform):
	try:
		return fc_compiler[platform]
	except KeyError:
		return fc_compiler["default"]

def configure(conf):
	try:
		test_for_compiler = Options.options.check_fc
	except AttributeError:
		raise Configure.ConfigurationError("Add set_options(opt): opt.pimp('compiler_fortran')")
	orig = conf.env
	for compiler in test_for_compiler.split():
		try:
			conf.start_msg('Checking for %r (fortran compiler)' % compiler)
			conf.env = orig.derive()
			conf.check_tool(compiler)
		except conf.errors.ConfigurationError as e:
			conf.end_msg(False)
			debug('compiler_fortran: %r' % e)
		else:
			if conf.env['FC']:
				orig.table = conf.env.get_merged_dict()
				conf.env = orig
				conf.end_msg(True)
				conf.env.COMPILER_FORTRAN = compiler
				break
			conf.end_msg(False)
	else:
		conf.fatal('could not configure a fortran compiler!')

def options(opt):
	build_platform = Utils.unversioned_sys_platform()
	detected_platform = Options.platform
	possible_compiler_list = __list_possible_compiler(detected_platform)
	test_for_compiler = ' '.join(possible_compiler_list)
	fortran_compiler_opts = opt.add_option_group("Fortran Compiler Options")
	fortran_compiler_opts.add_option('--check-fortran-compiler',
			default="%s" % test_for_compiler,
			help='On this platform (%s) the following Fortran Compiler will be checked by default: "%s"' % (detected_platform, test_for_compiler),
		dest="check_fc")

	for compiler in test_for_compiler.split():
		opt.pimp('%s' % compiler, option_group=fortran_compiler_opts)

