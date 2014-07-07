#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Logs
from wafplus import modify, ismodified
from wsiwaf import get_all_sources
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
        if self.package is not None :
            self.package.add_font(self)
        if not hasattr(self, 'tests') :
            self.tests = font_tests.global_test()
        if not hasattr(self, 'ots_target') :
            self.ots_target = self.target[:-4] + "_ots.log"

    def __str__(self) : return self.target

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
        if hasattr(self, 'typetuner') :
            res.add('typetuner')
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'legacy', 'license', 'pdf', 'fret', 'woff')) :
            if x and not isinstance(x, basestring) :
                res.update(x.get_build_tools())
        res.update(progset)
        return res

    def get_sources(self, ctx) :
        res = get_all_sources(self, ctx, 'source', 'legacy', 'sfd_master', 'classes', 'ap', 'license', 'opentype', 'graphite', 'tests')
        res.extend(getattr(self, 'extra_srcs', []))
        return res
        
    def get_targets(self, ctx) :
        res = [self.target]
        return res

    def build(self, bld) :
        res = {}

        basepath = bld.srcnode.find_node('wscript').abspath()
        if self.source == self.target :
            Logs.error("Font source may not be the same as the target: '%s'" % self.target)
        # convert from legacy
        if hasattr(self, 'legacy') :
            self.legacy.build(bld, getattr(self, 'ap', None))

        # build font
        targetnode = bld.path.find_or_declare(self.target)
        tarname = None
        if self.source.endswith(".ttf") :
            bgen = bld(rule = "${COPY} ${SRC} ${TGT}", source = self.source, target = targetnode)
        else :
            srcnode = bld.path.find_or_declare(self.source)
            if getattr(self, "sfd_master", None) and self.sfd_master != self.source:
                tarname = self.source + "_"
                bld(rule = "${COPY} ${SRC} ${TGT}", source = srcnode, target = tarname)
                modify("${SFDMELD} ${SRC} ${DEP} ${TGT}", tarname, [self.sfd_master], path = basepath, before = self.target + "_sfd")
            bgen = bld(rule = "${FONTFORGE} -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = tarname or srcnode, target = self.target, name = self.target + "_sfd") # for old fontforges
            # bgen = bld(rule = "${FONTFORGE} -quiet -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = tarname or srcnode, target = self.target, name = self.target + "_sfd")

        if hasattr(self, 'version') :
            if hasattr(self.version, 'len') and not isinstance(self.version, basestring) :
                ttfsetverparms = "-d '" + self.version[1] + "' " + self.version[0]
            else :
                ttfsetverparms = str(self.version)
            modify("${TTFSETVER} " + ttfsetverparms + " ${DEP} ${TGT}", self.target, path = basepath, late = 1)
        if hasattr(self, 'copyright') :
            modify("${TTFNAME} -t 0 -n '%s' ${DEP} ${TGT}" % (self.copyright), self.target, path = basepath, late = 1)
        if hasattr(self, 'license') :
            if hasattr(self.license, 'reserve') :
                self.package.add_reservedofls(*self.license.reserve)
            self.license.build(bld, self)

        # add smarts
        if hasattr(self, 'ap') :
            if not hasattr(self, 'legacy') or hasattr(self.legacy, 'noap') :
                apnode = bld.path.find_or_declare(self.ap)
                if self.source.endswith(".sfd") and not os.path.exists(apnode.get_src().abspath()) :
                    apopts = getattr(self, 'ap_params', "")
                    bld(rule = "${SFD2AP} " + apopts + " ${SRC} ${TGT}", source = tarname or self.source, target = apnode)
                elif not hasattr(self.ap, 'isGenerated') and (hasattr(self, 'classes') or ismodified(self.ap, path = basepath)) :
                    origap = self.ap
                    self.ap = self.ap + ".smith"
                    bld(rule="${COPY} ${SRC} ${TGT}", source = origap, target = self.ap)
            # if hasattr(self, 'classes') :
            #     modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.ap, [self.classes], shell = 1, path = basepath)
        
        # add smarts
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'pdf', 'woff', 'fret')) :
            if x :
                x.build(bld, self.target, bgen, self)

        if hasattr(self, 'typetuner') :
            modify("${TYPETUNER} -o ${TGT} add ${SRC} ${DEP}", self.target, [self.typetuner])

        return self

    def build_test(self, bld, test='test') :
        if self.tests :
            self.tests.build_tests(bld, self, test)

    def build_ots(self, bld) :
        bld(rule="${OTS} ${SRC} > /dev/null 2>${TGT}", target=self.ots_target, source=[self.target], shell=1)

class Legacy(object) :

    def __init__(self, src, *k, **kw) :
        self.target = src
        self.params = ''
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        if self.source.lower().endswith(".ttf") :
            res = ["ttfbuilder"]
            if self.target.endswith('.sfd') :
                res.append("fontforge")
        else :
            res = ["ffbuilder", "sfd2ap"]
        return res

    def get_sources(self, ctx) :
        return get_all_sources(self, ctx, 'source', 'xml', 'ap')

    def build(self, bld, targetap) :
        cmd = " " + getattr(self, 'params', "")
        srcs = [self.source, self.xml]
        if self.source.lower().endswith(".ttf") :
            if hasattr(self, 'ap') :
                srcs.append(self.ap)
                cmd += " -x ${SRC[2].bldpath()}"
            trgt = [re.sub(r'\..*', '.ttf', self.target)]
            if targetap and not hasattr(self, 'noap') :
                trgt.append(targetap)
                cmd += " -z ${TGT[1].bldpath()}"
            bld(rule = "${TTFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].bldpath()}", source = srcs, target = trgt)
            if self.target.endswith(".sfd") :
                bld(rule = "${FONTFORGE} -quiet -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.target, shell = 1) # for old fontforge
                # bld(rule = "${FONTFORGE} -quiet -nosplash -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.target, shell = 1)
        else :
            bld(rule = "${FFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].bldpath()}", source = srcs, target = self.target)
            if targetap and not hasattr(self, 'noap') :
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
        return get_all_sources(self, ctx, 'master')

    def build(self, bld, target, tgen, font) :
        if not hasattr(self, 'no_make') :
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
        if hasattr(font, 'typetuner') and not getattr(self, 'no_typetuner', 0) :
            xmlparms = " -x ${TGT[0].bldpath()}"
            tgts = [target, font.typetuner]
            modify("${VOLT2TTF} " + self.params + xmlparms + " -t ${SRC} ${DEP} ${TGT}", tgts, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_ot")
        else :
            modify("${VOLT2TTF} " + self.params + " -t ${SRC} ${DEP} ${TGT}", target, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_ot")
            


class Gdl(Internal) :

    def __init__(self, source = None, *k, **kw) :
        self.master = ''
        self.params = ''
        super(Gdl, self).__init__(source, *k, **kw)
    
    def get_build_tools(self) :
        return ("make_gdl", "grcompiler", "ttftable")

    def get_sources(self, ctx) :
        return get_all_sources(self, ctx, 'master')

    def build(self, bld, target, tgen, font) :
        srcs = [font.source]
        if self.master : srcs.append(self.master)
        modify("${TTFTABLE} -delete graphite ${DEP} ${TGT}", target, srcs, path = bld.srcnode.find_node('wscript').abspath())
        prevars = ""
        if hasattr(self, 'gdlpp_prefs') :
            prevars = 'GDLPP_PREFS="' + self.gdlpp_prefs + '" '
        depends = getattr(self, 'depends', [])
        if self.source is not None :
            if not hasattr(self, 'no_make') :
                srcs = []
                cmd = getattr(self, 'make_params', '') + " "
                ind = 0
                if hasattr(font, 'ap') :
                    srcs.append(bld.path.find_or_declare(font.ap))
                    cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                    ind += 1
                if hasattr(font, 'classes') :
                    srcs.append(bld.path.find_or_declare(font.classes))
                    cmd += "-c ${SRC[" + str(ind) + "].bldpath()} "
                    ind += 1
                if self.master :
                    mnode = bld.path.find_or_declare(self.master)
                    srcs.append(mnode)
                    snode = bld.bldnode.find_or_declare(self.source)
                    loc = mnode.path_from(snode.parent)
#                    cmd += '-i ${SRC[' + str(ind) + "].bldpath()} "
                    cmd += '-i ' + loc + ' '
                    ind += 1
                bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(target).bldpath() + " ${TGT}", shell = 1, source = srcs + [target], target = self.source)
            modify(prevars + "${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr", deps = depends, shell = 1)
        elif self.master :
            modify(prevars + "${GRCOMPILER} " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.master], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr", deps = depends, shell = 1)


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
        modify(self.insert_ofl, font.target, path = bld.srcnode.find_node('wscript').abspath(), late = 1)
        
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
        tempfn = make_tempnode(bld)

        def dottfname(*opts) :
            cmd = [task.env.get_flat("TTFNAME")] + list(opts) + [task.dep.path_from(bld.bldnode), tempfn]
            task.exec_command(cmd, cwd = getattr(task, 'cwd', None), env = task.env.env or None)

        if hasattr(self, 'short') :
            licensetxt = u"This Font Software is licensed under the SIL Open Font License, Version 1.1"
            if len(self.reserve) :
                licensetxt += u" with Reserved Font Names " + " and ".join(map(lambda x: '"%s"' % x, self.reserve))
            dottfname("-t", "13", "-n", licensetxt)
        else :
            make_ofl(fname, self.reserve, self.version, copyright = self.copyright)
            dottfname("-t", "13", "-s", fname)
            os.unlink(fname)
        res = task.exec_command([task.env.get_flat("TTFNAME"), "-t", "14", "-n", "http://scripts.sil.org/OFL", tempfn, task.tgt.path_from(bld.bldnode)], cwd = getattr(task, 'cwd', None), env = task.env.env or None)
        os.unlink(tempfn)
        return res

def make_ofl(fname, names, version, copyright = None, template = None) :
    oflh = file(fname, "w+")
    # if copyright : oflh.write(copyright + "  (" + os.getenv('DEBEMAIL') + "), \n")
    # if copyright : oflh.write(copyright +"  (<URL|email>), \n")
    if copyright : oflh.write(copyright + "\n") # URL/email is not required and often doesn't exist. Find a better way to handle it if given.
    if names :
        oflh.write("with Reserved Font Name " + " and ".join(map(lambda x: '"%s"' % x, names)) + ".\n")
    if not template :
        oflbasefn = "OFL_" + str(version).replace('.', '_') + '.txt'
        thisdir = os.path.dirname(__file__)
        template = os.path.join(thisdir, oflbasefn)
    oflbaseh = file(template, "r")
    for l in oflbaseh.readlines() : oflh.write(l)
    oflbaseh.close()
    oflh.close()
    return fname

class Fret(object) :

    def __init__(self, tgt = None, **kw) :
        self.target = tgt
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return ['fret']

    def build(self, bld, tgt, tgen, font) :
        if self.target is None :
            output = tgt.replace(".ttf", ".pdf")
        else :
            output = self.target
        args = getattr(self, 'params', '-r')
        bld(rule = "${FRET} " + args + " ${SRC} ${TGT}", target = output, source = [tgt])

class Woff(object) :

    def __init__(self, tgt = None, **kw) :
        self.target = tgt
        for k, v in kw.items() :
            setattr(self, k, v)

    def get_build_tools(self) :
        return ['ttf2woff']

    def build(self, bld, tgt, tgen, font) :
        if self.target is None :
            output = tgt.replace(".ttf", ".woff")
        else :
            output = self.target
        args = getattr(self, 'params', '')
        bld(rule = "${TTF2WOFF} " + args + " ${SRC} ${TGT}", target = output, source = [tgt])

class Subset(Font) :

    def get_build_tools(self, ctx) :
        return ['ttfsubset']
        
    def build(self, bld) :
        srcs = []
        parms = getattr(self, 'params', '')
        config = getattr(self, 'config', None)
        count = 0
        if config is not None :
            parms += "-g ${SRC[" + str(count) + "].bldpath()} "
            srcs += [config]
            count += 1
        parms += "${SRC[" + str(count) + "].bldpath()} ${TGT}"
        srcs += [self.source]
        bld(rule = "${TTFSUBSET} " + parms, target = self.target, source = srcs)

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
    if 'subfamily' in kw :
        opts += '-w "' + kw['subfamily'] + '" '
        del kw['subfamily']
    def iname(tgt) :
        return ('${TTFNAME} -n "' + n + '"' + opts + "${DEP} ${TGT}", [], kw)
    return iname

def onload(ctx) :
    varmap = { 'font' : Font, 'legacy' : Legacy, 'volt' : Volt,
            'gdl' : Gdl, 'name' : name, 'ofl' : Ofl, 'fret' : Fret,
            'internal' : Internal, 'fonttest' : font_tests.font_test,
            'tex' : font_tests.TeX, 'svg' : font_tests.SVG,
            'tests' : font_tests.Tests, 'woff' : Woff, 'subset' : Subset
             }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)

