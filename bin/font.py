#!/usr/bin/python

from waflib import Context
from wafplus import *
import font_tests, font_package
import sys, os, re
from random import randint

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
        if not hasattr(self, 'package') :
            self.package = font_package.global_package()
        self.package.add_font(self)

    def get_build_tools(self) :
        res = set()
        res.add("makensis")
        if getattr(self, 'source', "").endswith(".sfd") :
            res.add('fontforge')
            res.add('sfdmeld')
            if hasattr(self, 'ap') :
                res.add('sfd2ap')
        if hasattr(self, 'version') :
            res.add('ttfsetver')
        if hasattr(self, 'classes') :
            res.add('add_classes')
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'legacy', 'license')) :
            if x and not isinstance(x, basestring) :
                res.update(x.get_build_tools())
        return res

    def build(self, bld) :
        res = {}

        # convert from legacy
        if hasattr(self, 'legacy') :
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

        if hasattr(self, 'version') :
            modify("${TTFSETVER} " + self.version + " ${DEP} ${TGT}", self.target)
        if hasattr(self, 'copyright') :
            modify("${TTFNAME} -t 0 -n '%s' ${DEP} ${TGT}" % (self.copyright), self.target)
        if hasattr(self, 'license') :
            if hasattr(self.license, 'reserve') :
                self.package.add_reservedofls(*self.license.reserve)
            self.license.build(bld, self)

        # add smarts
        if hasattr(self, 'ap') :
            if self.source.endswith(".sfd") :
                bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.source, target = self.ap)
            if hasattr(self, 'classes') :
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
        if hasattr(self, 'ap') :
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
        if hasattr(font, 'ap') :
            srcs.append(font.ap)
            cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        if hasattr(self, 'master') :
            srcs.append(self.master)
            cmd += "-i ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        bld(rule = "${MAKE_VOLT} " + cmd + "-t " + bld.path.find_or_declare(target).bldpath() + " > ${TGT}", shell = 1, source = srcs + [target], target = self.source)
        modify("${VOLT2TTF} " + self.params + " -t ${SRC} ${DEP} ${TGT}", target, [self.source], name = font.target + "_ot")


class Gdl(object) :

    def __init__(self, source, *k, **kw) :
        self.source = source
        self.params = ''
        self.master = ''
        for k, v in kw.items() :
            setattr(self, k, v)
    
    def get_build_tools(self) :
        return ("make_gdl", "grcompiler", "ttftable")

    def build(self, bld, target, tgen, font) :
        modify("${TTFTABLE} -delete graphite ${DEP} ${TGT}", target, [getattr(self, 'source', None), getattr(self, 'master', None)])
        if self.source :
            srcs = []
            cmd = getattr(self, 'make_params', '') + " "
            ind = 0
            if hasattr(font, 'ap') :
                srcs.append(font.ap)
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
            if hasattr(self, 'master') :
                srcs.append(self.master)
                cmd += "-i ../${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
            bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(target).bldpath() + " ${TGT}", shell = 1, source = srcs + [target], target = self.source)
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.source], name = font.target + "_gr")
        elif self.master :
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.master], name = font.target + "_gr")

class Ofl(object) :

    def __init__(self, *reserved, **kw) :
        if not 'version' in kw : kw['version'] = 1.1
        if not 'copyright' in kw : kw['copyright'] = getattr(Context.g_module, 'COPYRIGHT', '')
        self.reserve = reserved
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return ["ttfname"]

    def build(self, bld, font) :
        modify(self.insert_ofl, font.target)
        
    def globalofl(self, task) :
        bld = task.generator.bld
        make_ofl(self.file, self.all_reserveds, self.version, copyright = self.copyright)
        return True

    def build_global(self, bld) :
        if not hasattr(self, 'file') : self.file = 'OFL.txt'
        bld(rule = self.globalofl)

    def insert_ofl(self, task) :
        bld = task.generator.bld
        fname = make_tempnode(bld)
        make_ofl(fname, self.reserve, self.version, copyright = self.copyright)
        tempfn = make_tempnode(bld)
        # ttfname -t 13 -s fname inputs[0] temp
        # ttfname -t 14 -p "http://scripts.sil.org/ofl" temp outputs[0]
        task.exec_command([task.env.get_flat("TTFNAME"), "-t", "13", "-s", fname, task.dep.path_from(bld.bldnode), tempfn], cwd = getattr(task, 'cwd', None), env = task.env.env or None)
        os.unlink(fname)
        res = task.exec_command([task.env.get_flat("TTFNAME"), "-t", "14", "-n", "http://scripts.sil.org/ofl", tempfn, task.tgt.path_from(bld.bldnode)], cwd = getattr(task, 'cwd', None), env = task.env.env or None)
        os.unlink(tempfn)
        return res

def make_ofl(fname, names, version, copyright = None) :
    oflh = file(fname, "w+")
    if copyright : oflh.write(copyright + "\n")
    if names :
        oflh.write("Reserved names: " + ", ".join(map(lambda x: '"%s"' % x, names)) + "\n")
    oflbasefn = "OFL_" + str(version).replace('.', '_') + '.txt'
    thisdir = os.path.dirname(__file__)
    oflbaseh = file(os.path.join(thisdir, oflbasefn), "r")
    for l in oflbaseh.readlines() : oflh.write(l)
    oflbaseh.close()
    oflh.close()
    return fname

def make_tempnode(bld) :
    return os.path.join(bld.bldnode.abspath(), ".tmp", "tmp" + str(randint(0, 100000)))
    
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
    opts = u" "
    if 'lang' in kw :
        opts += u"-l " + kw['lang'] + u" "
        del kw['lang']
    if 'string' in kw :
        opts += u"-t " + kw['string'] + u" "
        del kw['string']
    if 'full' in kw :
        opts += u'-f "' + kw['full'] + u'" '
        del kw['full']
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
        for p in font_package.Package.packages :
            p.build(bld)
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

def fontinit(ctx) :
    add_configure()
    add_build()

varmap = { 'font' : Font, 'legacy' : Legacy, 'volt' : Volt,
            'gdl' : Gdl, 'process' : process, 'create' : create,
            'cmd' : cmd, 'name' : name, 'ofl' : Ofl, 'init' : fontinit
         }
for k, v in varmap.items() :
    if hasattr(Context, 'wscript_vars') :
        Context.wscript_vars[k] = v
    else :
        setattr(Context.g_module, k, v)

