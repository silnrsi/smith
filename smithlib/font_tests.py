#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Utils, Node, Errors, Logs
import package, templates
import wsiwaf
import os, shutil, codecs, re
from functools import partial
from itertools import combinations
import time

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

def node_from(n, oldp, newp, newext) :
    p = n.path_from(oldp)
    k = p.rfind('.')
    if k >= 0 : p = p[:k] + newext
    else : p += newext
    return newp.find_or_declare(p)

def initdefaults(self, ctx, **info) :
    for k, v in info.items() :
        if not hasattr(self, k) :
            setattr(self, k, ctx.env[v[0]] or v[1])

def texprotect(s) :
    return re.sub(ur'([_&])', ur'\\\1', s)


class FontGroup(list) :
    """ An attributed list with such interesting elements as: graphite, opentype, script, name
        We want the ordered nature of the list """

    def __init__(self, name) :
        super(FontGroup, self).__init__(self)
        self.id = name
        self.script = set()

    def __hash__(self) : return hash(self.id)

    def append(self, font) :
        """Add font if not present and analyse to set fontgroup flags and lists"""
        if hasattr(font, 'graphite') : self.graphite = True
        if hasattr(font, 'opentype') : self.opentype = True
        if hasattr(font, 'script') : self.script.update(font.script)
        super(FontGroup, self).append(font)

def strsToDicts(aDict) :
    if aDict is None : return None
    for k, v in aDict.items() :
        if isinstance(v, basestring) :
            newv = {}
            for s in v.split(';') :
                sk, sv = s.split('=', 1)
                newv[sk.trim()] = sv.trim()
            aDict[k] = v
    return aDict

class FontTests(object) :
    testMap = {}

    @classmethod
    def aTestCommand(this, cls) :
        this.testMap[cls._type] = cls
        return cls

    def addFontToGroup(self, font, name, once = False) :
        """Adds a font to the given group by name"""
        if name not in self._allFontGroups :
            fg = FontGroup(name)
            self._allFontGroups[name] = fg
        else :
            fg = self._allFontGroups[name]
        if font is not None and (not once or font not in fg) :
            fg.append(font)
        return fg

    def __init__(self, testfiles = None) :
        self._allFontGroups = {}
        self._allTests = {}
        self._testfiles = strsToDicts(testfiles)
        self.addTestCmd('pdfs', type='TeX')
        self.addTestCmd('waterfall', type='Waterfall')
        self.addTestCmd('xfont', type='CrossFont')
        self.addTestCmd('xtest', shapers=2, extracmds=['cmptxtrender'],
                cmd='${CMPTXTRENDER} -p -k -e ${shaper} -s "${script}" -l "${lang}" -e ${altshaper} -L ${shaper} -L ${altshaper} -t ${SRC[0]} -o ${TGT} --copy=fonts --strip "${SRC[1]}" "${SRC[1]}"')
        self.addTestCmd('test', usestandards=True, extracmds=['cmptxtrender'], shapers=1,
                cmd='${CMPTXTRENDER} -p -k -e ${shaper} -e ${shaper} -s "${script}" -l "${lang}" -t ${SRC[0]} -L test -L standard -o ${TGT} --copy fonts_${shaper} --strip "${SRC[1]}" "${SRC[2]}"')
        self.addTestCmd('ftml', type='FTML')
        c = type('alltests_Context', (package.cmdContext,), {'cmd' : 'alltests', '__doc__' : "User defined test: alltests"})

    def addTestCmd(self, _cmd, **kw) :
        testtype = kw.pop('type', 'test')
        if 'label' not in kw :
            i = len(self._allTests.get(_cmd, []))
            kw['label'] = _cmd + (" " + str(i) if i else "")
        builder = self.testMap.get(testtype, TestCommand)
        test = builder(_cmd, self, **kw)
        if kw.pop('replace', False) :
            self._allTests[_cmd] = [test]
        else :
            if _cmd not in self._allTests : self._allTests[_cmd] = []
            c = type(_cmd + '_Context', (package.cmdContext,), {'cmd' : _cmd, '__doc__' : "User defined test: " + _cmd})
            self._allTests[_cmd].append(test)

    def addFont(self, font) :
        for ts in self._allTests.values() :
            for t in ts :
                t.addFont(font)

    def addFtmlTest(self, path, **kw) :
        cmd = kw.pop('cmd', 'ftml')
        fontmode = 'none' if 'fonts' in kw and not 'fontmode' in kw else 'all'
        if cmd not in self._allTests :
            self.addTestCmd(cmd, type='FTML', fontmode=fontmode)
        for t in self._allTests[cmd] :
            t.addXsl(path, **kw)

    def build_tests(self, ctx, _cmd) :
        if _cmd == 'alltests' :
            cmds = sorted(self._allTests.keys())
            optional = True
        else :
            cmds = [_cmd]
            optional = False
        resultsdir = getattr(self, 'testresultsdir', ctx.env['TESTRESULTSDIR'] or 'tests')
        resultsroot = ctx.bldnode.make_node(resultsdir)
        for c in cmds :
            iname = c + "_index.html"
            tests = self._allTests.get(c, [])
            if not len(tests) or not any(map(lambda x: x.has_work(ctx, self._testfiles), tests)) : continue
            resultsnode = ctx.bldnode.find_or_declare(os.path.join(resultsdir, iname))
            res = templates.FontTests['index_head']
            temp = ""
            for t in tests :
                temp = t.build(ctx, resultsroot, optional=optional, testfiles=self._testfiles)
                if temp == "" : break
                res += temp
            if temp == "" : continue
            res += templates.FontTests['index_tail']
            resultsnode.write(res)

    def get_sources(self, ctx) :
        res = set()
        for ts in self._allTests.values() :
            for t in ts :
                res.update(t.get_sources(ctx))
        return res

    def get_build_tools(self, ctx) :
        res = set()
        for ts in self._allTests.values() :
            for t in ts :
                res.update(t.get_build_tools(ctx))
        return res


class TestFile(object) :

    def __init__(self, node, **kw) :
        self.node = node
        name = node if isinstance(node, basestring) else node.name
        for k, v in kw.items() : setattr(self, k, v)
        # parse filename
        if 'lang' not in kw :
            (lang, sep, tail) = name.partition('_')
            if sep == '_' and 2 < len(lang) < 5 :
                self.lang = lang

    def __str__(self) :
        return str(self.node)

    def setCtx(self, ctx) :
        if not isinstance(self.node, Node.Node) :
            self.node = ctx.path.find_resource(self.node)


class Test(object) :
    
    def __init__(self, font, label, **kw) :
        self._font = font
        self._srcs = []
        self.label = label
        self.fid = getattr(font, 'test_suffix', font.id) if font is not None else ""
        if 'shaper' in kw : self.fid += "_" + kw['shaper']
        if 'script' in kw and kw['script'] is not None : self.fid += "_" + kw['script']
        if 'altshaper' in kw : self.fid += "_" + kw['altshaper'] + "_" + kw['altscript']
        self.kw = kw
        self.kw['font'] = font

    def setSrcs(self, srcs) :
        self._srcs = srcs

fontmodes = {
    'all' : 0,
    'none' : 1,
    'collect' : 2
}

@FontTests.aTestCommand
class TestCommand(object) :

    _type = 'test'
    _intermediatesPerTest = False
    _defaults = {}

    def __init__(self, _cmd, fontTests, **kw) :
        self._subcmd = _cmd
        if not hasattr(self, 'shapers') : self.shapers = 1
        self.ext = '.html'
        self.kw = {}
        self.supports = ['.txt', '.ftml', '.xml']
        if 'coverage' in kw :
            if kw['coverage'] == 'fonts' : kw['notestfiles'] = True
            elif kw['coverage'] == 'shapers' : kw['shapers'] = 1; kw['notestfiles'] = True
            elif kw['coverage'] == 'textshaper' : kw['shapers'] = 1
            elif kw['coverage'] == 'shaperpairs' : kw['shapers'] = 2
            del kw['coverage']
        if 'label' not in kw : kw['label'] = _cmd
        if 'cmd' in kw : kw['cmd'] = wsiwaf.cmd(kw['cmd'])
        self.files = None
        for x in ('cmd', 'ext', 'files', 'label', 'shapers', 'supports') :     # magic attributes
            if x in kw : setattr(self, x, kw.pop(x))
        for k, v in kw.items() : self.kw[k] = v     # setattr(self, k, v)
        self._tests = []
        self._fonts = []
        self._filesLoaded = False
        self._srcsSet = False
        self._fontTests = fontTests

    def getFontGroup(self, name, font, once = False) :
        fg = self._fontTests.addFontToGroup(font, name, once)
        return fg

    def addFont(self, font) :
        if font in self._fonts : return
        self._fonts.append(font)
        fmode = fontmodes[self.kw.get('fontmode', 'all')]
        if fmode == 1 : font = None
        if self.shapers == 0 :
            f = self.getFontGroup('_allFonts', font, once = True) if fmode == 2 else font
            if fmode == 0 or not len(self._tests) :
                self.addTest(f, self.label, **self.kw)
        elif self.shapers == 1 :
            if hasattr(font, 'graphite') :
                f = self.getFontGroup('_allFonts_gr', font, once = True) if fmode == 2 else font
                if fmode == 0 or not any(map(lambda x: x._font == f and x.kw.get('shaper', '')=='gr', self._tests)) :
                    self.addTest(f, self.label + "_gr", shaper = 'gr', **self.kw)
            if hasattr(font, 'opentype') :
                if hasattr(font, 'script') :
                    scripts = [font.script] if isinstance(font.script, basestring) else font.script
                else :
                    scripts = [""]
                for s in scripts :
                    f = self.getFontGroup('_allFonts_ot' + s, font, once = True) if fmode == 2 else font
                    if fmode == 0 or not any(map(lambda x: x._font == f and x.kw.get('shaper', '')=='ot' and x.kw.get('script', '')==s, self._tests)) :
                        self.addTest(f, self.label + "_ot_" + s, shaper='ot', script=s, **self.kw)
        elif self.shapers == 2 :
            scripts = []
            if hasattr(font, "graphite") :
                scripts.append("")
            if hasattr(font, "opentype") and hasattr(font, "script") :
                if isinstance(font.script, basestring) :
                    scripts.append(font.script)
                else :
                    scripts.extend(font.script)
            for c in combinations(scripts, 2) :
                s1 = 'ot' if c[0] != "" else 'gr'
                s2 = 'ot' if c[1] != "" else 'gr'
                f = self.getFontGroup('_allFonts_' + s1+s2+c[0]+c[1], font, once = True) if fmode == 2 else font
                if fmode == 0 or not any(map(lambda x: x._font == f and x.kw.get('shaper', '')==s1 and x.kw.get('altshaper', '')==s2 and x.kw.get('script', '')==c[0] and x.kw.get('altscript', '')==c[1], self._tests)) :
                    self.addTest(f, self.label+"_"+s1+s2+c[0]+c[1], shaper=s1, altshaper=s2, script=c[0], altscript=c[1], **self.kw)

    def addTest(self, font, label, **kw) :
        """ Creates and adds a test from adding a font """
        t = Test(font, label, **kw)
        self._tests.append(t)

    def _setFiles(self, ctx, testfiles) :
        if self._filesLoaded : return
        self._filesLoaded = True
        if self.kw.get('notestfiles', False) : return
        testsdir = self.kw.get('testdir', ctx.env['TESTDIR'] or 'tests')
        if self.files is None :
            self.files = map(TestFile, antlist(ctx, testsdir, '**/*'))
        if getattr(self, 'addAllTestFiles', False) :
            filelist = antlist(ctx, testsdir, '**/*')
            testset = set(map(str, self.files))
            for f in filelist :
                if f not in testset :
                    testset.add(f)
                    if testfiles is not None and f in testfiles :
                        tf = TestFile(f, **testfiles[f])
                    else :
                        tf = TestFile(f)
                    self.files.append(tf)
        for f in self.files :
            f.setCtx(ctx)

    def get_resultsnode(self, ctx) :
        resultsroot = getattr(self, 'testresultsdir', ctx.env['TESTRESULTSDIR'] or 'tests')
        resultsdir = os.path.join(resultsroot, self.kw.get('resultsdir', self._subcmd))
        resultsnode = ctx.bldnode.find_or_declare(resultsdir)
        return resultsnode

    def _set_defaults(self, ctx) :
        for k, v in self._defaults.items() :
            if not hasattr(self, k) :
                setattr(self, k, ctx.env[v[0]] or  v[1])

    def _build_intermediates(self, ctx, testfiles) :
        self._set_defaults(ctx)
        fmode = fontmodes[getattr(self, 'fontmode', 'all')]
        resultsnode = self.get_resultsnode(ctx)
        if not self._srcsSet :
            self._setFiles(ctx, testfiles)
            self._srcsSet = True
            files = self.files if not self.kw.get('notestfiles', False) else [None]
            if self._intermediatesPerTest :
                for t in self._tests :
                    srcs = []
                    for f in files :
                        s = self.build_intermediate(ctx, f, t, resultsnode)
                        if s is not None :
                            s.origin = f
                            srcs.append(s)
                    t.setSrcs(srcs)
            else :
                srcs = []
                for f in files :
                    s = self.build_intermediate(ctx, f, None, resultsnode)
                    if s is not None :
                        s.origin = f
                        srcs.append(s)
                for t in self._tests :
                    t.setSrcs(srcs)
        return (fmode, resultsnode)

    def build(self, ctx, resultsroot, optional=False, testfiles=None) :
        """ Main entry point to the test system """
        (fmode, resultsnode) = self._build_intermediates(ctx, testfiles=testfiles)
        perfont = {}    # dict of tests against rows of results for each font
        for t in self._tests :
            if t._font not in perfont : perfont[t._font] = {}
        for t in self._tests :
            perfont[t._font][t] = {k.origin: v for k,v in self.build_test(ctx, t, resultsnode, resultsroot, optional=optional).items()}
        res = ""
        temps = templates.TestCommand
        for f, v in perfont.items() :
            allrows = set()
            res += temps['init_head'].format((f.id if f is not None else ""), "TestFile")
            allkeys = sorted(v.keys(), key=lambda x: x.label)
            for t in allkeys :
                res += temps['head_row'].format(t.label)
                allrows.update(v[t].keys())
            res += temps['head_row_end']
            for i in sorted(allrows) :
                res += temps['row_head'].format(str(i))
                for t in allkeys :
                    res += temps['cell_head']
                    if i in v[t] :
# It would be nice if we could flag a link (or hide it) if the size of the targetted file is zero. But
# we can't do that at this point since the commands to create the targets haven't run yet, only been
# scheduled. So may need some javascript for this.
                        res += temps['cell_content'].format(v[t][i])
                    res += temps['cell_tail']
                res += temps['row_tail']
            res += temps['init_tail']
        return res

    def build_intermediate(self, ctx, f, test, resultsnode) :
        """ Converts .htxt files to .txt, returns node for .txt files, all others return None.
            This method is intended to be subclassed """
        if f is None : return None
        (_, ext) = os.path.splitext(str(f.node))
        if ext == '.htxt' :
            targ = f.node.change_ext('.txt')
            ctx(rule=r"perl -CSD -pe 's{\\[uU]([0-9A-Fa-f]+)}{pack(qq/U/, hex($1))}oge' ${SRC} > ${TGT}", shell = 1, source = f.node, target = targ)
            return targ
        elif ext in self.supports :
            return f.node
        else :
            return None

    def build_test(self, ctx, test, targetdir, resultsroot, optional=False) :
        """ High level driver to run all the tests. See do_build for the subclassable method """
        def tostr(x) :
            if isinstance(x, basestring) :
                return x
            else :
                return x.path_from(resultsroot)

        results = {}
        srcs = test._srcs if test._srcs is not None else [None]
        for s in srcs :
            res = self.do_build(ctx, s, test, targetdir, optional=optional)
            if res is not None :
                results[s] = tostr(res)
        return results

    def do_build(self, ctx, srcnode, test, targetdir, optional=False) :
        """ Does the actual taskgen creation for running a particular test. This method is intended to be subclassed """
        s = str(srcnode).rpartition(".")[0]
        t = s + "_" + test.fid + self.ext
        target = ctx.path.find_or_declare(os.path.join(targetdir.bldpath(), t))
        srcs = [srcnode]
        fonts = test.kw.get('font', [])
        fonts = fonts if test.kw.get('multifonts', False) or isinstance(fonts, list) else [fonts]
        for f in fonts :
            srcs.append(ctx.bldnode.find_resource(str(f.target)))
        if test.kw.get('usestandards', False) :
            stddir = test.kw.get('standards', ctx.env['STANDARDS'] or 'references')
            for f in fonts :
                t = ctx.path.find_resource(os.path.join(stddir, str(f.target)))
                if t is None :
                    if optional : return None
                    Logs.error("Cannot find corresponding reference to {} in references dir {}/".format(f.target, stddir))
                    raise Errors.BuildError()
                srcs.append(t)
        gen = self.cmd.build(ctx, srcs, target, **test.kw)
        return target
#        gen.taskgens = [font.target + "_" + mode] if mode else [font.target]

    def has_work(self, ctx, testfiles) :
        """Returns True if there will be meaningful output from this test"""
        self._build_intermediates(ctx, testfiles)
        for t in self._tests :
            if t.kw.get('notestfiles', False) or len(t._srcs) : return True
        return False

    def get_sources(self, ctx) :
        self._setFiles(ctx, None)
        res = map(lambda x:x.node.path_from(ctx.srcnode), self.files)
        self.files = None
        self._filesLoaded = False
        return res

    def get_build_tools(self, ctx) :
        res = ["cp", "ttftable"]
        res.extend(self.kw.get('extracmds', []))
        return res

@FontTests.aTestCommand
class FtmlTestCommand(TestCommand) :

    _type="FTML"

    def __init__(self, _cmd, fontTests, **kw) :
        super(FtmlTestCommand, self).__init__(_cmd, fontTests, **kw)
        self._xsls = []

    def _make_ftml(self, task) :
        temps = templates.FtmlTestCommand
        ftmldat = temps['head']
        testf = codecs.open(task.inputs[0].abspath(), encoding='utf-8')
        count = 1
        for l in testf.readlines() :
            ftmldat += temps['content'].format(count, l.strip())
            count += 1
        testf.close()
        ftmldat += temps['tail']
        ftest = codecs.open(task.outputs[0].abspath(), "w", encoding="utf-8")
        ftest.write(ftmldat)
        ftest.close()
        return 0

    def build(self, ctx, resultsroot, optional=False, testfiles=None) :
        self.fmap = {}
        resultsnode = self.get_resultsnode(ctx)
        fontresults = resultsnode.find_or_declare('fonts')
        # need to copy displayftml.html into tests/ftml to get security working
        targdisp = resultsnode.find_or_declare('displayftml.html')
        if not os.path.exists(targdisp.abspath()) :
            shutil.copy(os.path.join(os.path.dirname(__file__), "displayftml.html"), targdisp.abspath())
        # go through fonts setting up cp or ttftable type contexts to get copies into the tests/ftml tree
        for f in self._fonts :
            fname = str(f.target)
            if self.shapers == 0 :
                target = fontresults.find_or_declare(fname)
                ctx(rule="${CP} ${SRC} ${TGT}", source = f.target, target = target)
                self.fmap[str(f.target)] = {"" : target}
            elif self.shapers == 1 :
                if hasattr(f, 'graphite') :
                    target = fontresults.find_or_declare(fname.replace(".", "_gr.", 1))
                    ctx(rule="${TTFTABLE} -d opentype ${SRC} ${TGT}", source = f.target, target = target)
                    if fname not in self.fmap : self.fmap[fname] = {}
                    self.fmap[fname]['gr'] = target
                if hasattr(f, 'opentype') :
                    if hasattr(f, 'script') :
                        scripts = [f.script] if isinstance(f.script, basestring) else f.script
                    else :
                        scripts = [None]
                    for s in scripts :
                        target = fontresults.find_or_declare(fname.replace(".", "_ot" + ("_"+s if s else "") + ".", 1))
                        rem = ",".join(filter(lambda x:x != s, scripts))
                        ctx(rule="${{TTFTABLE}} -d graphite {} ${{SRC}} ${{TGT}}".format("-s " + rem if rem else ""), source=f.target, target=target)
                        self.fmap[fname]['ot'+s] = target
        # go through copying all the xsl files as well, sigh
        xslresults = resultsnode.find_or_declare('xsl')
        self.xslmap = {}
        for x in self._xsls :
            ofile = xslresults.find_or_declare(x[0])
            ifile = ctx.srcnode.find_resource(x[0])
            self.xslmap[x[0]] = ofile
            if not os.path.exists(ofile.abspath()) :
                shutil.copy(ifile.abspath(), ofile.abspath())
        return super(FtmlTestCommand, self).build(ctx, resultsroot, testfiles=testfiles)

    def build_intermediate(self, ctx, f, test, resultsnode) :
        src = super(FtmlTestCommand, self).build_intermediate(ctx, f, test, resultsnode)
        if src is None :
            return None
        elif str(src).endswith(".ftml") :
            targ = resultsnode.find_or_declare(src.name)
            ctx(rule="${CP} ${SRC} ${TGT}", source=src, target=targ)
        elif str(src).endswith(".txt") :
            targname = src.name.replace('.txt', '.ftml')
            targ = resultsnode.find_or_declare(targname)
            ctx(rule = self._make_ftml, target = targ, source = src)
        else :
            return None
        return targ

    def do_build(self, ctx, srcnode, test, targetdir, optional=False) :
        resultsroot = ctx.bldnode.find_resource(getattr(self, 'testresultsdir', ctx.env['TESTRESULTSDIR'] or 'tests'))
        d = targetdir.find_resource('displayftml.html')
        res = "{}?xml={}&xsl={}".format(d.path_from(resultsroot), srcnode.path_from(targetdir), self.xslmap[test.kw['xsl']].path_from(targetdir))
        shp = test.kw.get('shaper', '')
        if shp == 'ot' : shp += test.kw.get('script', '')
        if ('multiplefonts' in test.kw and test.kw['multiplefonts']) or isinstance(test._font, list) :
            for f in test._font :
                res += "&fontsrc[]={}".format(self.fmap[str(f.target)][shp].abspath())
        else :
            res += "&fontsrc={}".format(self.fmap[str(test._font.target)][shp].path_from(targetdir))
        return res

    def addXsl(self, xsl, **kw) :
        if 'name' not in kw : kw['name'] = os.path.splitext(os.path.basename(xsl))[0]
        kw['xsl'] = xsl
        self._xsls.append((xsl, kw))
        fmode = fontmodes[kw.get('fontmode', 'all')]
        if fmode == 0 :         # all
            fonts = self._fonts
        elif fmode == 1 :
            fonts = [kw['fonts']]   # the group passed in
        elif fmode == 2 :
            fonts = [self.getFontGroup('_allFonts', None)]

        # add the tests directly so we don't multiply them
        for f in fonts :
            allf = f
            if fmode != 1 and (kw.get('multiplefonts', False) or 'fonts' in kw) :
                allf = kw.get('fonts', [])
                allf.insert(kw.get('addfontindex', 0), f)
            if self.shapers == 0 :
                self._tests.append(Test(allf, kw['name'], **kw))
            elif self.shapers == 1 :
                if hasattr(f, 'graphite') :
                    self._tests.append(Test(allf, kw['name'] + "_gr", shaper='gr', **kw))
                if hasattr(f, 'opentype') :
                    if hasattr(f, 'script') :
                        scripts = [f.script] if isinstance(f.script, basestring) else f.script
                    else :
                        scripts = [""]
                    for s in scripts :
                        self._tests.append(Test(allf, "{}_ot{}".format(kw['name'], ("_"+script if script else "")),
                                script=s, shaper='ot', **kw))

    def addTest(self, font, label, **kw) :
        for x in self._xsls :
            tkw = x[1]
            tkw.update(kw)
            label += "_" + tkw['name']
            self._tests.append(Test(font, label, **tkw))

@FontTests.aTestCommand
class TexTestCommand(TestCommand) :

    _type = 'TeX'
    _intermediatesPerTest = True

    def __init__(self, _cmd, fontTests, **kw) :
        kw['shapers'] = 1
        self._configured = False
        if 'supports' not in kw : kw['supports'] = ['.txt', '.htex']
        super(TexTestCommand, self).__init__(_cmd, fontTests, **kw)

    def _make_tex(self, mf, font, task) :
        texdat = templates.TexTestCommand['txt'].format(font.target, mf, texprotect(font.target),
                    texprotect(mf), time.strftime("%H:%M %a %d %b %Y %Z"),
                    texprotect(task.inputs[0].bldpath()), task.inputs[0].bldpath())
        task.outputs[0].write(texdat)
        return 0

    def _make_from_htex(self, mf, font, task) :
        texdat = templates.TexTestCommand['htex'].format(font, mf, task.inputs[0].bldpath())
        task.outputs[0].write(texdat)
        return 0

    def build_intermediate(self, ctx, f, test, resultsnode) :
        if f is None :
            targname = (self._subcmd + '_' + test.label + '_' + test.fid + ".tex")
            fn = self._make_tex
            src = [ctx.srcnode.find_node('wscript')]
        else :
            src = super(TexTestCommand, self).build_intermediate(ctx, f, test, resultsnode)
            if src is None :
                return None
            targname = src.name.rpartition('.')[0] + '_' + test.label + '_' + test.fid + ".tex"
            fn = self._make_from_htex if str(src).endswith('.htex') else self._make_tex
        attrs = ""
        s = test.kw.get('shaper', None)
        if s : attrs = "/" + s.upper()
        mf = ['language='+f.lang] if hasattr(f, 'lang') else []
        if 'script' in test.kw and test.kw['script'] != '' : mf.append('script='+test.kw['script'])
        if hasattr(f, 'features') :
            for k, v in f.features.items() :
                mf.append(k+'='+v)
        if len(mf) :
            attrs += ":" + "&".join(mf)
        targ = resultsnode.find_or_declare(targname)
        ctx(rule = curry_fn(fn, attrs, test._font), target = targ, source = src)
        return targ

    def do_build(self, ctx, srcnode, test, targetdir, deps = None, optional=False) :
        if deps is None : deps = []
        if test._font :
            fonts = test._font if isinstance(test._font, FontGroup) else [test._font]
            mode = getattr(test, 'shaper', None)
            for f in fonts :
                if mode == 'gr' :
                    deps.extend(f.graphite.get_sources(ctx))
                elif mode == 'ot' :
                    deps.extend(f.opentype.get_sources(ctx))
                else :
                    deps.extend(f.get_sources(ctx))
        target = srcnode.change_ext('.pdf')
        ctx(rule = '${XETEX} --interaction=batchmode --output-directory=./' + srcnode.bld_dir() + ' ./${SRC[0].bldpath()}',
                source = [srcnode], target = target, deps = deps,
                taskgens = [test.fid])
        return target

    def get_build_tools(self, ctx) :
        if self._configured : return []
        self._configured = True
        try :
            ctx.find_program('xetex')
        except ctx.errors.ConfigurationError :
            pass
        return set()


@FontTests.aTestCommand
class Waterfall(TexTestCommand) :

    _type = 'Waterfall'
    _defaults = {
        'text' : ('TESTSTRING', ''),
        'sizes' : ('WATERFALLSIZES', [6, 8, 9, 10, 11, 12, 13, 14, 16, 18, 22, 24, 28, 32, 36, 42, 48, 56, 72]),
        'sizefactor' : ('TESTLINESPACINGFACTOR', 1.2)
    }

    def __init__(self, _cmd, fontTests, **kw) :
        kw['notestfiles'] = 1
        super(Waterfall, self).__init__(_cmd, fontTests, **kw)

    def _make_tex(self, mf, font, task) :
        temps = templates.Waterfall
        texdat = temps['head'].format(texprotect(font.target), texprotect(mf), texprotect(self.kw.get('featstr', '')), time.strftime("%H:%M %a %d %b %Y %Z"))

        for s in self.sizes :
            texdat += temps['content'].format(font.target, mf, self.kw.get('featstr', ''), s, s * self.sizefactor, self.text) 
        texdat += temps['tail']
        ftest = codecs.open(task.outputs[0].abspath(), "w", encoding="utf-8")
        ftest.write(texdat)
        ftest.close()
        return 0

    def build(self, ctx, resultsroot, optional=False, testfiles=None) :
        """ Main entry point to the test system """
        self._set_defaults(ctx)
        if self.text == "" : return
        return super(Waterfall, self).build(ctx, resultsroot, optional=optional, testfiles=testfiles)

    def has_work(self, ctx, testfiles) :
        self._set_defaults(ctx)
        if self.text == "" : return False
        return super(Waterfall, self).has_work(ctx, testfiles)

    def get_sources(self, ctx) :
        return []


@FontTests.aTestCommand
class CrossFont(Waterfall) :

    _type = 'CrossFont'
    _defaults = {
        'text' : ('TESTSTRING', ''),
        'size' : ('TESTFONTSIZE', 12)
    }

    def __init__(self, _cmd, fontTests, **kw) :
        kw['fontmode'] = 'collect'
        super(CrossFont, self).__init__(_cmd, fontTests, **kw)

    def get_sources(self, ctx) :
        return []

    def _make_tex(self, mf, font, task) :
        temps = templates.CrossFont
        featstr = self.kw.get('featstr', '')
        texdat = temps['head'].format(texprotect(mf), texprotect(featstr), time.strftime("%H:%M %a %d %b %Y %Z"))

        for f in font :
            texdat += temps['content'].format(f.target, mf, featstr, self.size, texprotect(f.target), self.text)
        texdat += temps['tail']
        ftest = codecs.open(task.outputs[0].abspath(), "w", encoding="utf-8")
        ftest.write(texdat)
        ftest.close()
        return 0

