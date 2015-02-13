#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Utils
import package
import wsiwaf
import os, shutil, codecs
from functools import partial

globaltest = None
def global_test() :
    global globaltest
    if not globaltest :
        globaltest = font_test()
    return globaltest

def copy_task(task) :
    shutil.copy(task.inputs[0].srcpath(), task.outputs[0].srcpath())
    return 0

def curry_fn(fn, *parms, **kw) :
    def res(*args) :
        return fn(*(parms + args), **kw)
    return res

def antlist(ctx, testdir, globs) :
    if isinstance(globs, basestring) :
        globs = [globs]
    found = ctx.path.find_node(testdir)
    if found : return found.ant_glob(globs)
    return []

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

def initdefaults(self, ctx, **info) :
    for k, v in info.items() :
        if not hasattr(self, k) :
            if v[0] not in ctx.env :
                setattr(self, k, v[1])
            else :
                setattr(self, k, ctx.env[v[0]])
    

class font_test(object) :
    tests = []

    def __init__(self, *kv, **kw) :
        if 'htexts' not in kw : kw['htexts'] = '*.htxt'
        if 'texts' not in kw : kw['texts'] = '*.txt'
        if 'targets' not in kw : kw['targets'] = {  'pdfs' : TeX(),
                                                    'svg' : SVG(),
                                                    'xfont' : CrossFont(),
                                                    'test' : Tests(),
                                                    'waterfall' : Waterfall(),
                    'xtest' : Tests({'cross' : wsiwaf.cmd('cmptxtrender -p -k -e ${shaper} -s "${script}" -e ${altshaper} -L ${shaper} -L ${altshaper} -t ${SRC[1]} -o ${TGT} --copy=fonts --strip ${fileinfo} ${SRC[0]} ${SRC[0]}')}, coverage='shaperpairs') }
        if 'extras' in kw : kw['targets'].update(kw['extras'])
        for k, item in kw.items() :
            setattr(self, k, item)

        for t in self.targets.keys() :
            c = type(t + 'Context', (package.cmdContext,), {'cmd' : t, '__doc__' : "User defined test: " + t})
        self.tests.append(self)
        self._hasinit = False

    def config(self, ctx) :
        res = set(['perl'])
        for t in self.targets.values() :
            res.update(t.config(ctx))
        return res

    def get_sources(self, ctx, font) :
        if not hasattr(self, 'testdir') :
            self.testdir = ctx.env['TESTDIR'] or 'tests'
        testsdir = self.testdir + os.sep
        res = []
        for s in (getattr(self, y, None) for y in ('texts', 'htexts', 'texs')) :
            if s :
                res.extend(antlist(ctx, testsdir, s))
        for s in self.targets.values() :
            res.extend(s.get_sources(ctx, font))
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
        lookups = {
            'text' : ('TESTSTRING', ''),
            'size' : ('TESTFONTSIZE', 12),
            'waterfallsizes' : ('WATERFALLSIZES', [6, 8, 9, 10, 11, 12, 13, 14, 16, 18, 22, 24, 28, 32, 36, 42, 48, 56, 72]),
            'waterfalldir' : ('WATERFALLDIR', 'waterfall')
        }
        initdefaults(self, ctx, testdir = ('TESTDIR', 'tests'), resultsdir = ('TESTRESULTSDIR', None))
        self.testnode = ctx.path.find_node(self.testdir)
        if self.resultsdir is None :
            self.resultsdir = self.testdir
            self.resultsnode = self.testnode.get_bld()
        else :
            self.resultsnode = ctx.bldnode.find_or_declare(self.resultsdir)
        
        testsdir = self.testdir + os.sep
        if not self._hasinit : self.build_testfiles(ctx, testsdir)

        self.modes = {}
        if getattr(font, 'graphite', None) :
            self.modes['gr'] = "/GR"
        if getattr(font, 'sfd_master', None) or getattr(font, 'opentype', None) :
            t = "/ICU"
            scr = getattr(font, 'script', None)
            if isinstance(scr, basestring) :
                self.modes['ot'] = t + ":script=" + scr
            elif scr :
                for s in scr :
                    self.modes['ot_' + s] = t + ':script=' + s
            else :
                self.modes['ot'] = t
        self.targets[target].build(ctx, self, font)

    def results_node(self, node) :
        if node.is_bld() : return node
        path = node.path_from(self.testnode)
        return self.resultsnode.make_node(path)

class TeX(object) :

    def __init__(self, *kv, **kw) :
        if 'texs' not in kw : kw['texs'] = '*.tex'
        if 'htexs' not in kw : kw['htexs'] = '*.htex'
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
        return set()

    def get_sources(self, ctx, font) :
        return []

    def make_tex(self, mf, font, test, task) :
        texdat = r'''
\font\test="[./%s]%s" at 12pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{\hskip0pt\relax}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{\shipout\vbox{\makeheadline\pagebody\makefootline}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}
\obeylines
\everypar{\global\advance\count0by1\llap{\tt\the\count0\quad}}
\test
\input ./%s
\bye
''' % (font, mf, task.inputs[0].bldpath())
        task.outputs[0].write(texdat)
        return 0

    def make_from_htex(self, mf, font, test, task) :
        texdat = r'''
\def\buildfont{"[%s]%s"}
\input %s
\bye
''' % (font, mf, task.inputs[0].bldpath())
        task.outputs[0].write(texdat)
        return 0
    
    def build_maketexfiles(self, ctx, test, font, n, fid, fn, txtfiles = dict(), folder='') :
        textfiles = []
        for m, mf in test.modes.items() :
            if not isinstance(n, basestring) :
                nfile = os.path.split(n.bld_base())[1]
                parts = nfile.partition('_')
                attrs = txtfiles.get(n, None)
                if attrs :
                    if isinstance(attrs, dict) :
                        attrs = "&".join(map(lambda x,y : x+"="+y, attrs.items()))
                    mf += ":" + attrs.replace('lang=', 'language=').replace('&', ':')
                elif parts[1] and len(parts[0]) < 5 :
                    lang = parts[0]
                    mf += ":language=" + lang
                else :
                    lang = None

            if isinstance(n, basestring) :
                newn = ctx.path.find_or_declare(os.path.join(test.resultsdir, folder, n))
            else :
                newn = n
            targfile = test.results_node(newn).bld_base() + '_' + fid + "_" + m + ".tex"
            targ = ctx.path.find_or_declare(targfile)
            if isinstance(n, basestring) :
                ctx(rule = curry_fn(fn, mf, font.target, test), target = targ)
            else :
                ctx(rule = curry_fn(fn, mf, font.target, test), source = n, target = targ)
            textfiles.append((targ, n))
        return textfiles

    def build_dotexfiles(self, ctx, font, files) :
        for n in files :
            targ = n[0].get_bld()
            mindex = str(n[0]).rindex('.')
            mode = str(n[0])[mindex-2:mindex]
            ctx(rule = '${XETEX} --interaction=batchmode --output-directory=./' + targ.bld_dir() + ' ./${SRC[0].bldpath()}',
    #            ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}',
                source = [n[0], font.target], target = targ.change_ext('.pdf'),
                taskgens = [font.target + "_" + mode])
    #                ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))

    def build(self, ctx, test, font) :
        if 'XETEX' not in ctx.env : return
        fid = getattr(font, 'test_suffix', font.id)
        testsdir = test.testdir + os.sep
        self._texfiles = antlist(ctx, testsdir, self.texs)
        self._htexfiles = antdict(ctx, testsdir, self.htexs)

        if hasattr(self, 'files') :
            txtfiles = antdict(ctx, testsdir, self.files)
        else :
            txtfiles = dict.fromkeys(test._txtfiles + test._htxttfiles)
        textfiles = []
        for n in txtfiles.keys() :
            textfiles.extend(self.build_maketexfiles(ctx, test, font, n, fid, self.make_tex, txtfiles))
        for n in self._htexfiles.keys() :
            textfiles.extend(self.build_maketexfiles(ctx, test, font, n, fid, self.make_from_htex, txtfiles))

        for n in self._texfiles :
            targfile = test.results_node(n).bld_base() + '_' + fid + ".tex"
            targ = ctx.path.find_or_declare(targfile)
            ctx(rule = copy_task, source = n, target = targ)
            textfiles.append((targ, n))
        self.build_dotexfiles(ctx, font, textfiles)

class Waterfall(TeX) :

    def __init__(self, *kv, **kw) :
        if 'featstr' not in kw : kw['featstr'] = ''
        else : kw['featstr'] = ':' + kw['featstr']
        if 'name' not in kw : kw['name'] = 'waterfall'
        for k, item in kw.items() :
            setattr(self, k, item)
        self._configured = False

    def make_waterfall(self, mf, font, test, task) :
        texdat = ur'''
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{\hskip0pt\relax}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{\shipout\vbox{\makeheadline\pagebody\makefootline}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}
'''
        for s in self.sizes :
            texdat += r'''
\font\test="[./%s]%s%s" at %d pt \baselineskip=%d pt
\noindent\test %s
\par
''' % (font, mf, self.featstr, s, s * self.sizefactor, self.text)

        texdat += ur'''
\bye
'''
        task.outputs[0].write(texdat.encode('utf-8'))
        return 0

    def build(self, ctx, test, font) :
        if 'XETEX' not in ctx.env : return
        initdefaults(self, ctx, text = ('TESTSTRING', ''), waterfalldir = ('WATERFALLDIR', 'waterfall'),
                        sizes = ('WATERFALLSIZES', [6, 8, 9, 10, 11, 12, 13, 14, 16, 18, 22, 24, 28, 32, 36, 42, 48, 56, 72]),
                        sizefactor = ('TESTLINESPACINGFACTOR', 1.2))
        fid = getattr(font, 'test_suffix', font.id)
        testsdir = test.testdir + os.sep

        textfiles = self.build_maketexfiles(ctx, test, font, self.name, fid, self.make_waterfall, folder=self.waterfalldir)
        self.build_dotexfiles(ctx, font, textfiles)


class CrossFont(object) :

    def __init__(self, *kv, **kw) :
        if 'featstr' not in kw : kw['featstr'] = ''
        else : kw['featstr'] = ':' + kw['featstr']
        if 'file' not in kw : kw['file'] = 'CrossFont'
        for k, item in kw.items() :
            setattr(self, k, item)
        self._configured = False
        self._tasks = None
        self._fonts = []

    def config(self, ctx) :
        if self._configured : return []
        self._configured = True
        try :
            ctx.find_program('xetex')
        except ctx.errors.ConfigurationError :
            pass
        return set()

    def get_sources(self, ctx, font) :
        return []

    def do_task(self, mf, task) :
        texdat = ur'''
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{\hskip0pt\relax}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{\shipout\vbox{\makeheadline\pagebody\makefootline}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}
'''
        for f in self._fonts :
            texdat += ur'''
\font\test="[./%s]%s%s" at %d pt
\noindent\hbox to 2in {\vbox{\hsize=2in\noindent \rm %s}}
\test %s
\par
''' % (f, mf, self.featstr, self.size, f, self.text)
        texdat += ur'''
\bye
'''
        task.outputs[0].write(texdat.encode('utf-8'))
        return task.exec_command([task.env['XETEX'], '--interaction=batchmode',
                                '--output-directory=./' + task.outputs[0].bld_dir(), task.outputs[0].bldpath()])

    def build(self, ctx, test, font) :
        if 'XETEX' not in ctx.env : return
        initdefaults(self, ctx, text = ('TESTSTRING', ''), size = ('TESTFONTSIZE', 12))
        self._fonts.append(font.target)
        if self._tasks is None :
            self._tasks = {}
            for m, mf in test.modes.items() :
                self._tasks[m] = ctx(rule = curry_fn(self.do_task, mf), target=test.resultsnode.make_node(self.file + '_' + m + '.tex'))


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
        return set()

    def get_sources(self, ctx, font) :
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
                    if isinstance(txtfiles[n], dict) : lang = "&".join(map(lambda x,y : x+"="+y, txtfiles[n].items()))
                    else : lang = txtfiles[n]
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
    def __init__(self, tests = None, *kv, **kw) :
        if 'ext' not in kw : kw['ext'] = '.html'
        if 'coverage' not in kw : kw['coverage'] = 'textshaper'
        self._extracmds = []
        for k, item in kw.items() :
            setattr(self, k, item)
        if not tests :
            tests = {'regression' : wsiwaf.cmd('${CMPTXTRENDER} -p -k -e ${shaper} -s "${script}" -l "${lang}" -t ${SRC[1]} -L test -L standard -o ${TGT} --copy fonts_${shaper} --strip ${fileinfo} ${SRC[0]} ${SRC[2]}')}
            self._extracmds += ['cmptxtrender']
        self.tests = tests

    def config(self, ctx) :
        return set(self._extracmds)

    def get_sources(self, ctx, font) :
        std = getattr(self, 'standards', ctx.env['STANDARDS'] or 'standards')
        f = os.path.basename(font.target)
        return [os.path.join(std, f)]

    def build(self, ctx, test, font) :
        if not hasattr(self, 'standards') :
            self.standards = ctx.env['STANDARDS'] or 'standards'
        if hasattr(self, 'files') :
            testsdir = test.testdir + os.sep
            txtfiles = antdict(ctx, testsdir, self.files)
        else :
            txtfiles = dict.fromkeys(test._txtfiles + test._htxttfiles)

        for name, t in self.tests.items() :
            f = os.path.basename(font.target)
            if self.coverage == 'fonts' :
                target = os.path.join(test.resultsdir, name, os.path.splitext(f)[0] + self.ext)
                self.dotest(t, ctx, font, None, None, target, name = name)
            elif self.coverage == 'shapers' :
                for m in test.modes.keys() :
                    shp = m[0:m.find("_")] if "_" in m else m
                    if hasattr(self, 'shapermap') : shp = self.shapermap(shp)
                    target = os.path.join(test.resultsdir, name, os.path.splitext(f)[0] + '_' + m + self.ext)
                    self.dotest(t, ctx, font, None, m, target, shaper = shp, name = name, script = None)
            else :
                for n in txtfiles.keys() :
                    ns = str(n)
                    if txtfiles[n] :
                        if isinstance(txtfiles[n], dict) : tinfo = txtfiles[n]
                        else : tinfo = self.parse_txtfile(txtfiles[n])
                    elif "_" in ns[:6] :
                        tinfo = {"lang" : ns[:ns.find("_")]}
                    else :
                        tinfo = {}
                    seen = set()
                    for m in test.modes.keys() :
                        shp = m[0:m.find("_")] if "_" in m else m
                        if hasattr(self, 'shapermap') : shp = self.shapermap(shp)
                        target = os.path.join(test.resultsdir, name, os.path.splitext(os.path.basename(n.bldpath()))[0] + "_" + os.path.splitext(f)[0] + '_' + m)
                        if self.coverage == 'textshaper' :
                            self.dotest(t, ctx, font, n, m, target + self.ext,
                                                shaper = shp,
                                                script = tinfo.get('script', None),
                                                name = name,
                                                lang = tinfo.get('lang', None),
                                                fileinfo = tinfo.get('extra', None))
                        elif self.coverage == 'shaperpairs' :
                            seen.add(m)
                            for q in test.modes.keys() :
                                if q in seen : continue
                                if q.startswith('ot') and m.startswith('ot') : continue
                                ashp = q[0:q.find("_")] if "_" in q else q
                                if hasattr(self, 'shapermap') : ashp = self.shapermap(ashp)
                                self.dotest(t, ctx, font, n, m, target + "_" + q + self.ext,
                                                shaper = shp,
                                                script = tinfo.get('script', None) if "_" not in q else q[q.find("_")+1:],
                                                name = name,
                                                lang = tinfo.get('lang', None),
                                                altshaper = ashp,
                                                fileinfo = tinfo.get('extra', None))

    def dotest(self, test, ctx, font, txtname, mode, target, **kws) :
        f = os.path.basename(font.target)
        inputs = [font.target]
        if txtname : inputs.append(txtname)
        std = os.path.join(self.standards, f)
        if os.path.exists(std) : inputs.append(std)
        if mode and mode.startswith("ot") :
            scr = getattr(font, 'script', [None])
            if isinstance(scr, basestring) : scr = [scr]
            for s in scr :
                if len(scr) > 1 :
                    dotindex = target.rfind(".")
                    targ = target[0:dotindex] + "_" + s + target[dotindex:]
                else :
                    targ = target
                olds = kws.get('script', None)
                if not olds : kws['script'] = s
                gen = test.build(ctx, inputs, targ, **kws)
                gen.taskgens = [font.target + "_" + mode]
                kws['script'] = olds
        else :
            gen = test.build(ctx, inputs, target, **kws)
            gen.taskgens = [font.target + "_" + mode] if mode else [font.target]

    def parse_txtfile(self, txt) :
        res = {}
        for i in txt.split('&') :
            (k, v) = i.split('=')
            res[k.strip()] = v.strip()
        return res
