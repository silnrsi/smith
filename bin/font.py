#!/usr/bin/python

from waflib import Context
from wafplus import *
import font_tests, templater
import sys, os, re

progset = set()

class Font(object) :
    fonts = []

    def __init__(self, *k, **kw) :
        if not 'id' in kw :
            kw['id'] = kw['test_suffix'] if 'test_suffix' in kw else kw['target'].lower().replace('.ttf','')
        self.volt_params = ""
        self.gdl_params = ""

        for k, item in kw.items() :
            setattr(self, k, item)
        if not isinstance(self.source, basestring) :
            self.legacy = self.source
            self.source = self.legacy.target
        self.fonts.append(self)

    def get_build_tools(self) :
        res = set()
        if getattr(self, 'source', "").endswith(".sfd") :
            res.add('fontforge')
            res.add('sfdmeld')
            if getattr(self, 'source_ap', None) :
                res.add('sfd2ap')
        if getattr(self, 'version', None) :
            res.add('ttfsetver')
        if getattr(self, 'classes', None) :
            res.add('add_classes')
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'legacy')) :
            if x :
                res.update(x.get_build_tools())
        return res

    def build(self, bld) :
        res = {}

        # convert from legacy
        if getattr(self, 'legacy', None) :
            self.legacy.build(bld, getattr(self, 'ap', None))

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

        if getattr(self, 'version') :
            modify("${TTFSETVER} " + self.version + " ${DEP} ${TGT}", self.target)

        # add smarts
        if getattr(self, 'ap', None) :
            if self.source.endswith(".sfd") :
                bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.source, target = self.ap)
            if getattr(self, 'classes', None) :
                modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.ap, [self.classes], shell = 1)
        
        # add smarts
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite')) :
            if x :
                x.build(bld, self.target, bgen, self)
        return self

class Legacy(object) :

    def __init__(self, src, *k, **kw) :
        self.target = src
        self.params = ''
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        res = ["ttfbuilder"]
        if self.target.endswith('.sfd') :
            res.append("fontforge")
        return res

    def build(self, bld, targetap) :
        cmd = ""
        srcs = [self.source, self.xml]
        if getattr(self, 'ap', None) :
            srcs.append(self.ap)
            cmd += " -x ${SRC[2].bldpath()}"
        trgt = [re.sub(r'\..*', '.ttf', self.target)]
        if targetap :
            trgt.append(targetap)
            cmd += " -z ${TGT[1].bldpath()}"
        bld(rule = "${TTFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].bldpath()}", source = srcs, target = trgt)
        if self.target.endswith(".sfd") :
            bld(rule = "${FONTFORGE} -nosplash -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.target, shell = 1)


class Volt(object) :

    def __init__(self, source, *k, **kw) :
        self.source = source
        self.params = ''
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return ('make_volt', 'volt2ttf')

    def build(self, bld, target, tgen, font) :
        cmd = getattr(self, 'make_params', '') + " "
        ind = 0
        srcs = []
        if getattr(font, 'ap', None) :
            srcs.append(font.ap)
            cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        if getattr(self, 'master', None) :
            srcs.append(self.master)
            cmd += "-i ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        bld(rule = "${MAKE_VOLT} " + cmd + "-t " + bld.path.find_or_declare(target).bldpath() + " > ${TGT}", shell = 1, source = srcs + [target], target = self.source)
        modify("${VOLT2TTF} " + self.params + " -t ${SRC} ${DEP} ${TGT}", target, [self.source])


class Gdl(object) :

    def __init__(self, source, *k, **kw) :
        self.source = source
        self.params = ''
        self.master = ''
        for k, v in kw.items() :
            setattr(self, k, v)
    
    def get_build_tools(self) :
        return ("make_gdl", "grcompiler")

    def build(self, bld, target, tgen, font) :
        if self.source :
            srcs = []
            cmd = getattr(self, 'make_params', '') + " "
            ind = 0
            if getattr(font, 'ap', None) :
                srcs.append(font.ap)
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
            if getattr(self, 'master', None) :
                srcs.append(self.master)
                cmd += "-i ../${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
            bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(target).bldpath() + " ${TGT}", shell = 1, source = srcs + [target], target = self.source)
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.source])
        elif self.master :
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.master])

def process(tgt, *cmds, **kw) :
    for c in cmds :
        res = c(tgt)
        modify(res[0], tgt, res[1], **res[2])
    return tgt

def create(tgt, *cmds, **kw) :
    for c in cmds :
        res = c(tgt)
        rule(res[0], res[1], tgt, **res[2])
    return tgt

def cmd(c, inputs, **kw) :
    def icmd(tgt) :
        return (c, inputs, kw)
    return icmd

def name(n, **kw) :
    progset.add('ttfname')
    kw['shell'] = 1
    opts = " "
    if 'lang' in kw :
        opts += "-l " + kw['lang'] + " "
        del kw['lang']
    def iname(tgt) :
        return ('${TTFNAME} -n "' + n + '"' + opts + "${DEP} ${TGT}", [], kw)
    return iname

def add_configure() :
    old_config = getattr(Context.g_module, "configure", None)

    def configure(ctx) :
        programs = set()
        for f in Font.fonts :
            programs.update(f.get_build_tools())
        programs.update(font_tests.configure_tests(ctx, Font.fonts))
        programs.update(progset)
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
Context.g_module.legacy = Legacy
Context.g_module.volt = Volt
Context.g_module.gdl = Gdl
Context.g_module.process = process
Context.g_module.create = create
Context.g_module.cmd = cmd
Context.g_module.name = name
