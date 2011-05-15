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

import os, string

import re
import uuid # requires python 2.5
from waflib.Build import BuildContext
from waflib import Utils, TaskGen, Logs, Task

BIN_GUID_PREFIX = Utils.md5('BIN').hexdigest()[:8].upper()
LIB_GUID_PREFIX = Utils.md5('LIB').hexdigest()[:8].upper()
SPU_GUID_PREFIX = Utils.md5('SPU').hexdigest()[:8].upper()
SAR_GUID_PREFIX = Utils.md5('SAR').hexdigest()[:8].upper()
EXT_GUID_PREFIX = Utils.md5('EXT').hexdigest()[:8].upper()
FRG_GUID_PREFIX = Utils.md5('FRG').hexdigest()[:8].upper()
SHA_GUID_PREFIX = Utils.md5('SHA').hexdigest()[:8].upper()

VS_GUID_VCPROJ         = "8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942"
VS_GUID_SOLUTIONFOLDER = "2150E333-8FDC-42A3-9474-1A3956D46DE8"

HEADERS_GLOB = '**/(*.h|*.hpp|*.H|*.inl)'

TEMPLATE = '''<?xml version="1.0" encoding="Windows-1252"?>
<Project DefaultTargets="Build" ToolsVersion="4.0"
	xmlns="http://schemas.microsoft.com/developer/msbuild/2003">

	<ItemGroup Label="ProjectConfigurations">
		${for cfg in project['configs']}
		<ProjectConfiguration Include="${cfg['name']}|${cfg['pname']}">
			<Configuration>${cfg['name']}</Configuration>
			<Platform>${cfg['pname']}</Platform>
		</ProjectConfiguration>
		${endfor}
	</ItemGroup>

	<PropertyGroup Label="Globals">
		<ProjectGuid>{${project['guid']}}</ProjectGuid>
		<Keyword>MakeFileProj</Keyword>
	</PropertyGroup>
	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />

	${for cfg in project['configs']}
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='${cfg['name']}|${cfg['pname']}'" Label="Configuration">
		<ConfigurationType>Makefile</ConfigurationType>
		<OutDir>${cfg['output_dir']}</OutDir>
	</PropertyGroup>
	${endfor}

	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
	<ImportGroup Label="ExtensionSettings">
	</ImportGroup>

	${for cfg in project['configs']}
	<ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='${cfg['name']}|${cfg['pname']}'">
		<Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
	</ImportGroup>
	${endfor}

	${for cfg in project['configs']}
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='${cfg['name']}|${cfg['pname']}'">
		<NMakeBuildCommandLine>${cfg['build_command']}</NMakeBuildCommandLine>
		<NMakeReBuildCommandLine>${cfg['rebuild_command']}</NMakeReBuildCommandLine>
		<NMakeOutput>${cfg['output_file']}</NMakeOutput>
		<NMakeCleanCommandLine>${cfg['rebuild_command']}</NMakeCleanCommandLine>
		<NMakePreprocessorDefinitions>${cfg['pre_defines']};$(NMakePreprocessorDefinitions)</NMakePreprocessorDefinitions>
		${if 'deploy_dir' in cfg}
		<RemoteRoot>${cfg['deploy_dir']}</RemoteRoot>
		${endif}
	</PropertyGroup>
	${endfor}

	${for cfg in project['configs']}
		${if False}
	<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='${cfg['name']}|${cfg['pname']}'">
		<Deploy>
			<DeploymentType>CopyToHardDrive</DeploymentType>
		</Deploy>
	</ItemDefinitionGroup>
		${endif}
	${endfor}

	<ItemGroup>
		${for x in project['sources']}<${project['ctx'].compile_key(x)} Include='${x.abspath()}' />
		${endfor}
	</ItemGroup>
	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
	<ImportGroup Label="ExtensionTargets">
	</ImportGroup>
</Project>
'''

FILTER_TEMPLATE = '''<?xml version="1.0" encoding="Windows-1252"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
	<ItemGroup>
		${for x in project['sources']}
			<${project['ctx'].compile_key(x)} Include="${x.abspath()}">
				<Filter>${x.parent.path_from(project['ctx'].srcnode)}</Filter>
			</${project['ctx'].compile_key(x)}>
		${endfor}
	</ItemGroup>
	<ItemGroup>
		${for d in project['dirs']}
			<Filter Include="${d.path_from(project['ctx'].srcnode)}">
				<UniqueIdentifier>${project['ctx'].make_guid(d.abspath())}</UniqueIdentifier>
			</Filter>
		${endfor}
	</ItemGroup>
</Project>
'''

COMPILE_TEMPLATE = '''def f(project):
	lst = []
	%s
	return ''.join(lst)
'''
reg_act = re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<code>[^}]*?)\})", re.M)
def compile_template(line):
	"""
	Compile a template expression into a python function (like jsps, but way shorter)
	"""
	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('subst'):
			extr.append(g('code'))
			return "<<|@|>>"
		return None

	line2 = reg_act.sub(repl, line)
	params = line2.split('<<|@|>>')
	assert(extr)


	indent = 0
	buf = []
	dvars = []
	app = buf.append

	def app(txt):
		buf.append(indent * '\t' + txt)

	for x in range(len(extr)):
		if params[x]:
			app("lst.append(%r)" % params[x])

		f = extr[x]
		if f.startswith('if') or f.startswith('for'):
			app(f + ':')
			indent += 1
		elif f.startswith('py:'):
			app(f.lstrip('py:'))
		elif f.startswith('endif') or f.startswith('endfor'):
			indent -= 1
		else:
			app('lst.append(%s)' % f)

	if extr:
		if params[-1]:
			app("lst.append(%r)" % params[-1])

	fun = COMPILE_TEMPLATE % "\n\t".join(buf)
	#print fun
	return Task.funex(fun)

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

	def do_solution(self):
		pass
		#mssolution.GenerateMSVSSolution(self.solution_name, platform, self.vcxprojs)

	def do_one_project(self, tg):
		platform = self.platform
		project = tg.name
		source_files = tg.to_nodes(getattr(tg, 'source', []))
		include_dirs = Utils.to_list(getattr(tg, 'includes', [])) + Utils.to_list(getattr(tg, 'export_dirs', []))
		guid = self.get_guid_prefix(tg)

		include_files = []
		for x in include_dirs:
			d = tg.path.find_node(x)
			if d:
				lst = [y for y in d.ant_glob(HEADERS_GLOB, flat=False)]
				include_files.extend(lst)

		# remove duplicates
		sources = list(set(source_files + include_files))
		sources.sort()

		values = {
				'sources'       : sources,
				'abs_path'      : tg.path.abspath(),
				'platform'      : self.platform,
				'name'          : project,
				'flags_debug'   : '',
				'flags_release' : '',
				'flags_final'   : '',
				'include_dirs'  : '',
				'ctx'           : self,
				}
		values['guid'] = self.make_guid(values, prefix = guid)

		out = self.bldnode.make_node('depprojs')
		out.mkdir()
		proj_file   = out.make_node('%s_%s.vcxproj' % (project, platform))
		filter_file = out.make_node('%s_%s.vcxproj.filters' % (project, platform))

		tg.post()

		values['configs'] = self.get_project_config(values, tg)

		# first write the project file
		Logs.warn('Creating %r' % proj_file)
		template1 = compile_template(TEMPLATE)
		proj_str = template1(values)
		proj_file.write(proj_str)

		# the filter needs a list of folders
		dirs = list(set([x.parent for x in sources]))
		dirs.sort()
		values['dirs'] = dirs

		# write the filter
		template2 = compile_template(FILTER_TEMPLATE)
		filter_str = template2(values)
		filter_file.write(filter_str)

		return proj_file.abspath()

	def compile_key(self, node):
		name = node.name
		if name.endswith('.cpp') or name.endswith('.c'):
			return 'ClCompile'
		return 'ClInclude'

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

