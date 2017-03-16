#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Build, Errors, Node, Options, Logs, Utils
import wafplus, font_tests
import font, templater 
import os, sys, shutil, time, ConfigParser

keyfields = ('copyright', 'version', 'appname', 'desc_short',
            'desc_long', 'outdir', 'desc_name', 'docdir', 'debpkg')
optkeyfields = ('company', 'instdir', 'zipfile', 'zipdir', 'readme',
            'license', 'contact', 'url', 'testfiles')

def formatdesc(s) :
    res = []
    for l in s.strip().splitlines(True) :
        if len(l) > 1 :
            res.append(" " + l)
        else :
            res.append(" ." + l)
    return "".join(res)

def formattz(tzsec) :
    tzmin = tzsec / 60
    tzhr = -tzmin / 60
    tzmin = tzmin % 60
    if tzmin < 0 : tzmin = -tzmin
    return "{0:+03d}{1:02d}".format(tzhr, tzmin)

class Package(object) :

    packagestore = []
    packdict = {}
    globalpackage = None

    @classmethod
    def initPackages(cls, ps = None, g = None) :
        cls.packagestore = ps or []
        cls.globalpackage = g

    @classmethod
    def packages(cls) :
        return cls.packagestore

    @classmethod
    def global_package(cls, **kw) :
        if cls.globalpackage == None :
            cls.globalpackage = len(cls.packagestore)
            fields = {}
            for k in keyfields :
                fields[k] = getattr(Context.g_module, k.upper(), '')
            for k in optkeyfields :
                v = getattr(Context.g_module, k.upper(), None)
                if v is not None :
                    fields[k] = v
            p = Package(**fields)
        else :
            p = cls.packagestore[cls.globalpackage]
        for k, v in kw.items() :
            setattr(p, k, v)
        return p

    def __init__(self, **kw) :
        if 'zipdir' not in kw : kw['zipdir'] = 'releases'
        if 'zipfile' not in kw :
            kw['zipfile'] = "%s/%s-%s.zip" % (kw['zipdir'], kw['appname'], kw['version'])

        for k, v in kw.items() :
            setattr(self, k, v)
        for k in keyfields :
            if not hasattr(self, k) : setattr(self, k, '')
        self.packagestore.append(self)
        self.fonts = []
        self.keyboards = []
        self.subpackages = {}
        self.reldir = ''
        self.order = []
        self.package = self
        self.fontTests = font_tests.FontTests(getattr(self, 'testfiles', None))

    def get_build_tools(self, ctx) :
        try :
            ctx.find_program('ots-sanitize', var="OTS")
            ctx.find_program('fontlint', var="FONTLINT")
            ctx.find_program('FontValidator.exe', var="FONTVALIDATOR")
            ctx.find_program('pyfontaine', var="PYFONTAINE")
        except ctx.errors.ConfigurationError :
            pass
        for p in ('makensis', ) :
            try :
                ctx.find_program(p)
            except ctx.errors.ConfigurationError :
                pass
        res = set()
        for f in self.fonts :
            res.update(f.get_build_tools(ctx))
        for k in self.keyboards :
            res.update(k.get_build_tools(ctx))
        res.update(self.fontTests.get_build_tools(ctx))
        return res

    def get_sources(self, ctx) :
        res = []
        self.subrun(ctx, lambda p, c: res.extend(p.get_sources(c)), onlyfn = True)
        fonts = [x for x in self.fonts if not hasattr(x, 'dontship')]
        keyboards = [x for x in self.keyboards if not hasattr(x, 'dontship')]

        res.extend(self.best_practise_files(fonts, keyboards))

        for f in fonts :
            res.extend(f.get_sources(ctx))
        for k in keyboards :
            res.extend(k.get_sources(ctx))
        res.extend(self.fontTests.get_sources(ctx))
        if self.docdir :
            for p, n, fs in os.walk(self.docdir) :
                for f in fs :
                    res.append(os.path.join(p, f))
        return res

    def best_practise_files(self,fonts,keyboards):
        licenses = []
        if fonts :
            licenses.extend([getattr(self, 'license', 'OFL.txt')])
        if 'OFL.txt' in licenses:
            licenses.extend(['OFL-FAQ.txt', 'FONTLOG.txt'])
        if keyboards :
            if not fonts or not getattr(self, 'license', None) :
                licenses.extend([getattr(self, 'license', 'MIT.txt')])

        files = licenses + ['README.txt', 'README.md']
        missing = [p for p in files if not os.path.exists(p)]
        if missing:
            Logs.warn("These files are required but missing: \n" + '\n'.join(missing))
        return(set(files) - set(missing))

    def add_package(self, package, path) :
        if path not in self.subpackages :
            self.subpackages[path] = []
            self.order.append(path)
        for p in package if isinstance(package, list) else (package, ) :
            p.reldir = path
            self.subpackages[path].append(p)

    def add_font(self, font) :
        self.fonts.append(font)
        self.global_package().add_font_to_test(font)

    def add_font_to_test(self, font) :
        self.fontTests.addFont(font)

    def add_kbd(self, kbd) :
        self.keyboards.append(kbd)

    def add_reservedofls(self, *reserved) :
        if hasattr(self, 'reservedofl') :
            self.reservedofl.update(reserved)
        else :
            self.reservedofl = set(reserved)

    def make_ofl_license(self, task, base) :
        bld = task.generator.bld
        font.make_ofl(task.outputs[0].path_from(base.path if base else bld.path), self.reservedofl,
                getattr(self, 'ofl_version', '1.1'),
                copyright = getattr(self, 'copyright', ''),
                template = getattr(self, 'ofltemplate', None))
        return 0
    
    def subrun(self, bld, fn, onlyfn = False) :
        for k in self.order :
            v = self.subpackages[k]
            relpath = os.path.relpath(k, bld.top_dir or bld.path.abspath())
            b = bld.__class__(out_dir = os.path.join(os.path.abspath(k), bld.bldnode.srcpath()),
                              top_dir = os.path.abspath(k), run_dir = os.path.abspath(k))
            b.init_dirs()
            b.issub = True
            if onlyfn :
                for p in v :
                    fn(p, b)
                continue
            b.fun = bld.fun
            gm = Context.g_module
            Context.g_module = Context.cache_modules[os.path.join(os.path.abspath(b.top_dir), 'wscript')]
            oexe = getattr(Context.g_module, bld.fun, None)
            def lexe(ctx) :
                for p in v :
                    fn(p, ctx)
                if oexe : oexe(ctx)
            setattr(Context.g_module, bld.fun, lexe)
            b.execute()
            setattr(Context.g_module, bld.fun, oexe)
            Context.g_module = gm
        
    def build(self, bld, base = None) :
        self.subrun(bld, lambda p, b: p.build(b, bld))
        for f in self.fonts :
            f.build(bld)
        for k in self.keyboards :
            k.build(bld)

        self.subrun(bld, lambda p, b: self.add_reservedofls(*p.reservedofl) if hasattr(p, 'reservedofl') else None, onlyfn = True)
        def methodwrapofl(tsk) :
            return self.make_ofl_license(tsk, base)

        if hasattr(self, 'reservedofl') :
            if not hasattr(self, 'license') : self.license = 'OFL.txt'
            if not os.path.exists(self.license) :
                bld(name = 'Package OFL', rule = methodwrapofl, target = bld.bldnode.find_or_declare(self.license))

    def build_test(self, bld, test='test') :
        self.subrun(bld, lambda p, b: p.build_test(b, test=test))
        self.fontTests.build_tests(bld, test)
        for k in self.keyboards :
            k.build_test(bld, test=test)

    def build_ots(self, bld) :
        if 'OTS' not in bld.env :
            Logs.warn("ots not installed. Can't complete. See http://github.com/khaledhosny/ots")
            return
        self.subrun(bld, lambda p, b: p.build_ots(b))
        for f in self.fonts :
            f.build_ots(bld)

    def build_fontlint(self, bld) :
        if 'FONTLINT' not in bld.env :
            Logs.warn("fontlint not installed. Can't complete. See http://fontforge.github.io and fontforge package")
            return
        self.subrun(bld, lambda p, b: p.build_fontlint(b))
        for f in self.fonts :
            f.build_fontlint(bld)

    def build_validate(self, bld) :
        if 'FONTVALIDATOR' not in bld.env :
            Logs.warn("FontValidator not installed. Can't complete. See http://github.com/HinTak/Font-Validator")
            return
        self.subrun(bld, lambda p, b: p.build_fontvalidator(b))
        for f in self.fonts :
            f.build_fontvalidator(bld)

    def build_pyfontaine(self, bld) :
        if 'PYFONTAINE' not in bld.env :
            Logs.warn("pyfontaine not installed. Can't complete. See http://github.com/davelab6/pyfontaine")
            return
        self.subrun(bld, lambda p, b: p.build_pyfontaine(b))
        for f in self.fonts :
            f.build_pyfontaine(bld)

    def build_start(self, bld) :
        self.subrun(bld, lambda p, b: p.build_start(b))
        for f in self.fonts :
            f.build_start(bld)

    def build_exe(self, bld) :
        if 'MAKENSIS' not in bld.env :
            Logs.error("makensis not installed. Can't complete. See http://nsis.sourceforge.net and nsis package")
            return
        for t in ('appname', 'version') :
            if not hasattr(self, t) :
                raise Errors.WafError("Package '%r' needs '%s' attribute" % (self, t))
        thisdir = os.path.dirname(__file__)
        fonts = [x for x in self.fonts if not hasattr(x, 'dontship')]
        for f in fonts: f.path = f.target
        kbds = [x for x in self.keyboards if not hasattr(x, 'dontship')]
        if not hasattr(self, 'license') :
            if fonts and kbds :
                # make new file and copy OFL.txt and MIT.txt into it
                self.license = 'LICENSE'
                font_license = bld.bldnode.find_resource('OFL.txt')
                if not font_license :
                    raise Errors.WafError("The font license file OFL.txt doesn't exist so cannot build exe")
                kb_license = bld.bldnode.find_resource('MIT.txt')
                if not kb_license :
                    raise Errors.WafError("The keyboard license file MIT.txt doesn't exist so cannot build exe")
                f = open("LICENSE", "w")
                for tempfile in kb_license, font_license:
                    f.write(tempfile.read())
                    f.write("\n")
                f.close()
            elif kbds :
                self.license = 'MIT.txt'
            else :
                self.license = 'OFL.txt'
        if self.license is not None and not bld.bldnode.find_resource(self.license):
            raise Errors.WafError("The license file " + self.license + " does not exist so cannot build exe.")

   
        env =   {
            'project' : self,
            'basedir' : thisdir,
            'fonts' : fonts,
            'kbds' : kbds,
            'env' : bld.env
                }
        def blddir(base, val) :
            x = bld.bldnode.find_resource(val)
            base = os.path.join(bld.srcnode.abspath(), base.package.reldir, bld.bldnode.srcpath())
            return os.path.join(base, x.bldpath())

        # create a taskgen to expand the installer.nsi
        bname = 'installer_' + self.appname
        def procpkg(p, c) :
            for k in p.keyboards :
                k.setup_vars(c)
            kbds.extend(p.keyboards)
            fonts.extend(p.fonts)
            for f in p.fonts :
                f.path = c.bldnode.find_or_declare(f.target).path_from(bld.bldnode)
        if Options.options.debug:
            import pdb; pdb.set_trace()

        self.subrun(bld, procpkg, onlyfn = True)
        if Options.options.debug:
            import pdb; pdb.set_trace()
        task = templater.Copier(prj=self, fonts=fonts, kbds=kbds, basedir=thisdir, env=bld.env, bld=blddir)
        task.set_inputs(bld.root.find_resource(self.exetemplate if hasattr(self, 'exetemplate') else os.path.join(thisdir, 'installer.nsi')))
        for d, x in self.get_files(bld) :
            if not x : continue
            r = os.path.relpath(os.path.join(d, x), bld.bldnode.abspath())
            y = bld.bldnode.find_or_declare(r)
            if os.path.isfile(y and y.abspath()) : task.set_inputs(y)

        task.set_outputs(bld.bldnode.find_or_declare(bname + '.nsi'))
        bld.add_to_group(task)
        bld(rule='${MAKENSIS} -V4 -O' + bname + '.log ${SRC}', source = bname + '.nsi', target = '%s/%s-%s.exe' % ((self.outdir or '.'), (self.desc_name or self.appname.title()), self.version))

    def execute_zip(self, bld) :
        import zipfile
        znode = bld.path.find_or_declare(self.zipfile)      # create dirs
        zip = zipfile.ZipFile(znode.abspath(), 'w', compression=zipfile.ZIP_DEFLATED)
        basearc = self.appname + '-' + str(self.version)

        for t in self.get_files(bld) :
            d, x = t[0], t[1]
            if not x : continue
            r = os.path.relpath(os.path.join(d, x), bld.bldnode.abspath())
            y = bld.path.find_or_declare(r)
            if len(t) > 2 :
                archive_name = os.path.join(basearc, t[2])
            else :
                archive_name = os.path.join(basearc, x)
            if os.path.isfile(y.abspath()) :
               zip.write(y.abspath(), archive_name, zipfile.ZIP_DEFLATED)
        zip.close()

    def _get_arcfile(self, bld, path) :
        if path is None : return None
        pnode = bld.path.find_resource(path)
        if pnode is None :
           return None
        elif pnode.is_src() :
            return (bld.path.abspath(), pnode.srcpath())
        else :
            return (bld.bldnode.abspath(), pnode.bldpath())


    def get_files(self, bld) :
        """ Returns a list of files to go into the generated zip for this package.
            Each entry in the list is (x, y, z) where:
                x is the base path from which the path to y is relative
                y is the path to the file to include
                z is optional and is the path to use in the archive
        """
        res = []
        self.subrun(bld, lambda p, c: res.extend(p.get_files(c)), onlyfn = True)

        res.extend(map(lambda x: (bld.out_dir, x), self.best_practise_files(self.fonts, self.keyboards)))

        for f in self.fonts :
            if not hasattr(f, 'dontship') :
                res.extend(map(lambda x: (bld.out_dir, x), f.get_targets(bld)))
        for k in self.keyboards :
            if not hasattr(k, 'dontship') :
                res.extend(map(lambda x: (bld.out_dir, x), k.get_targets(bld)))
        def docwalker(top, dname, fname) :
            i = 0
            while i < len(fname) :
                if fname[i].startswith('.') :
                    del fname[i]
                else :
                    i += 1
            res.extend([(top, os.path.relpath(os.path.join(dname, x), top)) for x in fname if os.path.isfile(os.path.join(dname, x))])
        if self.docdir :
            y = bld.path.find_or_declare(self.docdir)
            os.path.walk(y.abspath(), docwalker, bld.path.abspath())
        return res

class zipContext(Build.BuildContext) :
    """Create release zip of build results"""
    cmd = 'zip'

    def post_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_zip(self)
            Logs.warn('Zip release generated.')

class releaseContext(Build.BuildContext) :
    """Create release zip and tarball (source release) of build results"""
    cmd = 'release'

    def post_execute_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_srcdist(self)

    def post_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_zip(self)
            Logs.warn('Zip release and tarball (source release) generated.')

class cmdContext(Build.BuildContext) :
    """Build Windows installer"""
    cmd = 'exe' # must have a cmd otherwise this class overrides Build.BuildContext

    def pre_build(self) :
        if hasattr(self, 'issub') : return
        super(cmdContext, self).pre_build()
        if Options.options.debug :
            import pdb; pdb.set_trace()
        self.add_group(self.cmd)
        for p in Package.packages() :
            if hasattr(p, 'build_' + self.cmd) :
                getattr(p, 'build_' + self.cmd)(self)
            else :
                p.build_test(self, test=self.cmd)

class pdfContext(cmdContext) :
    """Create pdfs of test texts for fonts and layouts for keyboards"""
    cmd = 'pdfs'

    def build(self) :
        pass

class testContext(cmdContext) :
    """Run basic tests, usually regression tests"""
    cmd = 'test'

class otsContext(cmdContext) :
    """Test fonts using OpenType Sanitizer. Check <font.target>_ots.log"""
    cmd = 'ots'

class fontlintContext(cmdContext) :
    """Test fonts using fontlint. Check <font.target>_fontlint.log"""
    cmd = 'fontlint'

class fontvalidatorContext(cmdContext) :
    """Test fonts using FontValidator. Check html (and xml) reports."""
    cmd = 'validate'

class pyfontaineContext(cmdContext) :
    """Report coverage using pyfontaine. Check the test reports."""
    cmd = 'pyfontaine'

class crashContext(Context.Context) :
    """Crash and burn with fire"""
    cmd = 'crash'
    def execute(self) :
        Utils.subprocess.Popen("timeout 20 aafire -driver slang ; reset", shell = 1).wait()

class versionContext(Context.Context) :
    """Find out which version of smith you have. (as well as the underlying waf version)"""
    cmd = 'version'
    def execute(self) :
        Logs.warn('Version of smith currently installed (as a package):')
        Utils.subprocess.Popen("apt-cache show smith | grep Version", shell = 1).wait()
        Logs.warn('Version of waf currently installed:')
        Utils.subprocess.Popen("smith --version", shell = 1).wait()

class startContext(Context.Context) : 
    """start: create project template folder structure"""
    cmd = 'start'
    def execute(self) :
        thisdir = os.path.dirname(__file__)
        folders =  ('source', 'documentation', 'tools', 'web', 'tests', 'config', 'build', 'subsets')
        if not os.path.exists('wscript'):
            for f in folders:
                if not os.path.exists(f):
                    os.mkdir(f)
            shutil.copy(os.path.join(thisdir, 'wscript'), 'wscript')
            shutil.copy(os.path.join(thisdir, 'dot.gitattributes'), '.gitattributes')
            shutil.copy(os.path.join(thisdir, 'dot.gitignore'), '.gitignore')
            shutil.copy(os.path.join(thisdir, 'OFL.txt'), 'OFL.txt')
            shutil.copy(os.path.join(thisdir, 'OFL-FAQ.txt'), 'OFL-FAQ.txt')
            shutil.copy(os.path.join(thisdir, 'FONTLOG.txt'), 'FONTLOG.txt')
            shutil.copy(os.path.join(thisdir, 'README.md'), 'README.md')
            Logs.warn('This project has been smith-ified: template files and standard folders have been added to this folder.\nYou can now personalize the templates and run "smith configure"')
        else:
            Logs.warn('This project is already smith-ified. No files have been changed.')


class srcdistContext(Build.BuildContext) :
    """Create source release tarball of project (.tar.xz)"""
    cmd = 'srcdist'

    def execute_build(self) :
        self.recurse([self.run_dir], 'srcdist', mandatory = False)
        res = set(['wscript'])
        files = {}
        if Options.options.debug :
            import pdb; pdb.set_trace()
        if os.path.exists('debian') :
            files['debian'] = self.srcnode.find_node('debian')

        if os.path.exists('web') :
            files['web'] = self.srcnode.find_node('web')

        # hoover up everything under version control
        vcs = getattr(Context.g_module, "VCS", 'auto')
        if vcs is not None :
            for d in [''] + getattr(Context.g_module, 'SUBMODULES', []) :
                cmd = None
                vcsbase = None
                if vcs == 'git' or os.path.exists(os.path.join(d, '.git', '.gitignore', 'gitattributes')) :
                    cmd = ["git", "ls-files"]
                elif vcs == 'hg' or os.path.exists(os.path.join(d, '.hg')) :
                    cmd = ["hg", "locate", "--include", "."]
                    vcsbase = Utils.subprocess.Popen(["hg", "root"], cwd=d or '.', stdout=Utils.subprocess.PIPE).communicate()[0].strip()
                elif vcs == 'svn' or os.path.exists(os.path.join(d, '.svn')) :
                    cmd = ["svn", "list", "-R"]
                if cmd is not None :
                    filelist = Utils.subprocess.Popen(cmd, cwd=d or '.', stdout=Utils.subprocess.PIPE).communicate()[0]
                    flist = [os.path.join(d, x.strip()) for x in filelist.splitlines()]
                    if vcsbase is not None :
                        pref = os.path.relpath(d or '.', vcsbase)
                        flist = [x[len(pref)+1:] if x.startswith(pref) else x for x in flist]
                    res.update(flist)

        # add in everything the packages say they need, including explicit files
        for p in Package.packages() :
            res.update(set(p.get_sources(self)))

        # process the results into nodes
        for f in res :
            if not f : continue
            if isinstance(f, Node.Node) :
                files[f.srcpath()] = f
            else :
                n = self.srcnode.find_resource(f)
                files[f] = n

        # now generate the tarball
        import tarfile
        tarname = getattr(Context.g_module, 'SRCDIST', None)
        if not tarname :
            tarbase = getattr(Context.g_module, 'APPNAME', 'noname') + "-" + str(getattr(Context.g_module, 'VERSION', "0.0"))
            tarname = tarbase
        else :
            tarbase = tarname
        tarfilename = os.path.join(getattr(Context.g_module, 'ZIPDIR', 'releases'), tarname) + '.tar'
        tnode = self.path.find_or_declare(tarfilename)
        tar = tarfile.open(tnode.abspath(), 'w')
        incomplete = False

        for f in sorted(files.keys()) :
            if f.startswith('../') :
                Logs.warn('Sources will not include file: ' + f)
                incomplete = True
                continue
            if files[f] :
                tar.add(files[f].abspath(), arcname = os.path.join(tarbase, f))
        tar.close()
        xzfilename = tarfilename + '.xz'
        xznode = self.path.find_or_declare(xzfilename)
        cmd = ["xz", tnode.abspath()]
        Utils.subprocess.call(cmd)
        Logs.warn('Tarball .tar.xz (source release) generated.')
        if incomplete :
            Logs.error("Not all the sources for the project have been included in the tarball(s) so the wscript in it will not build.")

class srcdistcheckContext(srcdistContext) :
    """checks if the project compiles (tarball from 'srcdist')"""
    cmd = 'srcdistcheck'

    def execute_build(self) :
        import tarfile
        tarname = getattr(Context.g_module, 'SRCDIST', None)
        if not tarname :
            tarbase = getattr(Context.g_module, 'APPNAME', 'noname') + "-" + str(getattr(Context.g_module, 'VERSION', "0.0"))
            tarname = tarbase
        else :
            tarbase = tarname
        tarfilename = os.path.join(getattr(Context.g_module, 'ZIPDIR', 'releases'), tarname) + '.tar.gz'
        tnode = self.path.find_or_declare(tarfilename)
        try :
            tar = tarfile.open(tnode.abspath(), 'r:gz')
            tar.extractall()
            tar.close()
        except :
            Logs.error("Tarball not found. Run smith srcdist first.")
        # tarbase is directory to configure and build
        ret = Utils.subprocess.Popen([sys.argv[0], 'configure', 'build'], cwd=tarbase).wait()
	if ret:
            raise Errors.WafError('srcdistcheck failed with code %i' % ret)

        shutil.rmtree(tarbase)

class makedebianContext(Build.BuildContext) :
    """Build Debian/Ubuntu packaging templates for this project. Along with orig tarball"""
    cmd = 'deb-templates'

    def execute_build(self) :
        # check we have all the info we need
        if os.path.exists('debian') :
            Logs.warn("debian/ packaging folder already exists, did not generate new templates")
            return
        Logs.warn("debian/ packaging folder templates generated.")

        # generate the orig tarball for Debian/Ubuntu (simply copying the tarball and changing - to _)

        res = set(['wscript'])
        files = {}
        if Options.options.debug :
            import pdb; pdb.set_trace()

        if os.path.exists('web') :
            files['web'] = self.srcnode.find_node('web')

        # hoover up everything under version control
        vcs = getattr(Context.g_module, "VCS", 'auto')
        if vcs is not None :
            for d in [''] + getattr(Context.g_module, 'SUBMODULES', []) :
                cmd = None
                vcsbase = None
                if vcs == 'git' or os.path.exists(os.path.join(d, '.git', '.gitignore', 'gitattributes')) :
                    cmd = ["git", "ls-files"]
                elif vcs == 'hg' or os.path.exists(os.path.join(d, '.hg')) :
                    cmd = ["hg", "locate", "--include", "."]
                    vcsbase = Utils.subprocess.Popen(["hg", "root"], cwd=d or '.', stdout=Utils.subprocess.PIPE).communicate()[0].strip()
                elif vcs == 'svn' or os.path.exists(os.path.join(d, '.svn')) :
                    cmd = ["svn", "list", "-R"]
                if cmd is not None :
                    filelist = Utils.subprocess.Popen(cmd, cwd=d or '.', stdout=Utils.subprocess.PIPE).communicate()[0]
                    flist = [os.path.join(d, x.strip()) for x in filelist.splitlines()]
                    if vcsbase is not None :
                        pref = os.path.relpath(d or '.', vcsbase)
                        flist = [x[len(pref)+1:] if x.startswith(pref) else x for x in flist]
                    res.update(flist)

        # add in everything the packages say they need, including explicit files
        for p in Package.packages() :
            res.update(set(p.get_sources(self)))

        # process the results into nodes
        for f in res :
            if not f : continue
            if isinstance(f, Node.Node) :
                files[f.srcpath()] = f
            else :
                n = self.srcnode.find_resource(f)
                files[f] = n

        # now generate the tarball
        import tarfile
        tarname = getattr(Context.g_module, 'SRCDIST', None)
        if not tarname :
            tarbase = getattr(Context.g_module, 'APPNAME', 'noname') + "-" + str(getattr(Context.g_module, 'VERSION', "0.0"))
            tarname = tarbase
        else :
            tarbase = tarname
        tarfilename = os.path.join(getattr(Context.g_module, 'ZIPDIR', 'releases'), tarname) + '.tar'
        tnode = self.path.find_or_declare(tarfilename)
        incomplete = False

        xzfilename = tarfilename + '.xz'
        xznode = self.path.find_or_declare(xzfilename)

        origbase = getattr(Context.g_module, 'DEBPKG', 'noname') + "_" + str(getattr(Context.g_module, 'VERSION', "0.0"))
        origfilename = os.path.join('../../', origbase) + '.orig' + '.tar.xz'
        onode = self.path.find_or_declare(origfilename)
        shutil.copyfile(xznode.abspath(), onode.abspath())
        Logs.warn('Tarball .orig.tar.xz (source release) file for Debian/Ubuntu generated in the parent folder.')

        globalpackage = Package.packagestore[Package.globalpackage]
        srcname = getattr(globalpackage, 'debpkg', None)
        if not srcname :
            raise Errors.WafError('No debpkg information given to default_package. E.g. set DEBPKG')
        srcversion = getattr(globalpackage, 'version', None)
        if not srcversion :
            raise Errors.WafError('No version information given to default_package. E.g. set VERSION')
        maint = os.getenv('DEBFULLNAME') + ' <' + os.getenv('DEBEMAIL') + '>'
        if not maint :
            raise Errors.WafError("I don't know who you are, please set the DEBFULLNAME and DEBEMAIL environment variables")
        license = getattr(globalpackage, 'license', None)
        if not license :
            raise Errors.WafError("default_package needs a license. E.g. set LICENSE")
        license = self.bldnode.find_resource(license)
        if not license :
            raise Errors.WafError("The license file doesn't exist, perhaps you need to smith build first")

        contact = getattr(globalpackage, 'contact', '')
        if not contact :
            Logs.warn("Optional contact information not provided.")

        url = getattr(globalpackage, 'url', '')
        if not url :
            Logs.warn("Optional upstream URL not provided.")

        # install and dirs files
        os.makedirs('debian/bin')
        shutil.copy(sys.argv[0], 'debian/bin')
        hasfonts = 0
        haskbds = False
        for p in Package.packages() :
            pname = getattr(p, 'debpkg', None)
            if not pname : continue
            fdir = "/usr/share/fonts/opentype/" + pname + "\n"
            fdirs = file(os.path.join('debian', 'dirs'), 'w')
            if len(p.fonts) :
                fdirs.write(fdir)
                hasfonts = hasfonts | 1
            fdirs.close()
            finstall = file(os.path.join('debian', 'install'), 'w')
            for f in p.fonts :
                finstall.write(getattr(Context.g_module, 'out', 'results') + "/" + f.target + "\t" + fdir)
                if hasattr(f, 'graphite') : hasfonts = hasfonts | 2
            finstall.close()

        # source format 
        os.makedirs('debian/source')
        fformat = file(os.path.join('debian', 'source', 'format'), 'w')
        fformat.write('''3.0 (quilt)''')
        fformat.close()


        # changelog
        fchange = file(os.path.join('debian', 'changelog'), 'w')
        fchange.write('''{0} ({1}-1) unstable; urgency=low

  * Release of ... under ... 
  * Describe your significant changes here (use dch to help you fill in the changelog automatically).

 -- {2}  {3} {4}
'''.format(srcname, srcversion, maint, time.strftime("%a, %d %b %Y %H:%M:%S"), formattz(time.altzone)))
        fchange.close()

        # copyright (needs http://www.debian.org/doc/packaging-manuals/copyright-format/1.0/ machine-readable format)
        shutil.copy(license.abspath(), os.path.join('debian', 'copyright'))

        # control  (needs Homepage: field)
        bdeps = []
        if hasfonts & 1 :
            bdeps.append('libfont-ttf-scripts-perl, python-palaso, fontforge')
        if hasfonts & 2 :
            bdeps.append('grcompiler')
        if maint : maint = "\nMaintainer: " + maint
        fcontrol = file(os.path.join('debian', 'control'), 'w')
        fcontrol.write('''Source: {0}
Priority: optional
Section: fonts{1}
Build-Depends: debhelper (>= 9~), {2}
Standards-Version: 3.9.6
Homepage: {3}
X-contact: {4}

'''.format(srcname, maint, ", ".join(bdeps), url, contact))
        for p in Package.packages() :
            pname = getattr(p, 'debpkg', None)
            if not pname : continue
            fcontrol.write('''Package: {0}
Section: fonts
Architecture: all
Multi-Arch: foreign
Depends: ${{misc:Depends}}
Description: {1}
{2}

'''.format(pname, p.desc_short, formatdesc(p.desc_long)))
        fcontrol.close()

        # other files
        fileinfo = {
            'rules' : '''#!/usr/bin/make -f

SMITH=debian/bin/smith
%:
	dh $@

override_dh_auto_configure :
	${SMITH} configure

override_dh_auto_build :
	${SMITH} build

override_dh_auto_clean :
	${SMITH} distclean

override_dh_auto_test :

override_dh_auto_install :

override_dh_installchangelogs:
	dh_installchangelogs -k FONTLOG.txt

override_dh_builddeb:
	dh_builddeb -- -Zxz -Sextreme -z9
	#dh_builddeb -- -Zxz -z9
''',
            'compat' : '9'}
        for k, v in fileinfo.items() :
            f = file(os.path.join('debian', k), 'w')
            f.write(v + "\n")
            if k == 'rules' : os.fchmod(f.fileno(), 0775)
            f.close()

        # docs file  (probably needs a conditional on web/ and sources/ too)
        fdocs = file(os.path.join('debian', 'doc'), 'w')
        fdocs.write('''*.txt
documentation/''')
        fdocs.close()

        # watch file
        fwatch = file(os.path.join('debian', 'watch'), 'w')
        fwatch.write('''# access to the tarballs on the release server is not yet automated''')
        fwatch.close()

class graideContext(Build.BuildContext) :
    """Create graide .cfg files, one per font in graide/"""
    cmd = 'graide'

    configstruct = {
        'main' : {
            'font' : ('{0}/{1}', True),
            'testsfile' : ('{5}', True),
            'defaultrtl' : ('0', False),
            'ap' : ('{0}/{2}', True),
            'size' : ('40', False)
        },
        'build' : {
            'gdlfile' : ('{6}', True),
            'usemakegdl' : ('1', True),
            'makegdlfile' : ('{0}/{3}', True),
            'attpass' : ('0', False),
            'makegdlcmd' : ('{4}', True),
            'apronly' : ('1', True)
        },
        'ui' : {
            'textsize' : ('10', False)
        }
    }
    def execute_build(self) :
        graide = getattr(Context.g_module, 'GRAIDE_DIR', 'graide')
        if not os.path.exists(graide) : os.mkdir(graide)
        for p in Package.packages() :
            for f in p.fonts :
                if not hasattr(f, 'graphite') : continue
                base = os.path.basename(f.target)[:-4]
                if hasattr(f.graphite, 'make_params') :
                    makegdl = "make_gdl " + f.graphite.make_params + " -i %i -a %a"
                    if hasattr(f, 'classes') :
                        makegdl += " -c " + os.path.join('..', f.classes)
                    makegdl += " %f %g"
                else :
                    makegdl = ''
                master = os.path.join('..', f.graphite.master) if hasattr(f.graphite, 'master') else ''
                fname = os.path.join(graide, '{}.cfg'.format(base))
                cfg = ConfigParser.RawConfigParser()
                if os.path.exists(fname) :
                    cfg.read(fname)
                changed = False
                for sect in self.configstruct :
                    if not cfg.has_section(sect) :
                        cfg.add_section(sect)
                        changed = True
                    for opt, val in self.configstruct[sect].items() :
                        text = val[0].format(os.path.relpath(self.out_dir, graide),
                                                f.target,
                                                f.ap,
                                                f.graphite.source,
                                                makegdl,
                                                base+"_tests.xml",
                                                master)
                        if not cfg.has_option(sect, opt) or (val[1] and cfg.get(sect, opt) != text) :
                            cfg.set(sect, opt, text)
                            changed = True
                if changed :
                    with open(fname, "w") as fh :
                        cfg.write(fh)


def subdir(path) :
    currpackages = Package.packages()
    currglobal = Package.globalpackage
    Package.initPackages()

    def src(p) :
        return os.path.join(os.path.abspath(path), p)

    mpath = os.path.join(os.path.abspath(path), 'wscript')
    oldsrc = Context.wscript_vars.get('src', None)
    Context.wscript_vars['src'] = src
    #fcode = self.root.find_node(mpath).read('rU')
    #exec_dict = dict(Context.wscript_vars)
    #exec(compile(fcode, mpath, 'exec'), exec_dict)
    Context.load_module(mpath)

    respackages = Package.packages()
    Package.packdict[path] = respackages
    Package.initPackages(currpackages, currglobal)
    Context.wscript_vars['src'] = oldsrc
    return respackages

def ftmlTest(path, **kw) :
    gpackage = Package.global_package()
    gpackage.fontTests.addFtmlTest(path, **kw)

def testCommand(_cmd, **kw) :
    gpackage = Package.global_package()
    gpackage.fontTests.addTestCmd(_cmd, **kw)

def _findvcs(cwd) :
    if cwd == os.path.sep or cwd == '' : return None
    if os.path.exists(os.path.join(cwd, '.git')) :
        return 'git'
    elif os.path.exists(os.path.join(cwd, '.hg')) :
        return 'hg'
    ind = cwd[:-1].rfind(os.path.sep)
    if ind == -1 : return None
    return _findvcs(cwd[:ind])

def getversion(s = "{vcssha:.6}{vcsmodified}") :
    curdir = os.path.abspath(os.curdir)
    results = {'vcsmodified' : ''}
    vcssha = os.environ.get('BUILD_VCS_NUMBER', '')
    if '-r' in sys.argv or '--release' in sys.argv :
    #if Options.options.release :   # Can't use this in wscript since Options.parse_args() not run yet
        vcssha = ''
    elif vcssha != '' :       # in team city, so no vcs dirs available
        pass
    else:
        results['vcstype'] = 'svn' if os.path.exists(os.path.join(curdir, '.svn')) else _findvcs(curdir)

        if results['vcstype'] == 'git' :
            vcssha = Utils.subprocess.check_output(['git', 'rev-parse', 'HEAD'])
            results['vcsmodified'] = 'M' if Utils.subprocess.call(['git', 'diff-index', '--quiet', 'HEAD']) else ""
        elif results['vcstype'] == 'hg' :
            vcssha = Utils.subprocess.check_output(['hg', 'identify', '--id']).strip()
            if vcssha.endswith('+') :
                vcssha = vcssha[:-1]
                results['vcsmodified'] = 'M'
        elif results['vcstype'] == 'svn' :
            # (only in svn 1.9 and above) vcssha = Utils.subprocess.check_output(['svn', 'info', '--show-item=revision'])
            vcssha = Utils.re.search(ur'Revision: (\d+)', Utils.subprocess.check_output(['svn', 'info'])).group(1)
            results['vcsmodified'] = "M" if Utils.subprocess.check_output(['svn', 'status', '-q']) else ""
    results['vcssha'] = vcssha.strip()
    results['buildnumber'] = os.environ.get('BUILD_NUMBER', '')
    return s.format(**results)

def add_configure() :
    old_config = getattr(Context.g_module, "configure", None)

    def subconfig(ctx) :
        progs = set()
        for p in Package.packages() :
            progs.update(p.get_build_tools(ctx))
        for p in progs :
            ctx.find_program(p, var=p.upper())
        ctx.find_program('cp', var='COPY')
        for key, val in Context.g_module.__dict__.items() :
            if key == key.upper() : ctx.env[key] = val

    def configure(ctx) :
        currpackages = Package.packages()
        gm = Context.g_module
        rdir = Context.run_dir
        for k, v in Package.packdict.items() :
            Package.initPackages(v, None)
            c = ctx.__class__()
            c.top_dir = os.path.join(ctx.srcnode.abspath(), k)
            c.out_dir = os.path.join(ctx.srcnode.abspath(), k, ctx.bldnode.srcpath())
            Context.g_module = Context.cache_modules[os.path.join(os.path.abspath(c.top_dir), 'wscript')]
            oconfig = getattr(Context.g_module, 'configure', None)
            def lconfig(ctx) :
                subconfig(ctx)
                if oconfig : oconfig(ctx)
            Context.g_module.configure = lconfig
            Context.run_dir = c.top_dir
            c.execute()
            if oconfig :
                Context.g_module.configure = oconfig
            Context.g_module = gm
            Context.run_dir = rdir
        Package.initPackages(currpackages, None)
        subconfig(ctx)
        if old_config :
            old_config(ctx)

    Context.g_module.configure = configure

def add_build() :
    old_build = getattr(Context.g_module, "build", None)

    def build(bld) :
        bld.post_mode = 1
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.build(bld)
        if old_build : old_build(bld)

    Context.g_module.build = build

def init(ctx) :
    add_configure()
    add_build()

def onload(ctx) :
    varmap = { 'package' : Package, 'subdir' : subdir,
        'ftmlTest' : ftmlTest, 'testCommand' : testCommand,
        'getversion' : getversion }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)
