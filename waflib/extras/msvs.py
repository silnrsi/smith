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

from waflib.Build import BuildContext

class msvs_generator(Build.BuildContext):
	cmd = 'msvs'
	fun = 'build'

	def execute(self):
		self.restore()
		if not self.all_envs:
			self.load_envs()
			self.recurse([self.run_dir])
			self.create_files()

	def get_project_generator(self, taskgen):
		project_generators = {
			"cprogram"   : msvs_project_generator.generateMSVSProject_Binary,
			"cstlib"	 : msvs_project_generator.generateMSVSProject_StaticLib,
			"cxxprogram" : msvs_project_generator.generateMSVSProject_Binary,
			"cxxstlib"	 : msvs_project_generator.generateMSVSProject_StaticLib,
		}
		if hasattr(taskgen, "msvs_project_type") and project_generators.has_key(taskgen.msvs_project_type):
			return project_generators[taskgen.msvs_project_type]

		return msvs_project_generator.generateMSVSProject_UnknownType

	def get_tg_name(self, x):
		if hasattr(x, "msvs_project_name"): return x.msvs_project_name
		return x.name or None

	def create_files(self):
		processed   = []
		vcxprojs	= []
		platform    = getattr(self, 'platform', 'Win32')
		solution_name = None
		num_taskgen_errors = 0
		num_taskgen_warnings = 0

		for g in self.groups:
			for x in g:
				if not isinstance(x, task_gen):
					continue

				if 'msvs_project' in x.features:
					project = self.get_tg_name(x)
					if project == None:
						Logs.error('A task generator from the file "%s\\wscript" has the feature "msvs_project" but is missing the attribute "msvs_project_name". No project file will be generated.' % x.path.abspath())
						num_taskgen_errors += 1
						continue

					if project in processed:
						continue
					else:
						processed.append(project)

					source_files = Utils.to_list(getattr(x, 'source', []))
					include_dirs = Utils.to_list(getattr(x, 'includes', [])) + Utils.to_list(getattr(x, 'export_dirs', []))

					project_generator = self.get_project_generator(x)
					generated_projfile = project_generator(platform, project, x.path.abspath(), source_files, include_dirs)
					vcxprojs.append(generated_projfile)

				if 'msvs_solution' in x.features and hasattr(x, "solution_dir"):
					solution_name = os.path.join(x.path.abspath(), x.solution_dir, "_%s.sln" % (project, platform))

		# Projects for needy libraries.
		external_projects = msvs_project_generator.generateMSVSProjects_External(platform)
		vcxprojs += external_projects

		if num_taskgen_errors == 0:
			Logs.warn("VS project generation finished without errors.")
		else:
			Logs.warn('--------------------PROJECT ERRORS ----------------------')
			Logs.warn("VS project generation finished: %i errors!" % num_taskgen_errors)
			Logs.warn('---------------------------------------------------------')

		# Solution file.
		if solution_name != None:
			Logs.warn("Creating: %s" % solution_name)
			mssolution.GenerateMSVSSolution(solution_name, platform, vcxprojs)
		else:
			Logs.warn('----------------- SOLUTION ERROR -----------------------')
			Logs.warn(' No target with feature "msvs_solution" was found.')
			Logs.warn(' No solution file will be generated')
			Logs.warn('--------------------------------------------------------')


