#!/usr/bin/python

from waflib import Context
from wafplus import *
import font_tests, templater
import sys, os, re

class Font(object) :
    fonts = []

    def __init__(self, *k, **kw) :
        if not 'id' in kw :
            kw['id'] = kw['test_suffix'] if 'test_suffix' in kw else kw['target'].lower().replace('.ttf','')
        self.volt_params = ""
        self.gdl_params = ""

        for k, item in kw.items() :
            setattr(self, k, item)
        self.fonts.append(self)

    def get_build_tools(self) :
        res = set()
        if getattr(self, 'source', "").endswith(".sfd") :
            res.add('fontforge')
            res.add('sfdmeld')
            if getattr(self, 'source_ap', None) :
                res.add('sfd2ap')
        if getattr(self, 'legacy', None) :
            res.add('ttfbuilder')
        if getattr(self, 'classes', None) :
            res.add('add_classes')
        if getattr(self, 'gdl_source', None) or getattr(self, 'gdl_master', None):
            res.add('grcompiler')
            res.add('make_gdl')
        if getattr(self, 'volt_source', None) :
            res.add('volt2ttf')
            res.add('make_volt')
        return res

    def build(self, bld) :
        res = {}

        # convert from legacy
        if getattr(self, 'legacy', None) :
            cmd = ""
            srcs = [self.legacy, self.legacy_xml]
            if getattr(self, 'legacy_ap', None) :
                srcs.append(self.legacy_ap)
                cmd += " -x ${SRC[2].bldpath()}"
            trgt = [re.sub(r'\..*', '.ttf', self.source)]
            if getattr(self, 'source_ap', None) :
                trgt.append(self.source_ap)
                cmd += " -z ${TGT[1].abspath()}"
            leggen = bld(rule = "${TTFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].abspath()}", source = srcs, target = trgt)
            res[trgt[0]] = leggen
            if len(trgt) > 1 : res[trgt[1]] = leggen
            if self.source.endswith(".sfd") :
                ffgen = bld(rule = "${FONTFORGE} -nosplash -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.source, shell = 1)
                res[self.source] = ffgen

        # build font
        if self.source.endswith(".ttf") :
            bgen = bld(rule = "${COPY} ${SRC} ${TGT}", source = self.source, target = self.target)
        else :
            srcnode = bld.path.find_or_declare(self.source)
            if getattr(self, "sfd_master", None) and self.sfd_master != self.source:
                tarnode = srcnode.get_bld()
                modify("${SFDMELD} ${SRC} ${DEP} ${TGT}", self.source, [self.sfd_master], before = self.target)
                srcnode = tarnode
            bgen = bld(rule = "${FONTFORGE} -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = srcnode, target = self.target)
        res[self.target] = bgen

        # add smarts
        if getattr(self, 'source_ap', None) and self.source.endswith(".sfd") :
            agen = bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.source, target = self.source_ap)
            res[self.source_ap] = agen
        if getattr(self, 'classes', None) :
            cgen = modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.source_ap, [self.classes], shell = 1)
        
        # add OT
        if getattr(self, 'volt_source', None) :
            cmd = getattr(self, 'make_volt_params', "") + " "
            ind = 0
            srcs = []
            if getattr(self, 'source_ap', None) :
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                srcs.append(self.source_ap)
                ind += 1
            if getattr(self, 'volt_master', None) :
                cmd += "-i ${SRC[" + str(ind) + "].bldpath()} "
                srcs.append(self.volt_master)
                ind += 1
            vgen = bld(rule = "${MAKE_VOLT} " + cmd + "-t " + bld.path.find_or_declare(self.target).bldpath() + " > ${TGT}", shell = 1, after = [res[self.target]], source = srcs, target = self.volt_source)
            res[self.volt_source] = vgen
            vtgen = modify("${VOLT2TTF} " + self.volt_params + " -t ${SRC} ${DEP} ${TGT}", self.target, [self.volt_source])

        # add graphite
        if getattr(self, 'gdl_source', None) :
            srcs = []
            cmd = getattr(self, 'make_gdl_params', '') + " "
            ind = 0
            if getattr(self, 'source_ap', None) :
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
                srcs.append(self.source_ap)
            if getattr(self, 'gdl_master', None) :
                cmd += "-i ../${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
                srcs.append(self.gdl_master)
            ggen = bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(self.target).bldpath() + " ${TGT}", shell = 1, after = [res[self.target]], source = srcs, target = self.gdl_source)
            res[self.gdl_source] = ggen
            gtgen = modify("${GRCOMPILER} " + self.gdl_params + " ${SRC} ${DEP} ${TGT}", self.target, [self.gdl_source])
        elif getattr(self, 'gdl_master', None) :
            gtgen = modify("${GRCOMPILER} " + self.gdl_params + " ${SRC} ${DEP} ${TGT}", self.target, [self.gdl_master])

        return self

def add_configure() :
    old_config = getattr(Context.g_module, "configure", None)

    def configure(ctx) :
        programs = set()
        for f in Font.fonts :
            programs.update(f.get_build_tools())
        programs.update(font_tests.configure_tests(ctx, Font.fonts))
        for p in programs :
            ctx.find_program(p, var=p.upper())
        ctx.find_program('cp', var='COPY')
        for key, val in Context.g_module.__dict__.items() :
            if key == key.upper() : ctx.env[key] = val
        if old_config :
            old_config(ctx)

    Context.g_module.configure = configure

def add_build() :
    old_build = getattr(Context.g_module, "build", None)

    def build(bld) :
        for f in Font.fonts :
            f.build(bld)
        if old_build : old_build(bld)

    Context.g_module.build = build

class pdfContext(Build.BuildContext) :
    cmd = 'pdfs'
    func = 'pdfs'

    def pre_build(self) :
        self.add_group('pdfs')
        font_tests.build_tests(self, Font.fonts, 'pdfs')

class svgContext(Build.BuildContext) :
    cmd = 'svg'
    func = 'svg'

    def pre_build(self) :
        self.add_group('svg')
        font_tests.build_tests(self, Font.fonts, 'svg')

class exeContext(Build.BuildContext) :
    cmd = 'exe'

    def pre_build(self) :
        
        thisdir = os.path.dirname(__file__)
        self.add_group('exe')
        # create a taskgen to expand the installer.nsi
        self.env.fonts = Font.fonts
        self.env.basedir = thisdir
        task = templater.Copier(env = self.env)
        task.set_inputs(self.root.find_resource(os.path.join(thisdir, 'installer.nsi')))
        task.set_outputs(self.path.find_or_declare('installer.nsi'))
        self.add_to_group(task)

        # taskgen to run nsismake
        self(rule='makensis -Oinstaller.log ${SRC}', source = 'installer.nsi', target = '%s-%s.exe' % (self.env['DESC_NAME'] or self.env['APPNAME'].title(), self.env['VERSION']))

add_configure()
add_build()
Context.g_module.font = Font
