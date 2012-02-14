#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context
from wafplus import modify
import font_tests, package, keyboard
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
            self.package = package.Package.global_package()
        self.package.add_font(self)
        if not hasattr(self, 'tests') :
            self.tests = font_tests.global_test()

    def get_build_tools(self, ctx) :
        res = self.tests.config(ctx)
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
        res.update(progset)
        return res

    def get_sources(self, ctx) :
        res = []
        if hasattr(self, 'legacy') :
            res.extend(self.legacy.get_sources(ctx))
        else :
            res.append(self.source)
        res.append(getattr(self, 'sfd_master', None))
        res.append(getattr(self, 'classes', None))
        res.append(getattr(self, 'ap', None))
        for x in (getattr(self, y, None) for y in ('license', 'opentype', 'graphite', 'tests')) :
            if x :
                res.extend(x.get_sources(ctx))
        res.extend(getattr(self, 'extra_srcs', []))
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
                if tarnode != srcnode :
                    bld(rule = "${COPY} ${SRC} ${TGT}", source = srcnode.get_src(), target = tarnode)
                modify("${SFDMELD} ${SRC} ${DEP} ${TGT}", self.source, [self.sfd_master], path = bld.srcnode.find_node('wscript').abspath(), before = self.target)
                srcnode = tarnode
            bgen = bld(rule = "${FONTFORGE} -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = srcnode, target = self.target, name = self.target + "_sfd")

        if hasattr(self, 'version') :
            modify("${TTFSETVER} " + self.version + " ${DEP} ${TGT}", self.target, path = bld.srcnode.find_node('wscript').abspath())
        if hasattr(self, 'copyright') :
            modify("${TTFNAME} -t 0 -n '%s' ${DEP} ${TGT}" % (self.copyright), self.target, path = bld.srcnode.find_node('wscript').abspath())
        if hasattr(self, 'license') :
            if hasattr(self.license, 'reserve') :
                self.package.add_reservedofls(*self.license.reserve)
            self.license.build(bld, self)

        # add smarts
        if hasattr(self, 'ap') :
            if not hasattr(self, 'legacy') :
                apnode = bld.path.find_or_declare(self.ap)
                if self.source.endswith(".sfd") :
                    apopts = getattr(self, 'ap_params', "")
                    bld(rule = "${SFD2AP} " + apopts + " ${SRC} ${TGT}", source = self.source, target = apnode)
                else :
                    bld(rule="${COPY} ${SRC} ${TGT}", source = apnode.get_src(), target = apnode.get_bld())
            if hasattr(self, 'classes') :
                modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.ap, [self.classes], shell = 1, path = bld.srcnode.find_node('wscript').abspath())
        
        # add smarts
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite')) :
            if x :
                x.build(bld, self.target, bgen, self)
        return self

    def build_pdf(self, bld) :
        if self.tests :
            self.tests.build_tests(bld, self, 'pdfs')

    def build_svg(self, bld) :
        if self.tests :
            self.tests.build_tests(bld, self, 'svg')

    def build_test(self, bld) :
        if self.tests :
            self.tests.build_tests(bld, self, 'test')


class Legacy(object) :

    def __init__(self, src, *k, **kw) :
        self.target = src
        self.params = ''
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        if self.source.endswith(".ttf") :
            res = ["ttfbuilder"]
            if self.target.endswith('.sfd') :
                res.append("fontforge")
        else :
            res = ["ffbuilder", "sfd2ap"]
        return res

    def get_sources(self, ctx) :
        res = [self.source, self.xml]
        res.append(getattr(self, 'ap', None))
        return res

    def build(self, bld, targetap) :
        cmd = " " + getattr(self, 'params', "")
        srcs = [self.source, self.xml]
        if self.source.endswith(".ttf") :
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
        else :
            bld(rule = "${FFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].bldpath()}", source = srcs, target = self.target)
            if targetap :
                bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.target, target = targetap)


class Internal(object) :

    def __init__(self, src = None, *k, **kw) :
        self.source = src
        self.params = ''
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return []

    def get_sources(self, ctx) :
        return []

    def build(self, bld, target, tgen, font) :
        pass


class Volt(Internal) :

    def __init__(self, source, *k, **kw) :
        super(Volt, self).__init__(source, *k, **kw)

    def get_build_tools(self) :
        return ('make_volt', 'volt2ttf')

    def get_sources(self, ctx) :
        return [getattr(self, 'master', None)]

    def build(self, bld, target, tgen, font) :
        cmd = getattr(self, 'make_params', '') + " "
        ind = 0
        srcs = []
        if hasattr(font, 'ap') :
            srcs.append(bld.path.find_or_declare(font.ap))
            cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        if hasattr(self, 'master') :
            srcs.append(self.master)
            cmd += "-i ${SRC[" + str(ind) + "].bldpath()} "
            ind += 1
        bld(rule = "${MAKE_VOLT} " + cmd + "-t " + bld.path.find_or_declare(target).bldpath() + " > ${TGT}", shell = 1, source = srcs + [target], target = self.source)
        modify("${VOLT2TTF} " + self.params + " -t ${SRC} ${DEP} ${TGT}", target, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_ot")


class Gdl(Internal) :

    def __init__(self, source, *k, **kw) :
        self.master = ''
        self.params = ''
        super(Gdl, self).__init__(source, *k, **kw)
    
    def get_build_tools(self) :
        return ("make_gdl", "grcompiler", "ttftable")

    def get_sources(self, ctx) :
        return [getattr(self, 'master', None)]

    def build(self, bld, target, tgen, font) :
        srcs = [self.source]
        if self.master : srcs.append(self.master)
        modify("${TTFTABLE} -delete graphite ${DEP} ${TGT}", target, srcs, path = bld.srcnode.find_node('wscript').abspath())
        if self.source :
            srcs = []
            cmd = getattr(self, 'make_params', '') + " "
            ind = 0
            if hasattr(font, 'ap') :
                srcs.append(bld.path.find_or_declare(font.ap))
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
            if self.master :
                srcs.append(self.master)
                mnode = bld.path.find_or_declare(self.master)
                snode = bld.bldnode.find_or_declare(self.source)
                loc = mnode.path_from(snode.parent)
                cmd += '-i "' + loc + '" '
                ind += 1
            bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(target).bldpath() + " ${TGT}", shell = 1, source = srcs + [target], target = self.source)
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr")
        elif self.master :
            modify("${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.master], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr")

class Ofl(object) :

    def __init__(self, *reserved, **kw) :
        if not 'version' in kw : kw['version'] = 1.1
        if not 'copyright' in kw : kw['copyright'] = getattr(Context.g_module, 'COPYRIGHT', '')
        self.reserve = reserved
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return ["ttfname"]

    def get_sources(self, ctx) :
        return []

    def build(self, bld, font) :
        modify(self.insert_ofl, font.target, path = bld.srcnode.find_node('wscript').abspath())
        
    def globalofl(self, task) :
        bld = task.generator.bld
        make_ofl(self.file, self.all_reserveds, self.version, copyright = self.copyright, template = getattr(self, 'template', None))
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

def make_ofl(fname, names, version, copyright = None, template = None) :
    oflh = file(fname, "w+")
    if copyright : oflh.write(copyright + "\n")
    if names :
        oflh.write("Reserved Font Names: " + ", ".join(map(lambda x: '"%s"' % x, names)) + "\n")
    if not template :
        oflbasefn = "OFL_" + str(version).replace('.', '_') + '.txt'
        thisdir = os.path.dirname(__file__)
        template = os.path.join(thisdir, oflbasefn)
    oflbaseh = file(template, "r")
    for l in oflbaseh.readlines() : oflh.write(l)
    oflbaseh.close()
    oflh.close()
    return fname

def make_tempnode(bld) :
    return os.path.join(bld.bldnode.abspath(), ".tmp", "tmp" + str(randint(0, 100000)))
    
def name(n, **kw) :
    progset.add('ttfname')
    kw['shell'] = 1
    opts = " "
    if 'lang' in kw :
        opts += "-l " + kw['lang'] + " "
        del kw['lang']
    if 'string' in kw :
        opts += "-t " + kw['string'] + " "
        del kw['string']
    if 'full' in kw :
        opts += '-f "' + kw['full'] + '" '
        del kw['full']
    if 'nopost' in kw :
        opts += '-p '
    def iname(tgt) :
        return ('${TTFNAME} -n "' + n + '"' + opts + "${DEP} ${TGT}", [], kw)
    return iname

def onload(ctx) :
    varmap = { 'font' : Font, 'legacy' : Legacy, 'volt' : Volt,
            'gdl' : Gdl, 'name' : name, 'ofl' : Ofl,
            'internal' : Internal, 'fonttest' : font_tests.font_test,
            'tex' : font_tests.TeX, 'svg' : font_tests.SVG,
            'tests' : font_tests.Tests
             }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)

