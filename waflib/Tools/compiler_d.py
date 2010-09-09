#!/usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2010 (ita)

import os, sys, imp, types
from waflib import Utils, Configure, Options, Logs

def configure(conf):
	if getattr(Options.options, 'check_dmd_first', None):
		test_for_compiler = ['dmd', 'gdc']
	else:
		test_for_compiler = ['gdc', 'dmd']

	for compiler in test_for_compiler:
		conf.env.stash()
		conf.start_msg('Checking for %r (d compiler)' % compiler)
		try:
			conf.load(compiler)
		except conf.errors.ConfigurationError as e:
			conf.env.revert()
			conf.end_msg(False)
			Logs.debug('compiler_cxx: %r' % e)
		else:
			if conf.env.D:
				orig.table = conf.env.get_merged_dict()
				conf.end_msg(True)
				conf.env['COMPILER_D'] = compiler
				conf.env.D_COMPILER = conf.env.D # TODO remove this
				break
			conf.end_msg(False)
	else:
		conf.fatal('no suitable d compiler was found')

def options(opt):
	d_compiler_opts = opt.add_option_group('D Compiler Options')
	d_compiler_opts.add_option('--check-dmd-first', action='store_true',
			help='checks for the gdc compiler before dmd (default is the other way round)',
			dest='check_dmd_first',
			default=False)

	for d_compiler in ['gdc', 'dmd']:
		opt.load('%s' % d_compiler, option_group=d_compiler_opts)

