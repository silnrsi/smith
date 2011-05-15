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

PROJECT_TEMPLATE = '''<?xml version="1.0" encoding="Windows-1252"?>
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

SOLUTION_TEMPLATE = '''Microsoft Visual Studio Solution File, Format Version 11.00
# Visual Studio 2010
%(projects)s
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
%(pre_solution)s
    EndGlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution
%(post_solution)s
    EndGlobalSection
    GlobalSection(SolutionProperties) = preSolution
        HideSolutionNode = FALSE
    EndGlobalSection
    GlobalSection(NestedProjects) = preSolution
%(folder_nesting)s
    EndGlobalSection
EndGlobal
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
		errs = getattr(self, 'msvs_solution_errors', None)
		if errs:
			Logs.warn('----------------- SOLUTION ERROR -----------------------')
			Logs.warn(' Skipping the solution file (no ctx.solution_name given)')
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
		self.GenerateMSVSSolution(self.solution_name, self.platform, self.vcxprojs)

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
		template1 = compile_template(PROJECT_TEMPLATE)
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

		return proj_file

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

	def GenerateMSVSSolution(self, outfile, platform, project_files):
		projects_str		= ''
		pre_solution_str	= ''
		post_solution_str   = ''
		folder_nesting_str  = ''

		project_files = [x.abspath() for x in project_files]

		for project_path in project_files:
			if not project_path.endswith('.vcxproj'):
				print 'Error: %(outfile)s is said to require the file %(project_path)s, which does not end with .vcxproj' % globals()
				exit(1)

			project_path = project_path.strip()
			if os.path.exists(project_path):
				name = os.path.basename(project_path).split('_')[0]
				project = VSProject(name, project_path)
			else:
				print 'Error: file "%s" do not exist, ignoring!' % project_path

		CONFIGURATIONS = ['Release']

		for project in projectsTree():
			projects_str += project.slnStr()
			folder_nesting_str += project.slnNestStr()

			if project.__class__ == VSProject:
				for confs in CONFIGURATIONS:
					post_solution_str += emitProjectConfigString(project.guid, platform, confs, project.type.guid_prefix == BIN_GUID_PREFIX)

		pre_template = "\t\t%s|Xbox 360 = %s|Xbox 360\n" if platform == 'Xenon' else "\t\t%s|Win32 = %s|Win32\n"

		for conf in CONFIGURATIONS:
			for type in BUILDTYPES:
				tmp = '%s%s' % (type, conf)
				pre_solution_str += pre_template % (tmp, tmp)

		f = open(outfile, "w")
		f.write( SOLUTION_TEMPLATE % { 'projects'	   : projects_str,
									   'pre_solution'   : pre_solution_str,
									   'post_solution'  : post_solution_str,
									   'folder_nesting' : folder_nesting_str } )
		f.close()

def projectsTree():
    for folder_name in VSProjectType.by_folder_name.keys():
        for node in VSProjectType.by_folder_name[folder_name].selfAndDescendants():
            yield node


DEFAULT_FOLDER_CONFIG = """
[folders]
"""


class CaseSensitiveConfigParser(ConfigParser.ConfigParser):
    def optionxform(self, optionstr):
        return str(optionstr)


def readFolderConfig():
    config_parser = CaseSensitiveConfigParser()
    if os.path.exists("config\\msvs.config"):
        config_parser.read("config\\msvs.config")
    else:
        config_parser.readfp(StringIO.StringIO(DEFAULT_FOLDER_CONFIG), '<default configuration>')
    return config_parser


folder_config = readFolderConfig()

unknown_project_type = None


class VSSolutionTreeElement:
    def __init__(self):
        self.guid = genRandomUuid()
        self.parent_vs_element = None

    def selfAndDescendants(self):
        yield self
        for d in self.descendants():
            yield d

    def descendants(self):
        for c in self.children():
            yield c
            for d in c.descendants():
                yield d

    def children(self): # To be overridden
        if False:
            yield None  # Anyone know of a cleaner way to make a generator
                        # function that will always return an empty iterator?

    def slnStr(self):
        if self.__class__ == VSProject:
            path = os.path.join(os.getcwd(), self.path)
        else:
            path = self.name
        sln_str = 'Project("{%s}") = "%s", "%s", "{%s}"\nEndProject\n' % (self.vs_project_type_guid, self.name, path, self.guid)

        return sln_str

    def slnNestStr(self):
        if self.parent_vs_element and not self.guid[0:8] == BIN_GUID_PREFIX:
            sln_nest_str = '\t\t{%s} = {%s}\n' % (self.guid, self.parent_vs_element.guid)
        else:
            sln_nest_str = ''

        return sln_nest_str


class VSProjectNameGroup(VSSolutionTreeElement):
    by_type_and_folder_name = {}

    def __init__(self, name, project_type = None):
        VSSolutionTreeElement.__init__(self)

        self.vs_project_type_guid    = VS_GUID_SOLUTIONFOLDER
        self.path = self.name        = name

        self.parent_vs_element = self.project_type = project_type

        self.projects = []

    def children(self):
        for project in self.projects:
            yield project


class VSProjectType(VSSolutionTreeElement):
    by_guid_prefix = {}
    by_folder_name = {}

    def __init__(self, folder_name, guid_prefix = None):
        VSSolutionTreeElement.__init__(self)

        self.vs_project_type_guid    = VS_GUID_SOLUTIONFOLDER
        self.guid_prefix             = guid_prefix

        self.path = self.name = self.folder_name = folder_name

        VSProjectType.by_folder_name[folder_name] = self

        if guid_prefix != None:
            VSProjectType.by_guid_prefix[guid_prefix] = self

        self.name_groups = []
        self.projects = []

    def children(self):
        for name_group in self.name_groups:
            yield name_group
        for project in self.projects:
            yield project


class VSProject(VSSolutionTreeElement):
    by_type = {}

    def __init__(self, name, path, parent_folder = None):
        VSSolutionTreeElement.__init__(self)

        global unknown_project_type

        self.vs_project_type_guid = VS_GUID_VCPROJ
        self.name                 = name
        self.path                 = path
        self.guid                 = getGuid(self.path)

        project_types = { BIN_GUID_PREFIX : 'Binaries',
                          LIB_GUID_PREFIX : 'Project libraries',
                          SPU_GUID_PREFIX : 'SPU',
                          SAR_GUID_PREFIX : 'Site libraries',
                          EXT_GUID_PREFIX : 'External libraries',
                          FRG_GUID_PREFIX : 'Fragments',
                          SHA_GUID_PREFIX : 'Shader libraries' }

        self.type = None

        for project_type in project_types.keys():
            if self.guid[:8] == project_type:
                if not VSProjectType.by_guid_prefix.has_key(project_type):
                    VSProjectType(project_types[project_type], project_type)
                self.type = VSProjectType.by_guid_prefix[project_type]

        if not self.type:
            if not unknown_project_type:
                unknown_project_type = VSProjectType('Unknown project type')
            self.type = unknown_project_type

        if not VSProject.by_type.has_key(self.type):
            VSProject.by_type[self.type] = []
        VSProject.by_type[self.type].append(self)

        patterns = folder_config.options('folders')
        self.subfolder = None
        for pattern in patterns:
            subfolder_name = folder_config.get('folders', pattern)
            if fnmatch.fnmatchcase(self.name, pattern):
                if not VSProjectNameGroup.by_type_and_folder_name.has_key(self.type):
                    VSProjectNameGroup.by_type_and_folder_name[self.type] = {}
                if not VSProjectNameGroup.by_type_and_folder_name[self.type].has_key(subfolder_name):
                    name_group = VSProjectNameGroup(subfolder_name, self.type)
                    VSProjectNameGroup.by_type_and_folder_name[self.type][subfolder_name] = name_group
                    self.type.name_groups.append(name_group)
                self.parent_vs_element = self.subfolder = VSProjectNameGroup.by_type_and_folder_name[self.type][subfolder_name]
                VSProjectNameGroup.by_type_and_folder_name[self.type][subfolder_name].projects.append(self)
                break

        if not self.subfolder:
            self.parent_vs_element = self.type
            self.type.projects.append(self)


def projectsTree():
    for folder_name in VSProjectType.by_folder_name.keys():
        for node in VSProjectType.by_folder_name[folder_name].selfAndDescendants():
            yield node


#---------------------------------------------------------------------------

#######################################################################
# emitProjectConfigString - emits a configuration string used i Visual Studio Solution files
#
# PARAMETERS:
# guid = the guid of the project to emit string for.
# conf = configuration to write conf-string for.
# build = boolean telling if this project should be built when building entire solution.
#

proj_conf_template  = "\t\t{%(guid)s}.%(config)s.ActiveCfg = %(config)s\n"
build_conf_template = "\t\t{%(guid)s}.%(config)s.Build.0   = %(config)s\n"

def emitProjectConfigString(guid, platform, conf, build):
    ret = ''
    plat_str = 'Xbox 360' if platform == 'Xenon' else 'Win32'

    for type in BUILDTYPES:
        values = { 'guid' : guid,
                   'config' : '%s|%s' % (type + conf, plat_str) }

        ret += proj_conf_template % values

        if build:
            ret += build_conf_template % values

    return ret

#---------------------------------------------------------------------------





