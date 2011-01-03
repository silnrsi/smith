#!/usr/bin/python

from waflib import Context, Utils
import os, shutil
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

def curry_tex(fn, *parms) :
    def res(*args) :
        return fn(*(parms + args))
    return res

def antlist(ctx, testdir, globs) :
    if isinstance(globs, basestring) :
        globs = [globs]
    res = []
    for f in globs :
        res.extend(ctx.path.ant_glob(testdir + f))
    return res

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

    def build_testfiles(self, ctx, testsdir) :
        self._hasinit = True

        # make list of source tests to run against fonts, build if necessary
        self._txtfiles = antlist(ctx, testsdir, self.texts)
        self._htxtfiles = antlist(ctx, testsdir, self.htexts)
        self._htxttfiles = []

        for n in self._htxtfiles :
            targ = n.get_bld().change_ext('.txt')
            ctx(rule=r"perl -CSD -pe 's{\\[uU]([0-9A-Fa-f]+)}{pack(qq/U/, hex($1))}oge' ${SRC} > ${TGT}", shell = 1, source = n, target = targ)
            self._htxttfiles.append(targ)

    def build_tests(self, ctx, font, target) :
        if not target in self.targets : return
        if not hasattr(self, 'testdir') :
            self.testdir = ctx.env['TESTDIR'] or 'tests'
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

        txtfiles = antdict(ctx, testsdir, getattr(self, 'files', test._txtfiles + test._htxttfiles))
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

                targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + "_" + m + ".tex"
                targ = ctx.path.find_or_declare(targfile)
                ctx(rule = curry_tex(make_tex, mf, font.target), source = n, target = targ)
                textfiles.append((targ, n))

        for n in self._texfiles :
            targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + ".tex"
            targ = ctx.path.find_or_declare(targfile)
            ctx(rule = copy_task, source = n, target = targ)
            textfiles.append((targ, n))
        for n in textfiles :
            targ = n[0].get_bld()
            ctx(rule = '${XETEX} --output-directory=' + targ.bld_dir() + ' ${SRC}',
#            ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}',
                source = n[0], target = targ.change_ext('.pdf'),
                taskgens = [font.target + "_" + m])
#                ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))


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
        except ctx.errors.ConfigurationError :
            pass
        return []

    def build(self, ctx, test, font) :
        if 'GRSVG' not in ctx.env : return
        testsdir = test.testdir + os.sep
        fid = getattr(font, 'test_suffix', font.id)

        txtfiles = antdict(ctx, testsdir, getattr(self, 'files', test._txtfiles + test._htxttfiles))
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
                    rend = 'graphite'
                else :
                    rend = 'icu'
                if lang :
                    rend += " --feat " + lang
                targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + "_" + m + '.svg'
                ctx(rule='${GRSVG} ' + font.target + ' -i ${SRC} -o ${TGT} --renderer ' + rend + ' ' + getattr(self, 'params', ''), source = n, target = targfile)

