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

	def accept(self, tg):
		"""
		Return True if a task generator can be used as a msvs project
		"""
		if not isinstance(tg, task_gen):
			return False

		if getattr(tg, 'no_msvs', None):
			# no error
			return False

		if not tg.name:
			try:
				e = self.msvs_project_errors
			except:
				e = self.msvs_project_errors = []
			e.append(tg)
			return False

		try:
			p = self.msvs_processed
		except:
			p = self.msvs_processed = {}
		if id(tg) in p:
			return
		p[id(tg)] = x

	def collect_projects(self):
		vcxprojs = []
		for g in self.groups:
			for x in g:
				if self.accept(tg):
					source_files = Utils.to_list(getattr(x, 'source', []))
					include_dirs = Utils.to_list(getattr(x, 'includes', [])) + Utils.to_list(getattr(x, 'export_dirs', []))

					project_generator = self.get_project_generator(x)
					generated_projfile = project_generator(platform, project, x.path.abspath(), source_files, include_dirs)
					vcxprojs.append(generated_projfile)

				if 'msvs_solution' in x.features and hasattr(x, "solution_dir"):
					solution_name = os.path.join(x.path.abspath(), x.solution_dir, "_%s.sln" % (project, platform))
		#vcxprojs += msvs_project_generator.generateMSVSProjects_External(platform)
		return vcxprojs

	def create_files(self):
		"""
		Two parts here: projects and solution files
		"""
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
		vcxprojs = self.collect_projects

	def create_solution(self):
		if getattr(self, 'solution_name', None):
			Logs.warn('Creating: %s' % self.solution_name)
			mssolution.GenerateMSVSSolution(self.solution_name, platform, vcxprojs)
		else:
			self.msvs_solution_errors = True

