#!/usr/bin/env python
# encoding: utf-8
#
# written by Sylvain Rouquette, 2011

'''
To add the freeimage tool to the waf file:
$ ./waf-light --tools=compat15,freeimage
    or, if you have waf >= 1.6.2
$ ./waf update --files=freeimage

The wscript will look like:

def options(opt):
    opt.load('compiler_c freeimage')

def configure(conf):
    conf.load('compiler_c freeimage')
    
    # you can call check_freeimage with some parameters.
    # It's optional on Linux, it's 'mandatory' on Windows if
    # you didn't use --fi-path on the command-line

    # conf.check_freeimage(path='FreeImage/Dist', fip=True)

def build(bld):
    bld(source='main.cpp', target='app', use='FREEIMAGE')
'''

import os, sys, re
from waflib import Options, Utils, Logs
from waflib.Configure import conf

def options(opt):
    opt.add_option('--fi-path', type='string', default='', dest='fi_path',
                   help='''path to the FreeImage directory where the files are 
                   e.g. /FreeImage/Dist''')
    opt.add_option('--fip', action='store_true', default=False, dest='fip',
                   help='link with FreeImagePlus')
    opt.add_option('--fi-shared', action='store_true', default=False, dest='fi_shared',
                   help="link as shared libraries")

@conf
def check_freeimage(self, path=None, fip=False):
    self.start_msg('Checking FreeImage')
    if not self.env['CXX']:
        self.fatal('you must load compiler_cxx before loading freeimage')
    prefix = Options.options.fi_shared and '' or 'ST'
    platform = Utils.unversioned_sys_platform()
    if platform == 'win32':
        if not path:
            self.fatal('you must specify the path to FreeImage. use --fi-path=/FreeImage/Dist')
        else:
            self.env['INCLUDES_FREEIMAGE'] = path
            self.env['%sLIBPATH_FREEIMAGE' % prefix] = path
        if Options.options.fip:
            self.env['%sLIB_FREEIMAGE' % prefix] = ['FreeImage', 'FreeImagePlus']
        else:
            self.env['%sLIB_FREEIMAGE' % prefix] = ['FreeImage']
    else:
        if Options.options.fip:
            self.env['%sLIB_FREEIMAGE' % prefix] = ['freeimage', 'freeimageplus']
        else:
            self.env['%sLIB_FREEIMAGE' % prefix] = ['freeimage']
    self.end_msg('ok')

def configure(conf):
    platform = Utils.unversioned_sys_platform()
    if platform == 'win32' and not Options.options.fi_path:
        return
    conf.check_freeimage(Options.options.fi_path, Options.options.fip)
