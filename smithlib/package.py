#!/usr/bin/python

from waflib import Context, Build, Errors, Node
import font, templater 
import os, sys, shutil, time

globalpackage = None
def global_package(**kw) :
    global globalpackage
    if not globalpackage :
        globalpackage = Package()
        for k in ('COPYRIGHT', 'LICENSE', 'VERSION', 'APPNAME', 'DESC_SHORT',
                    'DESC_LONG', 'OUTDIR', 'ZIPFILE', 'ZIPDIR', 'DESC_NAME',
                    'DOCDIR', 'DEBPKG') :
            setattr(globalpackage, k.lower(), getattr(Context.g_module, k, ''))
    for k, v in kw.items() :
        setattr(globalpackage, k, v)
    return globalpackage

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

    packages = []
    def __init__(self, **kw) :
        for k, v in kw.items() :
            setattr(self, k, v)
        self.packages.append(self)
        self.fonts = []
        self.keyboards = []

    def get_build_tools(self, ctx) :
        try :
            ctx.find_program('makensis')
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
        for f in self.fonts :
            res.extend(f.get_sources(ctx))
        if hasattr(self, 'docdir') :
            for p, n, fs in os.walk(self.docdir) :
                for f in fs :
                    res.append(os.path.join(p, f))
        return res

    def add_font(self, font) :
        self.fonts.append(font)

    def add_kbd(self, kbd) :
        self.keyboards.append(kbd)

    def add_reservedofls(self, *reserved) :
        if hasattr(self, 'reservedofl') :
            self.reservedofl.update(reserved)
        else :
            self.reservedofl = set(reserved)

    def make_ofl_license(self, task) :
        bld = task.generator.bld
        font.make_ofl(task.outputs[0].srcpath(), self.reservedofl,
                getattr(self, 'ofl_version', '1.1'),
                copyright = getattr(self, 'copyright', ''))
        return 0
        
    def build(self, bld) :

        def methodwrapofl(tsk) :
            return self.make_ofl_license(tsk)

        for f in self.fonts :
            f.build(bld)
        for k in self.keyboards :
            k.build(bld)
        if hasattr(self, 'reservedofl') :
            if not getattr(self, 'license', None) : self.license = 'OFL.txt'
            bld(name = 'Package OFL', rule = methodwrapofl, target = bld.bldnode.find_or_declare(self.license))

    def build_pdf(self, bld) :
        for f in self.fonts :
            f.build_pdf(bld)
        for k in self.keyboards :
            k.build_pdf(bld)

    def build_svg(self, bld) :
        for f in self.fonts :
            f.build_svg(bld)
        for k in self.keyboards :
            k.build_pdf(bld)

    def build_exe(self, bld) :
        if 'MAKENSIS' not in bld.env : return
        for t in ('appname', 'version') :
            if not hasattr(self, t) :
                raise Errors.WafError("Package '%r' needs '%s' attribute" % (self, t))
        thisdir = os.path.dirname(__file__)
        env =   {
            'project' : self,
            'fonts' : self.fonts,
            'kbds' : self.keyboards,
            'basedir' : thisdir
                }
        # create a taskgen to expand the installer.nsi
        bname = 'installer_' + self.appname
        task = templater.Copier(prj = self, fonts = self.fonts, kbds = self.keyboards, basedir = thisdir, env = bld.env)
        task.set_inputs(bld.root.find_resource(os.path.join(thisdir, 'installer.nsi')))
        for f in self.fonts :
            task.set_inputs(bld.bldnode.find_resource(f.target))
        for k in self.keyboards :
            for t in ('target', 'kmx', 'pdf') :
                n = bld.bldnode.find_resource(getattr(k, t, None))
                if n : task.set_inputs(n)
        task.set_outputs(bld.bldnode.find_or_declare(bname + '.nsi'))
        bld.add_to_group(task)
        bld(rule='${MAKENSIS} -O' + bname + '.log ${SRC}', source = bname + '.nsi', target = '%s/%s-%s.exe' % ((self.outdir or '.'), (self.desc_name or self.appname.title()), self.version))

    def execute_zip(self, bld) :
        if not self.zipfile :
            self.zipfile = "%s/%s-%s.zip" % ((self.zipdir or '.'), self.appname, self.version)

        import zipfile
        znode = bld.path.find_or_declare(self.zipfile)      # create dirs
        zip = zipfile.ZipFile(znode.abspath(), 'w', compression=zipfile.ZIP_DEFLATED)

        for x in self.get_files() :
            if not x : continue
            y = bld.path.find_or_declare(x)
            archive_name = self.appname + '-' + str(self.version) + '/' + x
            zip.write(y.abspath(), archive_name, zipfile.ZIP_DEFLATED)
        zip.close()
        
    def get_files(self) :
        res = []
        try: res.append(self.license)
        except: pass
        for f in self.fonts :
            res.append(f.target)
        for k in self.keyboards :
            res.extend([k.target, k.kmx, k.pdf])
        return res

class exeContext(Build.BuildContext) :
    cmd = 'exe'

    def pre_build(self) :
        self.add_group('exe')
        for p in Package.packages :
            p.build_exe(self)

class zipContext(Build.BuildContext) :
    cmd = 'zip'

    def execute_build(self) :
        for p in Package.packages :
            p.execute_zip(self)

class pdfContext(Build.BuildContext) :
    cmd = 'pdfs'
    func = 'pdfs'

    def pre_build(self) :
        self.add_group('pdfs')
        for p in Package.packages :
            p.build_pdf(self)

class svgContext(Build.BuildContext) :
    cmd = 'svg'
    func = 'svg'

    def pre_build(self) :
        self.add_group('svg')
        for p in Package.packages :
            p.build_svg(self)

class srcdistContext(Build.BuildContext) :
    cmd = 'srcdist'

    def execute_build(self) :
        res = set(['wscript'])
        files = {}
        if os.path.exists('debian') :
            files['debian'] = self.srcnode.find_node('debian')
        for p in Package.packages :
            res.update(set(p.get_sources(self)))
        for f in res :
            if not f : continue
            if isinstance(f, Node.Node) :
                files[f.srcpath()] = f
            else :
                n = self.bldnode.find_resource(f)
                files[f] = n
        import tarfile

        tarname = getattr(Context.g_module, 'SRCDIST', 'srcdist')
        tar = tarfile.open(tarname + '.tar.gz', 'w:gz')
        for f in sorted(files.keys()) :
            if f.startswith('../') : continue
            tar.add(files[f].abspath(), arcname = os.path.join(tarname, f))
        tar.close()

class makedebianContext(Build.BuildContext) :
    cmd = 'makedebian'

    def execute_build(self) :
        # check we have all the info we need
        if os.path.exists('debian') : return
        srcname = getattr(globalpackage, 'debpkg', None)
        if not srcname :
            raise Errors.WafError('No debpkg information given to default_package. E.g. set DEBPKG')
        srcversion = getattr(globalpackage, 'version', None)
        if not srcversion :
            raise Errors.WafError('No version information given to default_package. E.g. set VERSION')
        maint = os.getenv('DEBEMAIL')
        if not maint :
            raise Errors.WafError("I don't know who you are, please set the DEBEMAIL environment variable")
        license = getattr(globalpackage, 'license', None)
        if not license :
            raise Errors.WafError("default_package needs a license. E.g. set LICENSE")
        license = self.bldnode.find_resource(license)
        if not license :
            raise Errors.WafError("The license file doesn't exist, perhaps you need to smith build first")

        # .install and .dirs files
        os.makedirs('debian/bin')
        shutil.copy(sys.argv[0], 'debian/bin')
        hasfonts = 0
        haskbds = False
        for p in Package.packages :
            pname = getattr(p, 'debpkg', None)
            if not pname : continue
            fdir = "/usr/share/fonts/truetype/" + pname + "\n"
            fdirs = file(os.path.join('debian', pname + '.dirs'), 'w')
            if len(p.fonts) :
                fdirs.write(fdir)
                hasfonts = hasfonts | 1
            fdirs.close()
            finstall = file(os.path.join('debian', pname + '.install'), 'w')
            for f in p.fonts :
                finstall.write("build/" + f.target + "\t" + fdir)
                if hasattr(f, 'graphite') : hasfonts = hasfonts | 2
            finstall.close()

        # changelog
        fchange = file(os.path.join('debian', 'changelog'), 'w')
        fchange.write('''{0} ({1}) unstable; urgency=low

  * Release

 -- {2}  {3} {4}
'''.format(srcname, srcversion, maint, time.strftime("%a, %d %b %Y %H:%M:%S"), formattz(time.altzone)))
        fchange.close()

        # copyright
        shutil.copy(license.abspath(), os.path.join('debian', 'copyright'))

        # control
        bdeps = []
        if hasfonts & 1 :
            bdeps.append('libfont-ttf-scripts-perl')
        if hasfonts & 2 :
            bdeps.append('grcompiler')
        if maint : maint = "\nMaintainer: " + maint
        fcontrol = file(os.path.join('debian', 'control'), 'w')
        fcontrol.write('''Source: {0}
Priority: optional
Section: fonts{1}
Build-Depends: debhelper (>= 8.0), {2}
Standards-Version: 3.9.1

'''.format(srcname, maint, ", ".join(bdeps)))
        for p in Package.packages :
            pname = getattr(p, 'debpkg', None)
            if not pname : continue
            fcontrol.write('''Package: {0}
Section: fonts
Architecture: all
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
''',
            'compat' : '8'}
        for k, v in fileinfo.items() :
            f = file(os.path.join('debian', k), 'w')
            f.write(v + "\n")
            if k == 'rules' : os.fchmod(f.fileno(), 0775)
            f.close()

def add_configure() :
    old_config = getattr(Context.g_module, "configure", None)

    def configure(ctx) :
        programs = set()
        for p in Package.packages :
            programs.update(p.get_build_tools(ctx))
        programs.update(font.progset)
        for p in programs :
            ctx.find_program(p, var=p.upper())
        ctx.find_program('cp', var='COPY')
        for key, val in Context.g_module.__dict__.items() :
            if key == key.upper() : ctx.env[key] = val
        if old_config :
            old_config(ctx)

    Context.g_module.configure = configure

def add_build() :
    old_build = getattr(Context.g_module, "build", None)

    def build(bld) :
        bld.post_mode = 1
        for p in Package.packages :
            p.build(bld)
        if old_build : old_build(bld)

    Context.g_module.build = build

def init(ctx) :
    add_configure()
    add_build()

def onload(ctx) :
    varmap = { 'package' : Package, 'default_package' : global_package }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)


