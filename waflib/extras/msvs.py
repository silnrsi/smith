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

"""
To add this tool to your project:
def options(conf):
	opt.load('msvs')

It can be a good idea to add the sync_exec tool too.

To generate solution files:
$ waf configure msvs

ASSUMPTIONS:
* a project can be either a directory or a target, vcxproj files are written only for targets that have source files
* each project is a vcxproj file, therefore the project guid needs only to be a hash of the absolute path

"""

import os, re
import uuid # requires python 2.5
from waflib.Build import BuildContext
from waflib import Utils, TaskGen, Logs, Task, Context

HEADERS_GLOB = '**/(*.h|*.hpp|*.H|*.inl)'

PROJECT_TEMPLATE = r'''<?xml version="1.0" encoding="Windows-1252"?>
<Project DefaultTargets="Build" ToolsVersion="4.0"
	xmlns="http://schemas.microsoft.com/developer/msbuild/2003">

	<ItemGroup Label="ProjectConfigurations">
		${for b in project.build_properties()}
		<ProjectConfiguration Include="${b.configuration}|${b.platform}">
			<Configuration>${b.configuration}</Configuration>
			<Platform>${b.platform}</Platform>
		</ProjectConfiguration>
		${endfor}
	</ItemGroup>

	<PropertyGroup Label="Globals">
		<ProjectGuid>{${project.guid}}</ProjectGuid>
		<Keyword>MakeFileProj</Keyword>
	</PropertyGroup>
	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />

	${for b in project.build_properties()}
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='${b.configuration}|${b.platform}'" Label="Configuration">
		<ConfigurationType>Makefile</ConfigurationType>
		<OutDir>${b.outdir}</OutDir>
	</PropertyGroup>
	${endfor}

	<Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
	<ImportGroup Label="ExtensionSettings">
	</ImportGroup>

	${for b in project.build_properties()}
	<ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='${b.configuration}|${b.platform}'">
		<Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
	</ImportGroup>
	${endfor}

	${for b in project.build_properties()}
	<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='${b.configuration}|${b.platform}'">
		<NMakeBuildCommandLine>${project.get_build_command(b)}</NMakeBuildCommandLine>
		<NMakeReBuildCommandLine>${project.get_rebuild_command(b)}</NMakeReBuildCommandLine>
		<NMakeCleanCommandLine>${project.get_clean_command(b)}</NMakeCleanCommandLine>
			${if hasattr(b, 'output_file')}
		<NMakeOutput>${b.output_file}</NMakeOutput>
			${endif}
		<NMakePreprocessorDefinitions>${b.pre_defines};$(NMakePreprocessorDefinitions)</NMakePreprocessorDefinitions>
		${if getattr(b, 'deploy_dir', None)}
		<RemoteRoot>${b.deploy_dir}</RemoteRoot>
		${endif}
	</PropertyGroup>
	${endfor}

	${for b in project.build_properties()}
		${if getattr(b, 'deploy_dir', None)}
	<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='${b.configuration}|${b.platform}'">
		<Deploy>
			<DeploymentType>CopyToHardDrive</DeploymentType>
		</Deploy>
	</ItemDefinitionGroup>
		${endif}
	${endfor}

	<ItemGroup>
		${for x in project.source}
		<${project.get_key(x)} Include='${x.abspath()}' />
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
		${for x in project.source}
			<${project.get_key(x)} Include="${x.abspath()}">
				<Filter>${x.parent.path_from(project.path)}</Filter>
			</${project.get_key(x)}>
		${endfor}
	</ItemGroup>
	<ItemGroup>
		${for x in project.dirs()}
			<Filter Include="${x.path_from(project.path)}">
				<UniqueIdentifier>{${project.make_guid(x.abspath())}}</UniqueIdentifier>
			</Filter>
		${endfor}
	</ItemGroup>
</Project>
'''

SOLUTION_TEMPLATE = '''Microsoft Visual Studio Solution File, Format Version 11.00
# Visual Studio 2010
${for p in project}
Project("{${p.ptype()}}") = "${p.name}", "${p.get_path()}", "{${p.guid}}"
EndProject${endfor}
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		${if project}
		${for (configuration, platform) in project[0].ctx.project_configurations()}
		${configuration}|${platform} = ${configuration}|${platform}
		${endfor}
		${endif}
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		${for p in project}
			${if p.source}
			${for b in p.build_properties()}
		{${p.guid}}.${b.configuration}|${b.platform}.ActiveCfg = ${b.configuration}|${b.platform}
			${if p.ctx.is_build(p, b)}
		{${p.guid}}.${b.configuration}|${b.platform}.Build.0 = ${b.configuration}|${b.platform}
			${endif}
			${endfor}
			${endif}
		${endfor}
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(NestedProjects) = preSolution
	${for p in project}
		${if p.pguid}
		{${p.guid}} = {${p.pguid}}
		${endif}
	${endfor}
	EndGlobalSection
EndGlobal
'''

COMPILE_TEMPLATE = '''def f(project):
	lst = []
	%s

	f = open('cmd.txt', 'w')
	f.write(str(lst))
	f.close()
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
			app(f[3:])
		elif f.startswith('endif') or f.startswith('endfor'):
			indent -= 1
		else:
			#app('lst.append((%s) or "cannot find %s")' % (f, f))
			app('lst.append(%s)' % f)

	if extr:
		if params[-1]:
			app("lst.append(%r)" % params[-1])

	fun = COMPILE_TEMPLATE % "\n\t".join(buf)
	#print fun
	return Task.funex(fun)

re_blank = re.compile('\n\s*\n', re.M)
def rm_blank_lines(txt):
	txt = re_blank.sub('\n', txt)
	return txt


def make_guid(v, prefix = None):
	"""
	simple utility function
	"""
	if isinstance(v, dict):
		keys = list(v.keys())
		keys.sort()
		tmp = str([(k, v[k]) for k in keys])
	else:
		tmp = str(v)
	d = Utils.md5(tmp.encode()).hexdigest().upper()
	if prefix:
		d = '%s%s' % (prefix, d[8:])
	gid = uuid.UUID(d, version = 4)
	return str(gid).upper()

class build_property(object):
	pass

class project(object):
	"""
	TODO this class is going to be split to make a proper hierarchy
	"""
	VS_GUID_VCPROJ         = "8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942"
	VS_GUID_SOLUTIONFOLDER = "2150E333-8FDC-42A3-9474-1A3956D46DE8"

	def __init__(self, ctx, tg=None, name=None):
		"""
		A project is more or less equivalent to a file/folder
		"""
		self.ctx    = ctx # context of the command
		self.pguid  = None # optional, guid to the parent project
		self.source = []  # list of source files
		if tg:
			self.tg     = tg  # task generator
			self.name   = name or tg.name # some kind of title for the solution (task generator target name)

			base = getattr(self.ctx, 'projects_dir', None) or tg.path
			self.path   = base.make_node(self.name + self.ctx.project_extension) # Node
			self.guid   = self.make_guid(self.path.abspath()) # unique id

			# self.title - when no absolute path is provided, set the absolute path

	def collect_source(self):
		tg = self.tg
		source_files = tg.to_nodes(getattr(tg, 'source', []))
		include_dirs = Utils.to_list(getattr(tg, 'includes', [])) + Utils.to_list(getattr(tg, 'export_dirs', []))
		include_files = []
		for x in include_dirs:
			if not isinstance(x, str):
				include_files.append(x)
				continue
			d = tg.path.find_node(x)
			if d:
				lst = [y for y in d.ant_glob(HEADERS_GLOB, flat=False)]
				include_files.extend(lst)

		# remove duplicates
		self.source.extend(list(set(source_files + include_files)))
		self.source.sort(key=lambda x: x.abspath())

	def collect_configurations(self):
		for c in self.ctx.configurations:
			for p in self.ctx.platforms:
				b = build_property()
				b.configuration = c
				b.platform = p
				try:
					b.output_file = self.tg.link_task.outputs[0].abspath()
				except:
					pass
				b.pre_defines = ' '.join([self.tg.env.DEFINES_ST % x for x in self.tg.env.DEFINES])

	def dirs(self):
		"""
		Get the list of parent folders for writing the filters
		"""
		lst = []
		for x in self.source:
			if x.parent not in lst:
				lst.append(x.parent)
		return lst

	def get_path(self):
		return getattr(self, 'title', self.path.abspath())

	def make_guid(self, val):
		return make_guid(val)

	def ptype(self):
		if not self.source:
			return self.VS_GUID_SOLUTIONFOLDER
		return self.VS_GUID_VCPROJ

	def build_properties(self):
		"""
		Returns a list of triplet (configuration, platform, output_directory)
		"""
		ret = []
		for c in self.ctx.configurations:
			for p in self.ctx.platforms:
				x = build_property()

				x.configuration = c
				x.platform = p

				x.outdir = self.path.parent.abspath()
				x.pre_defines = ''

				try:
					tsk = self.tg.link_task
				except:
					pass
				else:
					x.output_file = tsk.outputs[0].abspath()
					x.pre_defines = ' '.join([tsk.env.DEFINES_ST % k for k in tsk.env.DEFINES])

				# can specify "deploy_dir" too
				ret.append(x)
		return ret

	def get_key(self, node):
		name = node.name
		if name.endswith('.cpp') or name.endswith('.c'):
			return 'ClCompile'
		return 'ClInclude'

	def get_build_command(self, props):
		waf = self.ctx.srcnode.find_node('waf') or self.ctx.srcnode.find_node('waf.bat')
		waf = waf and waf.abspath() or 'waf'
		opt = '--execsolution=%s' % self.ctx.get_solution_node().abspath()
		return "%s build %s" % (waf, opt)

	def get_clean_command(self, props):
		waf = self.ctx.srcnode.find_node('waf') or self.ctx.srcnode.find_node('waf.bat')
		waf = waf and waf.abspath() or 'waf'
		opt = '--execsolution=%s' % self.ctx.get_solution_node().abspath()
		return "%s clean %s" % (waf, opt)

	def get_rebuild_command(self, props):
		waf = self.ctx.srcnode.find_node('waf') or self.ctx.srcnode.find_node('waf.bat')
		waf = waf and waf.abspath() or 'waf'
		opt = '--execsolution=%s' % self.ctx.get_solution_node().abspath()
		return "%s clean build %s" % (waf, opt)

class msvs_generator(BuildContext):
	cmd = 'msvs'
	fun = 'build'
	variant = 'Debug'

	def init(self):
		"""
		Some data that needs to be present
		"""
		if not getattr(self, 'configurations', None):
			self.configurations = ['Release'] # LocalRelease, RemoteDebug, etc
		if not getattr(self, 'platforms', None):
			self.platforms = ['Win32']
		if not getattr(self, 'all_projects', None):
			self.all_projects = []
		if not getattr(self, 'project_extension', None):
			self.project_extension = '.vcxproj'
		if not getattr(self, 'projects_dir', None):
			self.projects_dir = self.bldnode.make_node('depproj')
			self.projects_dir.mkdir()

	def execute(self):
		"""
		Entry point
		"""
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])

		# user initialization
		self.init()

		# two phases for creating the solution
		self.collect_projects() # add project objects into "self.all_projects"
		self.write_files() # write the corresponding project and solution files

	def collect_projects(self):
		"""
		Fill the list self.all_projects with project objects
		Fill the list of build targets
		"""
		self.collect_targets()
		self.collect_dirs()
		self.all_projects.sort(key=lambda x: x.path.abspath())

	def write_files(self):
		"""
		Write the project and solution files from the data collected
		so far. It is unlikely that you will want to change this
		"""
		for p in self.all_projects:
			if not p.source:
				continue

			Logs.warn('Creating %r' % p.path)

			# first write the project file
			template1 = compile_template(PROJECT_TEMPLATE)
			proj_str = template1(p)
			proj_str = rm_blank_lines(proj_str)
			p.path.write(proj_str)

			# then write the filter
			template2 = compile_template(FILTER_TEMPLATE)
			filter_str = template2(p)
			filter_str = rm_blank_lines(filter_str)
			tmp = p.path.parent.make_node(p.path.name + '.filters')
			tmp.write(filter_str)

		# and finally write the solution file
		node = self.get_solution_node()
		node.parent.mkdir()
		Logs.warn('Creating %r' % node)
		template1 = compile_template(SOLUTION_TEMPLATE)
		sln_str = template1(self.all_projects)
		sln_str = rm_blank_lines(sln_str)
		node.write(sln_str)

	def get_solution_node(self):
		"""
		The solution filename is required when writing the .vcproj files
		return self.solution_node and if it does not exist, make one
		"""
		try:
			return self.solution_node
		except:
			pass

		solution_name = getattr(self, 'solution_name', None)
		if not solution_name:
			solution_name = getattr(Context.g_module, Context.APPNAME, 'project') + '.sln'
		if os.path.isabs(solution_name):
			self.solution_node = self.root.make_node(solution_name)
		else:
			self.solution_node = self.srcnode.make_node(solution_name)
		return self.solution_node

	def project_configurations(self):
		"""
		Helper that returns all the pairs (config,platform)
		"""
		ret = []
		for c in self.configurations:
			for p in self.platforms:
				ret.append((c, p))
		return ret

	def is_build(self, p, props):
		"""
		Helper for the "guid.config.Build.0 = config"
		The idea is to enable exactly one line of such kind by platform/config
		"""
		try:
			cache = self.is_build_cache
		except AttributeError:
			cache = self.is_build_cache = {}
		key = (props.configuration, props.platform)
		if key in cache:
			return False
		cache[key] = True
		return True

	def collect_targets(self):
		for g in self.groups:
			for tg in g:
				if not isinstance(tg, TaskGen.task_gen):
					continue

				tg.post()
				if not getattr(tg, 'link_task', None):
					continue

				p = project(self, tg)
				p.collect_source() # delegate this processing
				p.collect_configurations()
				self.all_projects.append(p)

	def collect_dirs(self):

		seen = set([])
		def make_parents(x):
			if x in seen:
				return
			seen.add(x)

			# create a project representing the folder "x"
			n = project(self, None)
			n.path = x
			n.guid = make_guid(x.abspath())
			n.name = n.title = n.path.name

			self.all_projects.append(n)

			# recurse up to the project directory
			if x.height() > self.srcnode.height() + 1:
				up = x.parent
				n.pguid = make_guid(up.abspath())
				make_parents(up)

		for p in self.all_projects[:]: # iterate over a copy of all projects
			if not p.tg:
				# but only projects that have a task generator
				continue

			# make a folder for each task generator
			parent = p.tg.path
			p.pguid = make_guid(parent.abspath())
			make_parents(parent)

def options(ctx):
	"""
	If the msvs option is used, try to detect if the build is made from visual studio
	"""
	ctx.add_option('--execsolution', action='store', help='when building with visual studio, use a build state file')

	old = BuildContext.execute
	def override_build_state(ctx):
		def lock(rm, add):
			uns = ctx.options.execsolution.replace('.sln', rm)
			uns = ctx.root.make_node(uns)
			try:
				uns.delete()
			except:
				pass

			uns = ctx.options.execsolution.replace('.sln', add)
			uns = ctx.root.make_node(uns)
			try:
				uns.write('')
			except:
				pass

		if ctx.options.execsolution:
			ctx.launch_dir = Context.top_dir # force a build for the whole project (invalid cwd when called by visual studio)
			lock('.lastbuildstate', '.unsuccessfulbuild')
			old(ctx)
			lock('.unsuccessfulbuild', '.lastbuildstate')
		else:
			old(ctx)
	BuildContext.execute = override_build_state

