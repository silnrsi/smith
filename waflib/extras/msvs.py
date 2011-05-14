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
from waflib import Utils

BIN_GUID_PREFIX = Utils.md5('BIN').hexdigest()[:8].upper()
LIB_GUID_PREFIX = Utils.md5('LIB').hexdigest()[:8].upper()
SPU_GUID_PREFIX = Utils.md5('SPU').hexdigest()[:8].upper()
SAR_GUID_PREFIX = Utils.md5('SAR').hexdigest()[:8].upper()
EXT_GUID_PREFIX = Utils.md5('EXT').hexdigest()[:8].upper()
FRG_GUID_PREFIX = Utils.md5('FRG').hexdigest()[:8].upper()
SHA_GUID_PREFIX = Utils.md5('SHA').hexdigest()[:8].upper()

VS_GUID_VCPROJ         = "8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942"
VS_GUID_SOLUTIONFOLDER = "2150E333-8FDC-42A3-9474-1A3956D46DE8"

class msvs_generator(Build.BuildContext):
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
			for x in g:
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
		features = tg.to_list(getattr(tg, 'features', []))
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


	#############################################################################################################
	# TODO

	def do_solution(self):
		pass
		#mssolution.GenerateMSVSSolution(self.solution_name, platform, self.vcxprojs)

	def do_one_project(self, tg)
		#platform, project, base_path, source_files, include_dirs, guid):

		#source_files = Utils.to_list(getattr(x, 'source', []))
		#include_dirs = Utils.to_list(getattr(x, 'includes', [])) + Utils.to_list(getattr(x, 'export_dirs', []))
		#project_generator = self.get_project_generator(x)
		#generated_projfile = project_generator(platform, project, x.path.abspath(), source_files, include_dirs)
		#if 'msvs_solution' in x.features and hasattr(x, "solution_dir"):
			#solution_name = os.path.join(x.path.abspath(), x.solution_dir, "_%s.sln" % (project, platform))

		platform = self.platform
		project = tg.name
		base_path = tg.path.abspath()
		source_files = Utils.to_list(getattr(tg, 'source', []))
		include_dirs = Utils.to_list(getattr(x, 'includes', [])) + Utils.to_list(getattr(x, 'export_dirs', []))
		guid = self.get_guid_prefix()

		if not base_path.endswith("/") or not base_path.endswith("\\"):
			base_path += "/"

		# Grab all headers in the base_path and its subdirs.
		# The base_path points to  where the wscript file lies on disk.

		include_files = []
		for dir in include_dirs:
			search_dir = base_path + dir.strip()
			prep = dir.strip()+"\\"
			include_files += getFiles2(search_dir, ".h", prep)
			include_files += getFiles2(search_dir, ".inl", prep)

		values = { 'sources'	   : source_files + include_files,
				   'abs_path'	  : base_path,
				   'platform'	  : platform,
				   'name'		  : project,
				   'flags_debug'   : '',
				   'flags_release' : '',
				   'flags_final'   : '',
				   'include_dirs'  : '' }

		values['guid'] = self.make_guid(values, prefix = guid)
		out = self.bldnode().make_node('depprojs')
		out.mkdir()
		OUTPUT_PATH = out.abspath()

		proj_file   = out.make_node('%s_%s.vcxproj' % (project, platform))
		filter_file = out.make_node('%s_%s.vcxproj.filters' % (project, platform))

		Logs.warn('Creating %s' % proj_file)

		if guid == BIN_GUID_PREFIX:
			(proj_str, filter_str) = createProjectString(values, getBinProjectConfigs(values))
		else:
			(proj_str, filter_str) = createProjectString(values, getLibProjectConfigs(values))

		proj_file.write(proj_str)
		filter_file.write(filter_str)

		return proj_file.abspath()

