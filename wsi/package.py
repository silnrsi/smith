#!/usr/bin/python

from waflib import Context, Build
import font, templater 
import os

globalpackage = None
def global_package() :
    global globalpackage
    if not globalpackage :
        globalpackage = Package()
    return globalpackage

class Package(object) :

    packages = []
    def __init__(self, **kw) :
        for k in ('COPYRIGHT', 'LICENSE', 'VERSION', 'APPNAME', 'DESC_SHORT',
                    'DESC_LONG', 'OUTDIR', 'ZIPFILE', 'ZIPDIR', 'DESC_NAME', 'DOCDIR') :
            setattr(self, k.lower(), getattr(Context.g_module, k, None))
        for k, v in kw.items() :
            setattr(self, k, v)
        if not hasattr(self, 'docdir') : self.docdir = 'docs'
        self.packages.append(self)
        self.fonts = []
        self.keyboards = []

    def get_build_tools(self, ctx) :
        res = set(['makensis'])
        for f in self.fonts :
            res.update(f.get_build_tools(ctx))
        for k in self.keyboards :
            res.update(k.get_build_tools(ctx))
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
        font.make_ofl(task.outputs[0].srcpath(), self.reservedofl, getattr(self, 'ofl_version', '1.1'), copyright = getattr(self, 'copyright', ''))
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
            for t in ('target', 'source', 'pdf') :
                n = bld.bldnode.find_resource(getattr(k, t, None))
                if n : task.set_inputs(n)
        task.set_outputs(bld.bldnode.find_or_declare(bname + '.nsi'))
        bld.add_to_group(task)
        bld(rule='makensis -O' + bname + '.log ${SRC}', source = bname + '.nsi', target = '%s/%s-%s.exe' % ((self.outdir or '.'), (self.desc_name or self.appname.title()), self.version))

    def execute_zip(self, bld) :
        if self.zipfile :
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
            res.extend([k.target, k.source, k.pdf])
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
    varmap = { 'package' : Package }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)


