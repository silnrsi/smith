#!/usr/bin/python2
''' font module '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011 SIL International (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'


from waflib import Context, Logs
from wafplus import modify, ismodified
from wsiwaf import get_all_sources, initobj, initval, defer
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

        initobj(self, kw)
        if not isinstance(self.source, basestring) :
            self.legacy = self.source
            self.source = self.legacy.target
        self.fonts.append(self)
        if not hasattr(self, 'package') :
            self.package = package.Package.global_package()
        if self.package is not None :
            if hasattr(self.package, '__iter__') :
                for p in self.package : p.add_font(self)
            else :
                self.package.add_font(self)
        if not hasattr(self, 'ots_target') :
            self.ots_target = self.target[:-4] + "-ots.log"
        if not hasattr(self, 'fontlint_target') :
            self.fontlint_target = self.target[:-4] + "-fontlint.log"
        if not hasattr(self, 'pyfontaine_target') :
            self.pyfontaine_target = self.target[:-4] + "-pyfontaine.log"
        self._isbuilt = False

    def __str__(self) : return self.target

    def get_build_tools(self, ctx) :
        res = set()
        if getattr(self, 'source', "").lower().endswith(".ufo") and not hasattr(self, "buildusingfontforge") :
            res.add('psfufo2ttf')
        if not getattr(self, 'source', "").lower().endswith(".ttf") :
            res.add('fontforge')
            res.add('sfdmeld')
            if hasattr(self, 'ap') :
                if self.source.endswith('.sfd'):
                    res.add('sfd2ap')
                elif self.source.endswith('.ufo'):
                    res.add('psfexportanchors')
        if hasattr(self, 'version') :
            res.add('ttfsetver')
        # if hasattr(self, 'classes') :
        #     res.add('add_classes')
        if hasattr(self, 'typetuner') :
            res.add('typetuner')
        if hasattr(self, 'ttfautohint'):
            res.add('ttfautohint')
        if hasattr(self, 'buildusingfontforge') :
            res.add('fontforge')
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'legacy', 'license', 'pdf', 'fret', 'woff')) :
            if x and not isinstance(x, basestring) :
                res.update(x.get_build_tools(ctx))
        res.update(progset)
        return res

    def get_sources(self, ctx) :
        res = get_all_sources(self, ctx, 'source', 'legacy', 'sfd_master', 'classes', 'ap', 'license', 'opentype', 'graphite')
        res.extend(getattr(self, 'extra_srcs', []))
        return res
        
    def get_targets(self, ctx) :
        res = [self.target]
        if hasattr(self, 'woff') :
            woff = self.woff.target
            if woff is None :
                woff = str(self.target).replace('.ttf', '.woff')
            res.append(woff)
        return res

    def build(self, bld, ap=None) :
        res = {}
        if self._isbuilt : return self
        else : self._isbuilt = True

        basepath = bld.srcnode.find_node('wscript').abspath()
        if self.source == self.target :
            Logs.error("Font source may not be the same as the target: '%s'" % self.target)
        # convert from legacy
        if hasattr(self, 'legacy') :
            self.legacy.build(bld, getattr(self, 'ap', None))

        # build font
        targetnode = bld.path.find_or_declare(self.target)
        tarname = None
        srcnode = bld.path.find_or_declare(self.source)
        if self.source.endswith(".ttf") :
            bgen = bld(rule = "${COPY} '${SRC}' '${TGT}'", source = srcnode, target = targetnode, shell=True)
        elif self.source.endswith(".ufo") and not hasattr(self, 'buildusingfontforge') :
            bgen = bld(rule = "${PSFUFO2TTF} '${SRC}' '${TGT}'", source = srcnode, target = targetnode, shell=True) 
        else :
            if getattr(self, "sfd_master", None) and self.sfd_master != self.source:
                tarname = self.source + "_"
                bld(rule = "${COPY} '${SRC}' '${TGT}'", source = srcnode, target = tarname, shell=True)
                modify("${SFDMELD} ${SRC} ${DEP} ${TGT}", tarname, [self.sfd_master], path = basepath, before = self.target + "_sfd")
            bgen = bld(rule = "${FONTFORGE} -nosplash -quiet -lang=py -c 'import sys; f=open(sys.argv[1]); f.encoding=\"Original\"; f.generate(sys.argv[2])' ${SRC} ${TGT}", source = tarname or srcnode, target = self.target, name = self.target + "_sfd") # for old fontforges
            # bgen = bld(rule = "${FONTFORGE} -quiet -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = tarname or srcnode, target = self.target, name = self.target + "_sfd")

        if hasattr(self, 'version') :
            if isinstance(self.version, (list, tuple)) :
                ttfsetverparms = "-d '" + self.version[1] + "' " + self.version[0]
            elif self.package.buildversion != '' :
                ttfsetverparms = "-d '{1}' {0}".format(str(self.version), self.package.buildversion)
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
                    bld(rule = "${SFD2AP} " + apopts + " '${SRC}' '${TGT}'", source = tarname or self.source, target = apnode)
                elif self.source.endswith(".ufo") and not os.path.exists(apnode.get_src().abspath()):
                    apopts = getattr(self, 'ap_params', "")
                    bld(rule = "${PSFEXPORTANCHORS} " + apopts + " '${SRC}' '${TGT}'", source = tarname or self.source, target = apnode)
                elif not hasattr(self.ap, 'isGenerated') and (hasattr(self, 'classes') or ismodified(self.ap, path = basepath)) :
                    origap = self.ap
                    self.ap = self.ap + ".smith"
                    bld(rule="${COPY} '${SRC}' '${TGT}'", source = origap, target = self.ap, shell=True)
            # if hasattr(self, 'classes') :
            #     modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.ap, [self.classes], shell = 1, path = basepath)
        
        # add smarts
        for x in (getattr(self, y, None) for y in ('opentype', 'graphite', 'pdf', 'woff', 'fret')) :
            if x :
                x.build(bld, self.target, bgen, self)

        if hasattr(self, 'ttfautohint'):
            modify("${TTFAUTOHINT} " + self.ttfautohint + " ${DEP} ${TGT}", self.target)

        if hasattr(self, 'typetuner') :
            modify("${TYPETUNER} -o ${TGT} add ${SRC} ${DEP}", self.target, inputs = [self.typetuner])

        return self

    def build_ots(self, bld) :
        bld(rule="${OTS} ${SRC} > /dev/null 2> ${TGT}", target=self.ots_target, source=[self.target], shell=1)

    def build_fontlint(self, bld) :
        bld(rule="${FONTLINT} ${SRC} > ${TGT} 2>&1; exit 0", target=self.fontlint_target, source=[self.target], shell=1)

    def build_fontvalidator(self, bld) :
        target = str(self.target) + ".report.xml"
        bld(rule="${FONTVALIDATOR} ${SRC}; exit 0", source=self.target, target=bld.path.find_or_declare(target), shell=1)

    def build_pyfontaine(self, bld) :
        bld(rule="${PYFONTAINE} --missing --text  ${SRC} > ${TGT} ", target=self.pyfontaine_target, source=[self.target], shell=1)


class Legacy(object) :

    def __init__(self, src, *k, **kw) :
        self.target = src
        self.params = ''
        initobj(self, kw)

    def get_build_tools(self, ctx) :
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
                cmd += " -x '${SRC[2].bldpath()}'"
            trgt = [re.sub(r'\..*', '.ttf', self.target)]
            if targetap and not hasattr(self, 'noap') :
                trgt.append(targetap)
                cmd += " -z '${TGT[1].bldpath()}'"
            bld(rule = "${TTFBUILDER} -c '${SRC[1].bldpath()}'" + cmd + " '${SRC[0].bldpath()}' '${TGT[0].bldpath()}'", source = srcs, target = trgt)
            if self.target.endswith(".sfd") :
                bld(rule = "${FONTFORGE} -nosplash -quiet -lang=ff -c 'Open($1); Save($2)' '${SRC}' '${TGT}'", source = trgt[0], target = self.target, shell = 1) # for old fontforge
                # bld(rule = "${FONTFORGE} -quiet -nosplash -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.target, shell = 1)
        else :
            bld(rule = "${FFBUILDER} -c '${SRC[1].bldpath()}'" + cmd + " '${SRC[0].bldpath()}' '${TGT[0].bldpath()}'", source = srcs, target = self.target)
            if targetap and not hasattr(self, 'noap') :
                bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.target, target = targetap)


class Internal(object) :

    def __init__(self, src = None, *k, **kw) :
        self.source = initval(src)
        self.params = ''
        initobj(self, kw)

    def get_build_tools(self, ctx) :
        return []

    def get_sources(self, ctx) :
        return []

    def build(self, bld, target, tgen, font) :
        pass

class Volt(Internal) :

    def __init__(self, source, *k, **kw) :
        super(Volt, self).__init__(source, *k, **kw)

    def get_build_tools(self, ctx) :
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
            

class Fea(Internal) :

    def __init__(self, source = None, *k, **kw) :
        self.master = ''
        self.params = ''
        super(Fea, self).__init__(source, *k, **kw)
    
    def get_build_tools(self, ctx) :
        res = ["ttftable", "fonttools"]
        if hasattr(self, 'old_make_fea'):
            res.append("make_fea")
        else:
            res.append("psfmakefea")
        return res

    def get_sources(self, ctx) :
        return get_all_sources(self, ctx, 'master')

    def build(self, bld, target, tgen, font) :
        depends = getattr(self, 'depends', [])
        def aspythonstr(s) :
            return '"' + re.sub(ur"([\\'])", ur"\\\1", s) + '"'
        def doit(src, keeps) :
            modify("${TTFTABLE} -d opentype ${DEP} ${TGT}", target)
            if hasattr(font, 'buildusingfontforge') :
                modify("${FONTFORGE} -nosplash -quiet -lang=py -c 'f=open(\"${DEP}\",32); f.encoding=\"Original\"; list(f.removeLookup(x) for x in f.gsub_lookups+f.gpos_lookups if not len(f.getLookupInfo(x)[2]) or f.getLookupInfo(x)[2][0][0] not in ["+keeps+"]); f.mergeFeature(\"${SRC}\"); f.generate(\"${TGT}\")'", target, [src], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_fea", deps = depends, shell = 1)
            else :
                modify("${FONTTOOLS} feaLib -o '${TGT}' '${SRC}' '${DEP}'", target, [src], name = font.target + "_fea", path = bld.srcnode.find_node('wscript').abspath(), deps = depends, shell = 1) 

        srcs = [font.source]
        if self.master : srcs.append(self.master)
        keeps = ''
        if hasattr(self, 'keep_feats') :
            if isinstance(self.keep_feats, basestring) :
                keeps = aspythonstr(self.keep_feats)
            else :
                keeps = ", ".join(map(aspythonstr, self.keep_lookups))
        depends = getattr(self, 'depends', [])
        use_legacy = bool(getattr(self, 'old_make_fea', False))
        if not use_legacy:
            srctarget = font.source
        if self.source is not None :
            if not hasattr(self, 'no_make') :
                srcs = []
                cmd = getattr(self, 'make_params', '') + " "
                ind = 0
                if hasattr(font, 'ap') :
                    if use_legacy:
                        srcs.append(bld.path.find_or_declare(font.ap))
                        cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                        ind += 1
                    else:
                        srctarget = font.ap
                if hasattr(font, 'classes') :
                    srcs.append(bld.path.find_or_declare(font.classes))
                    cmd += "-c ${SRC[" + str(ind) + "].bldpath()} "
                    ind += 1
                if self.master :
                    mnode = bld.path.find_or_declare(self.master)
                    srcs.append(mnode)
                    if use_legacy:
                        snode = bld.bldnode.find_or_declare(self.source)
                        loc = mnode.path_from(snode.parent)
                    else:
                        loc = mnode.bldpath()
#                    cmd += '-i ${SRC[' + str(ind) + "].bldpath()} "
                    cmd += '-i ' + loc + ' '
                    ind += 1
                if hasattr(self, 'preinclude') and use_legacy:
                    mnode = bld.path.find_or_declare(self.preinclude)
                    srcs.append(mnode)
                    snode = bld.bldnode.find_or_declare(self.source)
                    loc = mnode.path_from(snode.parent)
                    cmd += '--preinclude=' + loc + ' '
                    ind += 1
                if use_legacy:
                    bld(rule = "${MAKE_FEA} " + cmd + bld.path.find_or_declare(target).bldpath() + " ${TGT}", shell = 1, source = srcs + [target], target = self.source)
                else:
                    bld(rule = "${PSFMAKEFEA} -o ${TGT} " + cmd + " ${SRC[" + str(ind) + "]}", shell = 1, source = srcs + [srctarget], target = self.source)
                if getattr(self, 'to_ufo', False) and font.source.lower().endswith('.ufo'):
                    bld(rule = "${CP} ${SRC} ${TGT}", target = os.path.join(bld.path.find_or_declare(font.source).bldpath(), "features.fea"), source = self.source)
            doit(self.source, keeps)
        elif self.master :
            doit(self.master, keeps)


class Gdl(Internal) :

    def __init__(self, source = None, *k, **kw) :
        self.master = ''
        self.params = ''
        super(Gdl, self).__init__(source, *k, **kw)
    
    def get_build_tools(self, ctx) :
        return ("make_gdl", "grcompiler", "ttftable")

    def get_sources(self, ctx) :
        return get_all_sources(self, ctx, 'master', 'depends')

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
                    cmd += "-a '${SRC[" + str(ind) + "].bldpath()}' "
                    ind += 1
                if hasattr(font, 'classes') :
                    srcs.append(bld.path.find_or_declare(font.classes))
                    cmd += "-c '${SRC[" + str(ind) + "].bldpath()}' "
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
            modify(prevars + "${GRCOMPILER} -q " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.source], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr", deps = depends, shell = 1)
        elif self.master :
            modify(prevars + "${GRCOMPILER} -q " + self.params + " ${SRC} ${DEP} ${TGT}", target, [self.master], path = bld.srcnode.find_node('wscript').abspath(), name = font.target + "_gr", deps = depends, shell = 1)


class Ofl(object) :

    def __init__(self, *reserved, **kw) :
        if not 'version' in kw : kw['version'] = 1.1
        #if not 'copyright' in kw : kw['copyright'] = getattr(Context.g_module, 'COPYRIGHT', '')
        self.reserve = reserved
        initobj(self, kw)

    def get_build_tools(self, ctx) :
        return ["ttfname"]

    def get_sources(self, ctx) :
        return []

    def build(self, bld, font) :
        if not hasattr(self, 'copyright') :
            self.copyright = getattr(font, 'copyright', getattr(font.package, 'copyright', ''))
        modify(self.insert_ofl, font.target, path = bld.srcnode.find_node('wscript').abspath(), late = 1)
        
    def globalofl(self, task) :
        bld = task.generator.bld
        if bld.srcnode.find_node(self.file) is None :
            make_ofl(self.file, self.all_reserveds, self.version, copyright = self.copyright, template = getattr(self, 'template', None))
        return True

    def build_global(self, bld) :
        if not hasattr(self, 'file') : self.file = 'OFL.txt'
        bld(rule = self.globalofl)

    def insert_ofl(self, task) :
        bld = task.generator.bld
        tempfn = make_tempnode(bld)

        def dottfname(*opts) :
            cmd = [task.env.get_flat("TTFNAME")] + list(opts) + [task.dep.path_from(bld.bldnode), tempfn]
            task.exec_command(cmd, cwd = getattr(task, 'cwd', None), env = task.env.env or None)

        if hasattr(self, 'file') :
            f = bld.srcnode.find_node(self.file)
        else :
            f = None
        if f is not None :
            dottfname("-t", "13", "-s", f.abspath())
        elif hasattr(self, 'short') :
            licensetxt = u"This Font Software is licensed under the SIL Open Font License, Version 1.1"
            if len(self.reserve) :
                licensetxt += u" with Reserved Font Names " + " and ".join(map(lambda x: '"%s"' % x, self.reserve))
            dottfname("-t", "13", "-n", licensetxt)
        else :
            fname = make_tempnode(bld)
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
        self.target = initval(tgt)
        initobj(self, kw)

    def get_build_tools(self, ctx) :
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
        self.target = initval(tgt)
        initobj(self, kw)

    def get_build_tools(self, ctx) :
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

    def get_sources(self, ctx) :
        res = get_all_sources(self, ctx, 'config')
        return res

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

# apply defer() after subclasses declared
# The wscript that builds waf (or smith) handles decorators in a special way
#  (see process_decorators()) by removing the decorator from the code and
#  applying the decorator function at the end of the file without reassigning
#  the name to the object returned by the decorator function.
#  This works for waf's decorators but not for defer().
Internal = defer(Internal)
Volt = defer(Volt)
Fea = defer(Fea)
Gdl = defer(Gdl)
Fret = defer(Fret)
Woff = defer(Woff)
Subset = defer(Subset)

def make_tempnode(bld) :
    return os.path.join(bld.bldnode.abspath(), ".tmp", "tmp" + str(randint(0, 100000)))
    
def name(n, **kw) :
    progset.add('ttfname')
    kw['shell'] = 1
    if n is None :
        opts = "-r " + str(kw.get('string', 0)) + ' '
        def iname(tgt) :
            return ('${TTFNAME} ' + opts + "${DEP} ${TGT}", [], kw)
        return iname
    opts = " "
    if 'lang' in kw :
        opts += "-l " + kw['lang'] + " "
        del kw['lang']
    if 'string' in kw :
        opts += "-t " + str(kw['string']) + " "
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
    varmap = { 'font' : Font, 'legacy' : Legacy, 'volt' : Volt, 'fea' : Fea,
            'gdl' : Gdl, 'name' : name, 'ofl' : Ofl, 'fret' : Fret,
            'woff' : Woff, 'internal' : Internal
             }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)

