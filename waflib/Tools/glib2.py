#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"GLib2 support"

from waflib import Task, Utils
from waflib.TaskGen import taskgen_method, before, after, feature

#
# glib-genmarshal
#

@taskgen_method
def add_marshal_file(self, filename, prefix):
	if not hasattr(self, 'marshal_list'):
		self.marshal_list = []
	self.meths.append('process_marshal')
	self.marshal_list.append((filename, prefix))

@before('process_source')
def process_marshal(self):
	for f, prefix in getattr(self, 'marshal_list', []):
		node = self.path.find_resource(f)

		if not node:
			raise Errors.WafError('file not found %r' % f)

		h_node = node.change_ext('.h')
		c_node = node.change_ext('.c')

		task = self.create_task('glib_genmarshal', node, [h_node, c_node])
		task.env.GLIB_GENMARSHAL_PREFIX = prefix
	self.source.append(c_node)

def genmarshal_func(self):

	bld = self.inputs[0].__class__.ctx

	get = self.env.get_flat
	cmd1 = "%s %s --prefix=%s --header > %s" % (
		get('GLIB_GENMARSHAL'),
		self.inputs[0].srcpath(self.env),
		get('GLIB_GENMARSHAL_PREFIX'),
		self.outputs[0].abspath(self.env)
	)

	ret = bld.exec_command(cmd1)
	if ret: return ret

	#print self.outputs[1].abspath(self.env)
	f = open(self.outputs[1].abspath(self.env), 'wb')
	c = '''#include "%s"\n''' % self.outputs[0].name
	f.write(c.encode("utf-8"))
	f.close()

	cmd2 = "%s %s --prefix=%s --body >> %s" % (
		get('GLIB_GENMARSHAL'),
		self.inputs[0].srcpath(self.env),
		get('GLIB_GENMARSHAL_PREFIX'),
		self.outputs[1].abspath(self.env)
	)
	ret = Utils.exec_command(cmd2)
	if ret: return ret

#
# glib-mkenums
#

@taskgen_method
def add_enums_from_template(self, source='', target='', template='', comments=''):
	if not hasattr(self, 'enums_list'):
		self.enums_list = []
	self.meths.append('process_enums')
	self.enums_list.append({'source': source,
	                        'target': target,
	                        'template': template,
	                        'file-head': '',
	                        'file-prod': '',
	                        'file-tail': '',
	                        'enum-prod': '',
	                        'value-head': '',
	                        'value-prod': '',
	                        'value-tail': '',
	                        'comments': comments})

@taskgen_method
def add_enums(self, source='', target='',
              file_head='', file_prod='', file_tail='', enum_prod='',
              value_head='', value_prod='', value_tail='', comments=''):
	if not hasattr(self, 'enums_list'):
		self.enums_list = []
	self.meths.append('process_enums')
	self.enums_list.append({'source': source,
	                        'template': '',
	                        'target': target,
	                        'file-head': file_head,
	                        'file-prod': file_prod,
	                        'file-tail': file_tail,
	                        'enum-prod': enum_prod,
	                        'value-head': value_head,
	                        'value-prod': value_prod,
	                        'value-tail': value_tail,
	                        'comments': comments})

@before('process_source')
def process_enums(self):
	for enum in getattr(self, 'enums_list', []):
		task = self.create_task('glib_mkenums')
		env = task.env

		inputs = []

		# process the source
		source_list = self.to_list(enum['source'])
		if not source_list:
			raise Errors.WafError('missing source ' + str(enum))
		source_list = [self.path.find_resource(k) for k in source_list]
		inputs += source_list
		env['GLIB_MKENUMS_SOURCE'] = [k.srcpath(env) for k in source_list]

		# find the target
		if not enum['target']:
			raise Errors.WafError('missing target ' + str(enum))
		tgt_node = self.path.find_or_declare(enum['target'])
		if tgt_node.name.endswith('.c'):
			self.source.append(tgt_node)
		env['GLIB_MKENUMS_TARGET'] = tgt_node.abspath(env)


		options = []

		if enum['template']: # template, if provided
			template_node = self.path.find_resource(enum['template'])
			options.append('--template %s' % (template_node.abspath(env)))
			inputs.append(template_node)
		params = {'file-head' : '--fhead',
		           'file-prod' : '--fprod',
		           'file-tail' : '--ftail',
		           'enum-prod' : '--eprod',
		           'value-head' : '--vhead',
		           'value-prod' : '--vprod',
		           'value-tail' : '--vtail',
		           'comments': '--comments'}
		for param, option in params.items():
			if enum[param]:
				options.append('%s %r' % (option, enum[param]))

		env['GLIB_MKENUMS_OPTIONS'] = ' '.join(options)

		# update the task instance
		task.set_inputs(inputs)
		task.set_outputs(tgt_node)

Task.task_factory('glib_genmarshal', func=genmarshal_func, vars=['GLIB_GENMARSHAL_PREFIX', 'GLIB_GENMARSHAL'],
	color='BLUE', ext_out='.h')
Task.task_factory('glib_mkenums',
	'${GLIB_MKENUMS} ${GLIB_MKENUMS_OPTIONS} ${GLIB_MKENUMS_SOURCE} > ${GLIB_MKENUMS_TARGET}',
	color='PINK', ext_out='.h')

def configure(conf):
	conf.find_perl_program('glib-genmarshal', var='GLIB_GENMARSHAL')
	conf.find_perl_program('glib-mkenums', var='GLIB_MKENUMS')

