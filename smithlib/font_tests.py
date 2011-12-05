#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Utils
import os, shutil, codecs
from functools import partial

globaltest = None
def global_test() :
    global globaltest
    if not globaltest :
        globaltest = font_test()
    return globaltest

def make_tex(mf, font, task) :
    texdat = r'''
\font\test="[%s]%s" at 12pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\obeylines
\test
\input %s
\bye
''' % (font, mf, task.inputs[0].bldpath())
    task.outputs[0].write(texdat)
    return 0
    
def copy_task(task) :
    shutil.copy(task.inputs[0].bldpath(), task.outputs[0].bldpath())
    return 0

def curry_fn(fn, *parms, **kw) :
    def res(*args) :
        return fn(*(parms + args), **kw)
    return res

def antlist(ctx, testdir, globs) :
    if isinstance(globs, basestring) :
        globs = [globs]
    return ctx.srcnode.find_node(testdir).ant_glob(globs)

def antdict(ctx, testdir, globs) :
    if isinstance(globs, basestring) :
        globs = {globs : None}
    elif isinstance(globs, list) or isinstance(globs, tuple) :
        globs = dict.fromkeys(globs)
    res = {}
    for f, v in globs.items() :
        for n in ctx.path.ant_glob(testdir + f) :
            res[n] = v
    return res


class font_test(object) :
    tests = []

    def __init__(self, *kv, **kw) :
        if 'htexts' not in kw : kw['htexts'] = '*.htxt'
        if 'texts' not in kw : kw['texts'] = '*.txt'
        if 'targets' not in kw : kw['targets'] = { 'pdfs' : TeX(), 'svg' : SVG() }
        for k, item in kw.items() :
            setattr(self, k, item)

        self.tests.append(self)
        self._hasinit = False

    def config(self, ctx) :
        res = set(['perl'])
        for t in self.targets.values() :
            res.update(t.config(ctx))
        return res

    def get_sources(self, ctx) :
        if not hasattr(self, 'testdir') :
            self.testdir = ctx.env['TESTDIR'] or 'tests'
        testsdir = self.testdir + os.sep
        res = []
        for s in (getattr(self, y, None) for y in ('texts', 'htexts', 'texs')) :
            if s :
                res.extend(antlist(ctx, testsdir, s))
        return res
        
    def build_testfiles(self, ctx, testsdir) :
        self._hasinit = True

        # make list of source tests to run against fonts, build if necessary
        self._txtfiles = antlist(ctx, testsdir, self.texts)
        self._htxtfiles = antlist(ctx, testsdir, self.htexts)
        self._htxttfiles = []

        for n in self._htxtfiles :
            targ = ctx.bldnode.make_node(os.path.splitext(self.results_node(n).bldpath())[0] + '.txt')
            ctx(rule=r"perl -CSD -pe 's{\\[uU]([0-9A-Fa-f]+)}{pack(qq/U/, hex($1))}oge' ${SRC} > ${TGT}", shell = 1, source = n, target = targ)
            self._htxttfiles.append(targ)

    def build_tests(self, ctx, font, target) :
        if not target in self.targets : return
        if not hasattr(self, 'testdir') :
            self.testdir = ctx.env['TESTDIR'] or 'tests'
        self.testnode = ctx.path.find_node(self.testdir)
        if hasattr(self, 'resultsdir') :
            self.resultsnode = ctx.bldnode.find_node(self.resultsdir)
        elif ctx.env['TESTRESULTSDIR'] :
            self.resultsdir = ctx.env['TESTRESULTSDIR']
            self.resultsnode = ctx.bldnode.find_or_declare(self.resultsdir)
        else :
            self.resultsnode = self.testnode.get_bld()
        
        testsdir = self.testdir + os.sep
        if not self._hasinit : self.build_testfiles(ctx, testsdir)
        fid = getattr(font, 'test_suffix', font.id)

        self.modes = {}
        if getattr(font, 'graphite', None) :
            self.modes['gr'] = "/GR"
        if getattr(font, 'sfd_master', None) or getattr(font, 'opentype', None) :
            t = "/ICU"
            if getattr(font, 'script', None) :
                t += ":script=" + font.script
            self.modes['ot'] = t
        self.targets[target].build(ctx, self, font)

    def results_node(self, node) :
        path = node.path_from(self.testnode)
        return self.resultsnode.make_node(path)

class TeX(object) :

    def __init__(self, *kv, **kw) :
        if 'texs' not in kw : kw['texs'] = '*.tex'
        for k, item in kw.items() :
            setattr(self, k, item)
        self._configured = False

    def config(self, ctx) :
        if self._configured : return []
        self._configured = True
        try :
            ctx.find_program('xetex')
        except ctx.errors.ConfigurationError :
            pass
        return []

    def build(self, ctx, test, font) :
        if 'XETEX' not in ctx.env : return
        testsdir = test.testdir + os.sep
        self._texfiles = antlist(ctx, testsdir, self.texs)
        fid = getattr(font, 'test_suffix', font.id)

        if hasattr(self, 'files') :
            txtfiles = antdict(ctx, testsdir, self.files)
        else :
            txtfiles = dict.fromkeys(test._txtfiles + test._htxttfiles)
        textfiles = []
        for n in txtfiles.keys() :
            for m, mf in test.modes.items() :
                nfile = os.path.split(n.bld_base())[1]
                parts = nfile.partition('_')
                if txtfiles[n] :
                    mf += ":" + txtfiles[n].replace('lang=', 'language=').replace('&', ':')
                elif parts[1] and len(parts[0]) < 5 :
                    lang = parts[0]
                    mf += ":language=" + lang
                else :
                    lang = None

                targfile = test.results_node(n.get_src()).bld_base() + '_' + fid + "_" + m + ".tex"
                targ = ctx.path.find_or_declare(targfile)
                ctx(rule = curry_fn(make_tex, mf, font.target), source = n, target = targ)
                textfiles.append((targ, n))

        for n in self._texfiles :
            targfile = test.results_node(n).bld_base() + '_' + fid + ".tex"
            targ = ctx.path.find_or_declare(targfile)
            ctx(rule = copy_task, source = n, target = targ)
            textfiles.append((targ, n))
        for n in textfiles :
            targ = n[0].get_bld()
            ctx(rule = '${XETEX} --interaction=batchmode --output-directory=' + targ.bld_dir() + ' ${SRC[0].bldpath()}',
#            ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}',
                source = [n[0], font.target], target = targ.change_ext('.pdf'),
                taskgens = [font.target + "_" + m])
#                ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))


def make_diffHtml(targfile, svgDiffXsl, svgLinesPerPage, fid, tsk) :
    textFile = codecs.open(tsk.inputs[0].abspath(), 'r', encoding="utf8")
    lineCount = len(textFile.readlines())
    textFile.close()
    pageCount = (lineCount / svgLinesPerPage) + 1
    n = tsk.outputs[0].change_ext('')
    bld = tsk.generator.bld

    svgDiffHtml = ("<html><head><title>" + str(n) + ' ' + fid + "</title>\n" +
        "<style type='text/css'> object { vertical-align: top; margin: 2px; min-width: 120px; }</style></head><body>\n")
    for svgPage in range(1, pageCount + 1) :
        target = bld.bldnode.make_node(targfile + '{0:02d}diff.svg'.format(svgPage))
        tsk.exec_command([tsk.env['XSLTPROC'], '-o', target.bldpath(), '--stringparam', 'origSvg',
                'file:' + bld.bldnode.make_node(targfile + '_gr{0:02d}.svg'.format(svgPage)).abspath(),
                svgDiffXsl, bld.bldnode.make_node(targfile + '_ot{0:02d}.svg'.format(svgPage)).bldpath()], cwd = getattr(tsk, 'cwd', None))
        svgDiffHtml += "<object data='../" + target.bldpath() +"' title='" + str(svgLinesPerPage * svgPage) +"'></object>\n"
    svgDiffHtml += "</body></html>"
    tsk.outputs[0].write(svgDiffHtml)


class SVG(object) :

    def __init__(self, *kv, **kw) :
        for k, item in kw.items() :
            setattr(self, k, item)
        self._configured = False

    def config(self, ctx) :
        if self._configured : return []
        self._configured = True
        try :
            ctx.find_program('grsvg')
            ctx.find_program('xsltproc')
            ctx.find_program('firefox')
        except ctx.errors.ConfigurationError :
            pass
        return []

    def build(self, ctx, test, font) :
        if 'GRSVG' not in ctx.env : return
        svgLinesPerPage = getattr(self, 'lines_per_page', 50)
        # TODO find a better way to do find this
        svgDiffXsl = getattr(self, 'diff_xsl', os.path.join(os.sep + 'usr','local', 'share', 'graphitesvg', 'diffSvg.xsl'))
        if not os.path.exists(svgDiffXsl) :
            svgDiffXsl = os.path.join(os.sep + 'usr', 'share', 'graphitesvg', 'diffSvg.xsl')

        testsdir = test.testdir + os.sep
        fid = getattr(font, 'test_suffix', font.id)

        if hasattr(self, 'files') :
            txtfiles = antdict(ctx, testsdir, self.files)
        else :
            txtfiles = dict.fromkeys(test._txtfiles + test._htxttfiles)

        if not hasattr(self, 'html') :
            self.html = os.path.join(test.testdir, 'svgdiff.html')

        if not hasattr(self, 'diffs') :
            self.diffs = len(test.modes) > 1
        diffSvgs = []
        svgIndexHtml = ("<html><head><title>" + str(font.id) + "</title>\n" +
                        "</head><body><h1>" + str(font.id) + "</h1>\n")
        for n in txtfiles.keys() :
            for m, mf in test.modes.items() :
                nfile = os.path.split(n.bld_base())[1]
                parts = nfile.partition('_')
                if txtfiles[n] :
                    lang = txtfiles[n]
                elif parts[1] and len(parts[0]) < 5 :
                    lang = 'lang=' + parts[0]
                else :
                    lang = None

                if m == 'gr' :
                    rend = getattr(self, 'grsvg_gr', 'graphite2')
                else :
                    rend = getattr(self, 'grsvg_ot', 'harfbuzzng')
#                    rend = 'icu'
                if (lang and len(lang) > 0 and len(lang) < 4):
                    rend += " --feat " + lang + " "
                targfile = test.results_node(n.get_src()).bld_base() + '_' + fid + "_" + m
                ntarg = os.path.split(targfile)
                targfile = os.path.join(ntarg[0], nfile, ntarg[1])
                ctx(rule='${GRSVG} ' + font.target + ' -p 24 -i ${SRC} -o ' + targfile +
                        ' --page ' + str(svgLinesPerPage) + ' --renderer ' + rend + ' ',
                        source = n, target = targfile + ".html")
            if self.diffs and 'XSLTPROC' in ctx.env :
                targ = test.results_node(n.get_src()).bld_base() + '_' + fid
                ntarg = os.path.split(targ)
                targtfile = os.path.join(ntarg[0], nfile, ntarg[1])
                ctx(rule = curry_fn(make_diffHtml, targtfile, svgDiffXsl, svgLinesPerPage, fid), source = [n, targfile + '.html'], target = targ + 'diff.html')
                diffSvgs.append(targ + "diff.html")
                svgIndexHtml += "<a href='../" + targ + "diff.html'>" + str(n) + "</a><br />\n";
        if self.diffs and 'FIREFOX' in ctx.env :
            svgIndexHtml += "</body></html>"
            namebits = os.path.splitext(self.html)
            indexhtmltarg = "".join([namebits[0], '_', fid, namebits[1]])
            ctx.bldnode.find_or_declare(indexhtmltarg).write(svgIndexHtml)
            ctx(rule='${FIREFOX} ' + indexhtmltarg, source = diffSvgs)

class Tests(object) :
    def __init__(self, tests, *kv, **kw) :
        for k, item in kw.items() :
            setattr(self, k, item)
        self.tests = tests

    def config(self, ctx) :
        return []

    def build(self, ctx, test, font) :
        if not hasattr(self, 'standards') :
            self.standards = ctx.env['STANDARDS'] or 'standards'
        if hasattr(self, 'files') :
            txtfiles = antdict(ctx, testsdir, self.files)
        else :
            txtfiles = dict.fromkeys(test._txtfiles + test._htxttfiles)

        for name, t in self.tests.items() :
            for n in txtfiles.keys() :
                for m in test.modes.keys() :
                    f = os.path.basename(font.target)
                    inputs = [font.target, n]
                    inputs.append(os.path.join(self.standards, f))
                    target = os.path.join(test.testdir, name, os.path.splitext(os.path.basename(n.bldpath()))[0] + "_" + os.path.splitext(f)[0] + '_' + m + '.log')
                    gen = t.build(ctx, inputs, target, shaper = m, script = getattr(font, 'script', None), name = name, fileinfo = txtfiles[n])
                    gen.taskgens = [font.target + "_" + m]
