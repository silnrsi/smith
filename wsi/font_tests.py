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

def configure_tests(ctx, font) :
    res = set(['xetex', 'grsvg', 'firefox', 'xdvipdfmx', 'xsltproc', 'firefox'])
    return res

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

class font_test(object) :
    tests = []

    def __init__(self, *kv, **kw) :
        if 'htexts' not in kw : kw['htexts'] = '*.htxt'
        if 'texts' not in kw : kw['texts'] = '*.txt'
        if 'texs' not in kw : kw['texs'] = '*.tex'
        
        for k, item in kw.items() :
            setattr(self, k, item)

        self.tests.append(self)
        self._hasinit = False

    def build_testfiles(self, ctx, testsdir) :
        self._hasinit = True

        # make list of source tests to run against fonts, build if necessary
        self._txtfiles = antlist(ctx, testsdir, self.texts)
        self._texfiles = antlist(ctx, testsdir, self.texs)
        self._htxtfiles = antlist(ctx, testsdir, self.htexts)
        self._htxttfiles = []

        for n in self._htxtfiles :
            targ = n.get_bld().change_ext('.txt')
            ctx(rule=r"perl -CSD -pe 's{\\[uU]([0-9A-Fa-f]+)}{pack(qq/U/, hex($1))}oge' ${SRC} > ${TGT}", shell = 1, source = n, target = targ)
            self._htxttfiles.append(targ)

    def build_tests(self, ctx, font, target) :
        if not hasattr(self, 'testdir') :
            self.testdir = ctx.env['TESTDIR'] or 'tests'
        testsdir = self.testdir + os.sep
        if not self._hasinit : self.build_testfiles(ctx, testsdir)
        fid = getattr(font, 'test_suffix', font.id)

        modes = {}
        textfiles = []
        if getattr(font, 'graphite', None) :
            modes['gr'] = "/GR"
        if getattr(font, 'sfd_master', None) or getattr(font, 'opentype', None) :
            t = "/ICU"
            if getattr(font, 'script', None) :
                t += ":script=" + font.script
            modes['ot'] = t
        for n in self._txtfiles + self._htxttfiles :
            for m, mf in modes.items() :
                nfile = os.path.split(n.bld_base())[1]
                parts = nfile.partition('_')[0]
                if parts[1] and len(parts[0]) < 5 :
                    lang = parts[0]
                    mf += ":language=" + lang
                else :
                    lang = None

                if target == "pdfs" or target == 'test' :
                    targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + "_" + m + ".tex"
                    targ = ctx.path.find_or_declare(targfile)
                    ctx(rule = curry_tex(make_tex, mf, font.target), source = n, target = targ)
                    textfiles.append((targ, n))

                elif target == 'svg' :
                    if m == 'gr' :
                        rend = 'graphite'
                    else :
                        rend = 'icu'
                    if lang :
                        rend += " --feat lang=" + lang
                    targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + "_" + m + '.svg'
                    ctx(rule='${GRSVG} ' + font.target + ' -i ${SRC} -o ${TGT} --renderer ' + rend + ' ' + getattr(self, 'grsvg_params', ''), source = n, target = targfile)

        if target == 'pdfs' or target == 'test' :
            for n in self._texfiles :
                targfile = n.get_bld().bld_base() + os.path.splitext(fid)[0] + ".tex"
                targ = ctx.path.find_or_declare(targfile)
                ctx(rule = copy_task, source = n, target = targ)
                textfiles.append((targ, n))
            for n in textfiles :
                targ = n[0].get_bld()
                ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}',
                    source = n[0], target = targ.change_ext('.xdv'),
                    taskgens = [font.target + "_" + m])
                if target == 'pdfs' :
                    ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))


