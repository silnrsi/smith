#! /usr/bin/env python
# Avalanche Studios 2009-2011
# Thomas Nagy 2011

"""
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. The name of the author may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

# not ready yet, some refactoring is needed

import uuid # requires python 2.5
from waflib.Build import BuildContext
from waflib import Utils, TaskGen, Logs


BIN_GUID_PREFIX = Utils.md5('BIN').hexdigest()[:8].upper()
LIB_GUID_PREFIX = Utils.md5('LIB').hexdigest()[:8].upper()
SPU_GUID_PREFIX = Utils.md5('SPU').hexdigest()[:8].upper()
SAR_GUID_PREFIX = Utils.md5('SAR').hexdigest()[:8].upper()
EXT_GUID_PREFIX = Utils.md5('EXT').hexdigest()[:8].upper()
FRG_GUID_PREFIX = Utils.md5('FRG').hexdigest()[:8].upper()
SHA_GUID_PREFIX = Utils.md5('SHA').hexdigest()[:8].upper()

VS_GUID_VCPROJ         = "8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942"
VS_GUID_SOLUTIONFOLDER = "2150E333-8FDC-42A3-9474-1A3956D46DE8"

HEADERS_GLOB = '**/*.h|*.hpp|*.H|*.inl'

PROJECT_TEMPLATE = '''<?xml version="1.0" encoding="Windows-1252"?>
<Project
	DefaultTargets="Build"
	ToolsVersion="4.0"
	xmlns="http://schemas.microsoft.com/developer/msbuild/2003"
	>

	<ItemGroup Label="ProjectConfigurations">
%(projectconfigurations)s
	</ItemGroup>

	<PropertyGroup Label="Globals">
		<ProjectGuid>{%(guid)s}</ProjectGuid>
		<Keyword>MakeFileProj</Keyword>
	</PropertyGroup>
	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />

%(propertygroups_pre)s

	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
	<ImportGroup Label="ExtensionSettings">
	</ImportGroup>

%(propertysheets)s

%(propertygroups_post)s

%(itemdefinitions)s

	<ItemGroup>
%(sources)s
	</ItemGroup>
	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
	<ImportGroup Label="ExtensionTargets">
	</ImportGroup>
</Project>
'''

PROJECTCONFIGURATION_TEMPLATE = '''
		<ProjectConfiguration Include="%(name)s|%(pname)s">
			<Configuration>%(name)s</Configuration>
			<Platform>%(pname)s</Platform>
		</ProjectConfiguration>
'''

PROPERTYGROUP_PRE_TEMPLATE = '''
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(pname)s'" Label="Configuration">
		<ConfigurationType>Makefile</ConfigurationType>
		<OutDir>%(output_dir)s</OutDir>
	</PropertyGroup>
'''

PROPERTYSHEET_TEMPLATE = '''
	<ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(pname)s'">
		<Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
	</ImportGroup>
'''

PROPERTYGROUP_POST_TEMPLATE = '''
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(pname)s'">
		<NMakeBuildCommandLine>%(build_command)s</NMakeBuildCommandLine>
		<NMakeReBuildCommandLine>%(rebuild_command)s</NMakeReBuildCommandLine>
		<NMakeOutput>%(output_dir)s%(output_file)s</NMakeOutput>
		<NMakeCleanCommandLine>%(clean_command)s</NMakeCleanCommandLine>
		<NMakePreprocessorDefinitions>%(pre_defines)s;$(NMakePreprocessorDefinitions)</NMakePreprocessorDefinitions>
	</PropertyGroup>
'''

PROPERTYGROUP_POST_TEMPLATE_XENON = '''
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(pname)s'">
		<NMakeBuildCommandLine>%(build_command)s</NMakeBuildCommandLine>
		<NMakeReBuildCommandLine>%(rebuild_command)s</NMakeReBuildCommandLine>
		<NMakeOutput>%(output_dir)s%(output_file)s</NMakeOutput>
		<NMakeCleanCommandLine>%(clean_command)s</NMakeCleanCommandLine>
		<NMakePreprocessorDefinitions>%(pre_defines)s;$(NMakePreprocessorDefinitions)</NMakePreprocessorDefinitions>
		<RemoteRoot>%(deploy_dir)s</RemoteRoot>
	</PropertyGroup>
'''

ITEMDEFINITION_TEMPLATE_XENON = '''
	<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(pname)s'">
		<Deploy>
			<DeploymentType>CopyToHardDrive</DeploymentType>
		</Deploy>
	</ItemDefinitionGroup>
'''

FILTER_TEMPLATE = '''<?xml version="1.0" encoding="Windows-1252"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
%s
</Project>
'''

JOIN_SEPARATOR = { "configurations" : "\n",
                   "include_search_path" : ";",
                   "include_dirs" : "@",}


class msvs_generator(BuildContext):
	cmd = 'msvs'
	fun = 'build'

	def execute(self):
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])
		self.create_files()

	def create_files(self):
		"""
		Two parts here: projects and solution files
		"""

		self.platform = getattr(self, 'platform', None) or self.env.PLATFORM or 'Win32'

		self.create_projects()
		errs = getattr(self, 'msvs_project_errors', [])
		if not errs:
			Logs.warn('VS project generation finished without errors')
		else:
			Logs.warn('--------------------PROJECT ERRORS ----------------------')
			Logs.warn('VS project generation finished with %d errors!' % len(errs))
			Logs.warn('---------------------------------------------------------')

		self.create_solution()
		errs = getattr(self, 'msvs_solution_errors')
		if errs:
			Logs.warn('----------------- SOLUTION ERROR -----------------------')
			Logs.warn(' No target with feature "msvs_solution" was found.')
			Logs.warn(' No solution file will be generated')
			Logs.warn('--------------------------------------------------------')

	def create_projects(self):
		"""
		Iterate over all task generators to create the project files
		"""
		self.vcxprojs = []
		for g in self.groups:
			for tg in g:
				if self.accept(tg):
					self.vcxprojs.append(self.do_one_project(tg))

	def create_solution(self):
		"""
		Create the top-level solutions file
		"""
		if getattr(self, 'solution_name', None):
			Logs.warn('Creating: %s' % self.solution_name)
			self.do_solution()
		else:
			self.msvs_solution_errors = True

	################## helper methods that may need to be overridden in subclasses

	def make_guid(self, x, prefix = None):
		d = Utils.md5(str(x)).hexdigest().upper()
		if prefix:
			d = '%s%s' % (prefix, d[8:])
		gid = uuid.UUID(d, version = 4)
		return str(gid).upper()

	def get_guid_prefix(self, tg):
		f = tg.to_list(getattr(tg, 'features', []))
		if 'cprogram' in f or 'cxxprogram' in f:
			return BIN_GUID_PREFIX
		if 'cstlib' in f or 'cxxstlib' in f:
			return LIB_GUID_PREFIX
		return ''

	def accept(self, tg):
		"""
		Return True if a task generator can be used as a msvs project,
		reject the ones that are not task generators or have the attribute "no_msvs"
		the ones that have no name are added to the list "msvs_project_errors"
		"""
		if not isinstance(tg, TaskGen.task_gen):
			return False

		if getattr(tg, 'no_msvs', None):
			# no error
			return False

		if not tg.name:
			try:
				e = self.msvs_project_errors
			except:
				e = self.msvs_project_errors = []
			Logs.error('discarding %r' % tg)
			e.append(tg)
			return False

		try:
			p = self.msvs_processed
		except:
			p = self.msvs_processed = {}
		if id(tg) in p:
			return
		p[id(tg)] = tg
		return True


	#############################################################################################################
	# TODO

	def do_solution(self):
		pass
		#mssolution.GenerateMSVSSolution(self.solution_name, platform, self.vcxprojs)

	def do_one_project(self, tg):
		platform = self.platform
		project = tg.name
		source_files = Utils.to_list(getattr(tg, 'source', []))
		include_dirs = Utils.to_list(getattr(tg, 'includes', [])) + Utils.to_list(getattr(tg, 'export_dirs', []))
		guid = self.get_guid_prefix(tg)

		include_files = []
		for x in include_dirs:
			d = tg.path.find_node(x)
			if d:
				lst = [y.path_from(tg.path) for y in d.ant_glob(HEADERS_GLOB, flat=False)]
				include_files.extend(lst)

		values = {
				'sources'       : source_files + include_files,
				'abs_path'      : tg.path.abspath(),
				'platform'      : self.platform,
				'name'          : project,
				'flags_debug'   : '',
				'flags_release' : '',
				'flags_final'   : '',
				'include_dirs'  : ''
				}
		values['guid'] = self.make_guid(values, prefix = guid)

		out = self.bldnode.make_node('depprojs')
		out.mkdir()
		proj_file   = out.make_node('%s_%s.vcxproj' % (project, platform))
		filter_file = out.make_node('%s_%s.vcxproj.filters' % (project, platform))

		tg.post()
		config = self.get_project_config(values, tg)
		(proj_str, filter_str) = self.create_project_string(values, config)

		Logs.warn('Creating %r' % proj_file)
		proj_file.write(proj_str)
		filter_file.write(filter_str)

		return proj_file.abspath()

	def get_project_name(self):
		if self.platform == 'Xenon':
			return 'Xbox 360'
		return 'Win32'

	def get_project_config(self, values, tg):
		# getLibProjectConfigs(values)
		link = getattr(tg, 'link_task', None)
		return [{
				'pname': self.get_project_name(),
				'name': self.platform,
				'build_command' : 'waf configure build',
				'rebuild_command' : 'waf configure clean build',
				'clean_command' : 'waf clean',
				'output_dir' : link and link.outputs[0].parent.abspath() or '',
				'output_file': link and link.outputs[0].abspath() or '',
				'pre_defines': Utils.subst_vars('${DEFINES_ST:DEFINES}', tg.env)
				}]

	def create_project_string(self, values, configurations):
		projectconfiguration_str	= ''
		propertygroup_pre_str		= ''
		propertysheet_str			= ''
		propertygroup_post_str		= ''
		itemdefinition_str			= ''

		for cfg in configurations:
			projectconfiguration_str += PROJECTCONFIGURATION_TEMPLATE % cfg
			propertygroup_pre_str    += PROPERTYGROUP_PRE_TEMPLATE % cfg
			propertysheet_str        += PROPERTYSHEET_TEMPLATE % cfg
			propertygroup_post_str   += PROPERTYGROUP_POST_TEMPLATE % cfg
			#if platform == 'Xenon':
			#	propertygroup_post_str		+= propertygroup_post_templ_xenon % cc
			#	if values['guid'][0:8] == BIN_GUID_PREFIX:
			#		itemdefinition_str			+= itemdefinition_templ_xenon % cc
			#else:
			#	propertygroup_post_str		+= propertygroup_post_templ % cc

		(file_str, filter_str) = self.gen_tree_string(values.get('sources', []), values['abs_path'])

		project_str = PROJECT_TEMPLATE % { 'name'                  : values['name'],
										   'guid'                  : values['guid'],
										   'pname'                 : self.get_project_name(),
										   'projectconfigurations' : projectconfiguration_str,
										   'propertygroups_pre'    : propertygroup_pre_str,
										   'propertysheets'        : propertysheet_str,
										   'propertygroups_post'   : propertygroup_post_str,
										   'itemdefinitions'       : itemdefinition_str,
										   'sources'		       : file_str }
		return (project_str, FILTER_TEMPLATE % filter_str)

	def gen_tree_string(self, *k, **kw):
		return ('', '')

