#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Build, Errors, Node, Options, Logs, Utils
import wafplus
import font, templater 
import os, sys, shutil, time, ConfigParser, subprocess

keyfields = ('copyright', 'version', 'appname', 'desc_short',
            'desc_long', 'outdir', 'zipfile', 'zipdir', 'desc_name',
            'docdir', 'debpkg')
optkeyfields = ('company', 'instdir', 'readme', 'license')

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
            p = Package()
            for k in keyfields :
                setattr(p, k, getattr(Context.g_module, k.upper(), ''))
            for k in optkeyfields :
                v = getattr(Context.g_module, k.upper(), None)
                if v is not None :
                    setattr(p, k, v)
        else :
            p = cls.packagestore[cls.globalpackage]
        for k, v in kw.items() :
            setattr(p, k, v)
        return p

    def __init__(self, **kw) :
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

    def get_build_tools(self, ctx) :
        try :
            ctx.find_program('validator_checker', var="OTS")
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
        return res

    def get_sources(self, ctx) :
        res = []
        self.subrun(ctx, lambda p, c: res.extend(p.get_sources(c)), onlyfn = True)
        licenses = [getattr(self, 'license', 'OFL.txt')]
        if licenses[0] == 'OFL.txt' :
            licenses.extend(['OFL-FAQ.txt', 'FONTLOG.txt'])
        for l in licenses :
            if os.path.exists(l) :
                res.append(l)
            else :
                Logs.error("License file \'" + l + "\' not found.")
        rentry = getattr(self, 'readme', 'README.txt')
        if os.path.exists(rentry) :
            res.append(rentry)
        else :
            Logs.error("Readme file \'" + rentry + "\' not found.")
        for f in self.fonts :
            res.extend(f.get_sources(ctx))
        for k in self.keyboards :
            res.extend(k.get_sources(ctx))
        if hasattr(self, 'docdir') :
            for p, n, fs in os.walk(self.docdir) :
                for f in fs :
                    res.append(os.path.join(p, f))
        return res

    def add_package(self, package, path) :
        if path not in self.subpackages :
            self.subpackages[path] = []
            self.order.append(path)
        for p in package if isinstance(package, list) else (package, ) :
            p.reldir = path
            self.subpackages[path].append(p)

    def add_font(self, font) :
        self.fonts.append(font)

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
            if not getattr(self, 'license', None) : self.license = 'OFL.txt'
            if not os.path.exists(self.license) :
                bld(name = 'Package OFL', rule = methodwrapofl, target = bld.bldnode.find_or_declare(self.license))

    def build_test(self, bld, test='test') :
        self.subrun(bld, lambda p, b: p.build_test(b, test=test))
        for f in self.fonts :
            f.build_test(bld, test=test)
        for k in self.keyboards :
            k.build_test(bld, test=test)

    def build_ots(self, bld) :
        if 'OTS' not in bld.env :
            Logs.error("ots not installed. Can't complete")
            return
        self.subrun(bld, lambda p, b: p.build_ots(b))
        for f in self.fonts :
            f.build_ots(bld)

    def build_exe(self, bld) :
        if 'MAKENSIS' not in bld.env :
            Logs.error("makensis not installed. Can't complete")
            return
        for t in ('appname', 'version') :
            if not hasattr(self, t) :
                raise Errors.WafError("Package '%r' needs '%s' attribute" % (self, t))
        thisdir = os.path.dirname(__file__)
        fonts = [x for x in self.fonts if not hasattr(x, 'dontship')]
        kbds = [x for x in self.keyboards if not hasattr(x, 'dontship')]
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

        self.subrun(bld, procpkg, onlyfn = True)
        task = templater.Copier(prj = self, fonts = fonts, kbds = kbds, basedir = thisdir, env = bld.env, bld = blddir)
        task.set_inputs(bld.root.find_resource(self.exetemplate if hasattr(self, 'exetemplate') else os.path.join(thisdir, 'installer.nsi')))
        for d, x in self.get_files(bld) :
            if not x : continue
            r = os.path.relpath(os.path.join(d, x), bld.bldnode.abspath())
            y = bld.bldnode.find_or_declare(r)
            if os.path.isfile(y and y.abspath()) : task.set_inputs(y)

        task.set_outputs(bld.bldnode.find_or_declare(bname + '.nsi'))
        bld.add_to_group(task)
        bld(rule='${MAKENSIS} -O' + bname + '.log ${SRC}', source = bname + '.nsi', target = '%s/%s-%s.exe' % ((self.outdir or '.'), (self.desc_name or self.appname.title()), self.version))

    def execute_zip(self, bld) :
        if not self.zipfile :
            self.zipfile = "%s/%s-%s.zip" % ((self.zipdir or '.'), self.appname, self.version)

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

        licenses = [getattr(self, 'license', 'OFL.txt')]
        if licenses[0] == 'OFL.txt' :
            licenses.extend(['OFL-FAQ.txt', 'FONTLOG.txt'])
        for l in licenses :
            lentry = self._get_arcfile(bld, l)
            if lentry is not None :
                res.append(lentry)
        rentry = self._get_arcfile(bld, getattr(self, 'readme', 'README.txt'))
        if rentry is not None :
            res.append(rentry)

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

class svgContext(cmdContext) :
    """Create svg test results"""
    cmd = 'svg'

class testContext(cmdContext) :
    """Run basic tests, usually regression tests"""
    cmd = 'test'

class otsContext(cmdContext) :
    """Test fonts using OpenType Sanitizer. Check <font.target>_ots.log"""
    cmd = 'ots'

class crashContext(Context.Context) :
    """Crash and burn with fire"""
    cmd = 'crash'
    def execute(self) :
        Utils.subprocess.Popen("timeout 20 aafire -driver slang ; reset", shell = 1).wait()
 
class srcdistContext(Build.BuildContext) :
    """Create source release of project"""
    cmd = 'srcdist'

    def execute_build(self) :
        self.recurse([self.run_dir], 'srcdist', mandatory = False)
        res = set(['wscript'])
        files = {}
        if Options.options.debug :
            import pdb; pdb.set_trace()
        if os.path.exists('debian') :
            files['debian'] = self.srcnode.find_node('debian')

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
                    vcsbase = subprocess.Popen(["hg", "root"], cwd=d or '.', stdout=subprocess.PIPE).communicate()[0].strip()
                elif vcs == 'svn' or os.path.exists(os.path.join(d, '.svn')) :
                    cmd = ["svn", "list", "-R"]
                if cmd is not None :
                    filelist = subprocess.Popen(cmd, cwd=d or '.', stdout=subprocess.PIPE).communicate()[0]
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
                n = self.bldnode.find_resource(f)
                files[f] = n

        # now generate the tarball
        import tarfile
        tarname = getattr(Context.g_module, 'SRCDIST', None)
        if not tarname :
            tarbase = getattr(Context.g_module, 'APPNAME', 'noname') + "-" + str(getattr(Context.g_module, 'VERSION', "0.0"))
            tarname = tarbase + "-source"
        else :
            tarbase = tarname
        tar = tarfile.open(os.path.join(getattr(Context.g_module, 'out', 'results'), getattr(Context.g_module, 'ZIPDIR', 'releases'), tarname) + '.tar.gz', 'w:gz')
        for f in sorted(files.keys()) :
            if f.startswith('../') : continue
            if files[f] :
                tar.add(files[f].abspath(), arcname = os.path.join(tarbase, f))
        tar.close()

class makedebianContext(Build.BuildContext) :
    """Build Debian/Ubuntu packaging templates for this project"""
    cmd = 'deb-templates'

    def execute_build(self) :
        # check we have all the info we need
        if os.path.exists('debian') : return
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
            bdeps.append('libfont-ttf-scripts-perl, python-palaso, fontforge, grcompiler')
        if hasfonts & 2 :
            bdeps.append('grcompiler')
        if maint : maint = "\nMaintainer: " + maint
        fcontrol = file(os.path.join('debian', 'control'), 'w')
        fcontrol.write('''Source: {0}
Priority: optional
Section: fonts{1}
Build-Depends: debhelper (>= 9~), {2}
Standards-Version: 3.9.6

'''.format(srcname, maint, ", ".join(bdeps)))
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
    Context.wscript_vars['src'] = src
    #fcode = self.root.find_node(mpath).read('rU')
    #exec_dict = dict(Context.wscript_vars)
    #exec(compile(fcode, mpath, 'exec'), exec_dict)
    Context.load_module(mpath)

    respackages = Package.packages()
    Package.packdict[path] = respackages
    Package.initPackages(currpackages, currglobal)
    return respackages

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
    varmap = { 'package' : Package, 'subdir' : subdir }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)