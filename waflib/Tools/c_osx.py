#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy 2008-2010

"""
MacOSX related tools
"""

import os, shutil, sys, platform
from waflib import TaskGen, Task, Build, Options, Utils
from waflib.TaskGen import taskgen_method, feature, after, before

app_info = '''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleGetInfoString</key>
	<string>Created by Waf</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>NOTE</key>
	<string>THIS IS A GENERATED FILE, DO NOT MODIFY</string>
	<key>CFBundleExecutable</key>
	<string>%s</string>
</dict>
</plist>
'''
"""
plist template
"""

@feature('c', 'cxx')
def set_macosx_deployment_target(self):
	"""
	see WAF issue 285 and also and also http://trac.macports.org/ticket/17059
	"""
	if self.env['MACOSX_DEPLOYMENT_TARGET']:
		os.environ['MACOSX_DEPLOYMENT_TARGET'] = self.env['MACOSX_DEPLOYMENT_TARGET']
	elif 'MACOSX_DEPLOYMENT_TARGET' not in os.environ:
		if sys.platform == 'darwin':
			os.environ['MACOSX_DEPLOYMENT_TARGET'] = '.'.join(platform.mac_ver()[0].split('.')[:2])

@taskgen_method
def create_bundle_dirs(self, name, out):
	"""
	Create bundle folders, used by :py:func:`create_task_macplist` and :py:func:`create_task_macapp`
	"""
	bld = self.bld
	dir = out.parent.get_dir(name)

	if not dir:
		dir = out.__class__(name, out.parent, 1)
		bld.rescan(dir)
		contents = out.__class__('Contents', dir, 1)
		bld.rescan(contents)
		macos = out.__class__('MacOS', contents, 1)
		bld.rescan(macos)
	return dir

def bundle_name_for_output(out):
	name = out.name
	k = name.rfind('.')
	if k >= 0:
		name = name[:k] + '.app'
	else:
		name = name + '.app'
	return name

@feature('cprogram', 'cxxprogram')
@after('apply_link')
def create_task_macapp(self):
	"""
	To compile an executable into a Mac application (a .app), set its *mac_app* attribute::

		def build(bld):
			bld.shlib(source='a.c', target='foo', mac_app = True)

	To force *all* executables to be transformed into Mac applications::

		def build(bld):
			bld.env.MACAPP = True
			bld.shlib(source='a.c', target='foo')
	"""
	if self.env['MACAPP'] or getattr(self, 'mac_app', False):
		apptask = self.create_task('macapp', self.link_task.outputs)

		out = self.link_task.outputs[0]

		name = bundle_name_for_output(out)
		dir = self.create_bundle_dirs(name, out)

		n1 = dir.find_or_declare(['Contents', 'MacOS', out.name])

		apptask.set_outputs([n1])
		apptask.chmod = Utils.O755
		apptask.install_path = os.path.join(self.install_path, name, 'Contents', 'MacOS')
		self.apptask = apptask

@feature('cprogram', 'cxxprogram')
@after('apply_link')
def create_task_macplist(self):
	"""
	Create a :py:class:`waflib.Tools.c_osx.macplist` instance.
	"""
	if  self.env['MACAPP'] or getattr(self, 'mac_app', False):
		# check if the user specified a plist before using our template
		if not getattr(self, 'mac_plist', False):
			self.mac_plist = app_info

		plisttask = self.create_task('macplist', self.link_task.outputs)

		out = self.link_task.outputs[0]
		self.mac_plist = self.mac_plist % (out.name)

		name = bundle_name_for_output(out)
		dir = self.create_bundle_dirs(name, out)

		n1 = dir.find_or_declare(['Contents', 'Info.plist'])

		plisttask.set_outputs([n1])
		plisttask.mac_plist = self.mac_plist
		plisttask.install_path = os.path.join(self.install_path, name, 'Contents')
		self.plisttask = plisttask

@feature('cshlib', 'cxxshlib')
@before('apply_link', 'propagate_uselib_vars')
def apply_bundle(self):
	"""
	To make a bundled shared library (a ``.bundle``), set the *mac_bundle* attribute::

		def build(bld):
			bld.shlib(source='a.c', target='foo', mac_bundle = True)

	To force *all* executables to be transformed into bundles::

		def build(bld):
			bld.env.MACBUNDLE = True
			bld.shlib(source='a.c', target='foo')
	"""
	if self.env['MACBUNDLE'] or getattr(self, 'mac_bundle', False):
		self.env['LINKFLAGS_cshlib'] = self.env['LINKFLAGS_cxxshlib'] = [] # disable the '-dynamiclib' flag
		self.env['cshlib_PATTERN'] = self.env['cxxshlib_PATTERN'] = self.env['macbundle_PATTERN']
		use = self.use = self.to_list(getattr(self, 'use', []))
		if not 'MACBUNDLE' in use:
			use.append('MACBUNDLE')

app_dirs = ['Contents', 'Contents/MacOS', 'Contents/Resources']

class macapp(Task.Task):
	"""
	Create mac applications
	"""
	color = 'PINK'
	def run(self):
		shutil.copy2(self.inputs[0].srcpath(), self.outputs[0].abspath())

class macplist(Task.Task):
	"""
	Create plist files
	"""
	color = 'PINK'
	ext_in = ['.bin']
	def run(self):
		self.outputs[0].write(self.mac_plist)

