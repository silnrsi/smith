#! /usr/bin/env python
# encoding: utf-8
# Eclipse CDT 5.0 generator for Waf
# Richard Quirk 2009-1011 (New BSD License)
# Thomas Nagy 2011 (ported to Waf 1.6)

"""
Usage:

def options(opt):
	opt.load('eclipse')

$ waf configure eclipse
"""

import sys, os
from waflib import Utils, Logs, Context, Options, Build, TaskGen
from xml.dom.minidom import Document

oe_cdt = 'org.eclipse.cdt'
cdt_mk = oe_cdt + '.make.core'
cdt_core = oe_cdt + '.core'
cdt_bld = oe_cdt + '.build.core'

class eclipse(Build.BuildContext):
	cmd = 'eclipse'
	fun = 'build'

	def execute(self):
		"""
		Entry point
		"""
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])

		appname = getattr(Context.g_module, Context.APPNAME, os.path.basename(self.srcnode.abspath()))
		self.create_cproject(appname, pythonpath=self.env['ECLIPSE_PYTHON_PATH'])

	def create_cproject(self, appname, workspace_includes=[], pythonpath=[]):
		"""
		Create the Eclipse CDT .project and .cproject files
		@param appname The name that will appear in the Project Explorer
		@param build The BuildContext object to extract includes from
		@param workspace_includes Optional project includes to prevent
			  "Unresolved Inclusion" errors in the Eclipse editor
		@param pythonpath Optional project specific python paths
		"""
		source_dirs = []
		cpppath = self.env['CPPPATH']
		Logs.warn('Generating Eclipse CDT project files')

		for g in self.groups:
			for tg in g:
				if not isinstance(tg, TaskGen.task_gen):
					continue

				tg.post()
				if not getattr(tg, 'link_task', None):
					continue

				l = Utils.to_list(getattr(tg, "includes", ''))
				sources = Utils.to_list(getattr(tg, 'source', ''))
				features = Utils.to_list(getattr(tg, 'features', ''))

				is_cc = 'c' in features or 'cxx' in features

				bldpath = tg.path.bldpath()

				base = os.path.normpath(os.path.join(self.bldnode.name, tg.path.srcpath()))

				if is_cc:
					sources_dirs = set([src.parent for src in tg.to_nodes(sources)])

				incnodes = tg.to_incnodes(tg.to_list(getattr(tg, 'includes', [])) + tg.env['INCLUDES'])
				for p in incnodes:
					path = p.path_from(self.srcnode)
					workspace_includes.append(path)

					if is_cc and path not in source_dirs:
						source_dirs.append(path)

		project = _create_project(sys.executable, appname)
		self.srcnode.make_node('.project').write(project)

		waf = os.path.abspath(sys.argv[0])
		project = _create_cproject(sys.executable, waf, appname, workspace_includes, cpppath, source_dirs)
		self.srcnode.make_node('.cproject').write(project)

		project = _create_pydevproject(appname, sys.path, pythonpath)
		self.srcnode.make_node('.pydevproject').write(project)

def add(doc, parent, tag, value = None):
	el = doc.createElement(tag)
	if (value):
		if type(value) == type(str()):
			el.appendChild(doc.createTextNode(value))
		elif type(value) == type(dict()):
			setAttributes(el, value)
	parent.appendChild(el)
	return el

def addDictionary(doc, parent, k, v):
	dictionary = add(doc, parent, 'dictionary')
	add(doc, dictionary, 'key', k)
	add(doc, dictionary, 'key', v)
	return dictionary

def setAttributes(node, attrs):
	for k, v in attrs.items():
		node.setAttribute(k, v)

def _create_project(executable, appname):
	doc = Document()
	projectDescription = doc.createElement('projectDescription')
	add(doc, projectDescription, 'name', appname)
	add(doc, projectDescription, 'comment')
	add(doc, projectDescription, 'projects')
	buildSpec = add(doc, projectDescription, 'buildSpec')
	buildCommand = add(doc, buildSpec, 'buildCommand')
	add(doc, buildCommand, 'name', oe_cdt + '.managedbuilder.core.genmakebuilder')
	add(doc, buildCommand, 'triggers', 'clean,full,incremental,')
	arguments = add(doc, buildCommand, 'arguments')
	# the default make-style targets are overwritten by the .cproject values
	dictionaries = {
			cdt_mk + '.contents': cdt_mk + '.activeConfigSettings',
			cdt_mk + '.enableAutoBuild': 'false',
			cdt_mk + '.enableCleanBuild': 'true',
			cdt_mk + '.enableFullBuild': 'true',
			}
	for k, v in dictionaries.items():
		addDictionary(doc, arguments, k, v)

	natures = add(doc, projectDescription, 'natures')
	nature_list = """
		core.ccnature
		managedbuilder.core.ScannerConfigNature
		managedbuilder.core.managedBuildNature
		core.cnature
	""".split()
	for n in nature_list:
		add(doc, natures, 'nature', oe_cdt + '.' + n)

	add(doc, natures, 'nature', 'org.python.pydev.pythonNature')

	doc.appendChild(projectDescription)
	return doc.toxml()

def addTarget(doc, buildTargets, executable, name, buildTarget, runAllBuilders=True):
	target = add(doc, buildTargets, 'target',
					{'name': name,
					 'path': '',
					 'targetID': oe_cdt + '.build.MakeTargetBuilder'})
	add(doc, target, 'buildCommand', executable)
	add(doc, target, 'buildArguments', None)
	add(doc, target, 'buildTarget', buildTarget)
	add(doc, target, 'stopOnError', 'true')
	add(doc, target, 'useDefaultCommand', 'false')
	add(doc, target, 'runAllBuilders', str(runAllBuilders).lower())

def _create_cproject(executable, waf, appname, workspace_includes, cpppath, source_dirs=[]):
	doc = Document()
	doc.appendChild(doc.createProcessingInstruction('fileVersion', '4.0.0'))
	cconf_id = cdt_core + '.default.config.1'
	cproject = doc.createElement('cproject')
	storageModule = add(doc, cproject, 'storageModule',
			{'moduleId': cdt_core + '.settings'})
	cconf = add(doc, storageModule, 'cconfiguration', {'id':cconf_id})

	storageModule = add(doc, cconf, 'storageModule',
			{'buildSystemId': oe_cdt + '.managedbuilder.core.configurationDataProvider',
			 'id': cconf_id,
			 'moduleId': cdt_core + '.settings',
			 'name': 'Default'})

	add(doc, storageModule, 'externalSettings')

	extensions = add(doc, storageModule, 'extensions')
	extension_list = """
		VCErrorParser
		MakeErrorParser
		GCCErrorParser
		GASErrorParser
		GLDErrorParser
	""".split()
	ext = add(doc, extensions, 'extension',
				{'id': cdt_core + '.ELF', 'point':cdt_core + '.BinaryParser'})
	for e in extension_list:
		ext = add(doc, extensions, 'extension',
				{'id': cdt_core + '.' + e, 'point':cdt_core + '.ErrorParser'})

	storageModule = add(doc, cconf, 'storageModule',
			{'moduleId': 'cdtBuildSystem', 'version': '4.0.0'})
	config = add(doc, storageModule, 'configuration',
				{'artifactName': appname,
				 'id': cconf_id,
				 'name': 'Default',
				 'parent': cdt_bld + '.prefbase.cfg'})
	folderInfo = add(doc, config, 'folderInfo',
						{'id': cconf_id+'.', 'name': '/', 'resourcePath': ''})

	toolChain = add(doc, folderInfo, 'toolChain',
			{'id': cdt_bld + '.prefbase.toolchain.1',
			 'name': 'No ToolChain',
			 'resourceTypeBasedDiscovery': 'false',
			 'superClass': cdt_bld + '.prefbase.toolchain'})

	targetPlatform = add(doc, toolChain, 'targetPlatform',
			{ 'binaryParser': 'org.eclipse.cdt.core.ELF',
			  'id': cdt_bld + '.prefbase.toolchain.1', 'name': ''})

	waf_build = '"%s" build'%(waf)
	waf_clean = '"%s" clean'%(waf)
	builder = add(doc, toolChain, 'builder',
					{'autoBuildTarget': waf_build,
					 'command': executable,
					 'enableAutoBuild': 'false',
					 'cleanBuildTarget': waf_clean,
					 'enableIncrementalBuild': 'true',
					 'id': cdt_bld + '.settings.default.builder.1',
					 'incrementalBuildTarget': waf_build,
					 'managedBuildOn': 'false',
					 'name': 'Gnu Make Builder',
					 'superClass': cdt_bld + '.settings.default.builder'})

	for tool_name in ("Assembly", "GNU C++", "GNU C"):
		tool = add(doc, toolChain, 'tool',
				{'id': cdt_bld + '.settings.holder.1',
				 'name': tool_name,
				 'superClass': cdt_bld + '.settings.holder'})
		if cpppath or workspace_includes:
			incpaths = cdt_bld + '.settings.holder.incpaths'
			option = add(doc, tool, 'option',
					{'id': incpaths+'.1',
					 'name': 'Include Paths',
					 'superClass': incpaths,
					 'valueType': 'includePath'})
			for i in workspace_includes:
				add(doc, option, 'listOptionValue',
							{'builtIn': 'false',
							'value': '"${workspace_loc:/%s/%s}"'%(appname, i)})
			for i in cpppath:
				add(doc, option, 'listOptionValue',
							{'builtIn': 'false',
							'value': '"%s"'%(i)})
	if source_dirs:
		sourceEntries = add(doc, config, 'sourceEntries')
		for i in source_dirs:
			 add(doc, sourceEntries, 'entry',
						{'excluding': i,
						'flags': 'VALUE_WORKSPACE_PATH|RESOLVED',
						'kind': 'sourcePath',
						'name': ''})
			 add(doc, sourceEntries, 'entry',
						{
						'flags': 'VALUE_WORKSPACE_PATH|RESOLVED',
						'kind': 'sourcePath',
						'name': i})

	storageModule = add(doc, cconf, 'storageModule',
						{'moduleId': cdt_mk + '.buildtargets'})
	buildTargets = add(doc, storageModule, 'buildTargets')
	def addTargetWrap(name, runAll):
		return addTarget(doc, buildTargets, executable, name,
							'"%s" %s'%(waf, name), runAll)
	addTargetWrap('configure', True)
	addTargetWrap('dist', False)
	addTargetWrap('install', False)
	addTargetWrap('check', False)

	storageModule = add(doc, cproject, 'storageModule',
						{'moduleId': 'cdtBuildSystem',
						 'version': '4.0.0'})

	project = add(doc, storageModule, 'project',
				{'id': '%s.null.1'%appname, 'name': appname})

	doc.appendChild(cproject)
	return doc.toxml()

def _create_pydevproject(appname, system_path, user_path):
	# create a pydevproject file
	doc = Document()
	doc.appendChild(doc.createProcessingInstruction('eclipse-pydev', 'version="1.0"'))
	pydevproject = doc.createElement('pydev_project')
	prop = add(doc, pydevproject,
				   'pydev_property',
				   'python %d.%d'%(sys.version_info[0], sys.version_info[1]))
	prop.setAttribute('name', 'org.python.pydev.PYTHON_PROJECT_VERSION')
	prop = add(doc, pydevproject, 'pydev_property', 'Default')
	prop.setAttribute('name', 'org.python.pydev.PYTHON_PROJECT_INTERPRETER')
	# add waf's paths
	wafadmin = [p for p in system_path if p.find('wafadmin') != -1]
	if wafadmin:
		prop = add(doc, pydevproject, 'pydev_pathproperty',
				{'name':'org.python.pydev.PROJECT_EXTERNAL_SOURCE_PATH'})
		for i in wafadmin:
			add(doc, prop, 'path', i)
	if user_path:
		prop = add(doc, pydevproject, 'pydev_pathproperty',
				{'name':'org.python.pydev.PROJECT_SOURCE_PATH'})
		for i in user_path:
			add(doc, prop, 'path', '/'+appname+'/'+i)

	doc.appendChild(pydevproject)
	return doc.toxml()


