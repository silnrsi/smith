#!/usr/bin/env python3
from __future__ import absolute_import, print_function
''' package module '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011-2025 SIL Global (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (https://opensource.org/licenses/BSD-3-Clause)'

from waflib import Context, Build, Errors, Node, Options, Logs, Utils
from smithlib.smith import isList, formatvars, create, defer
from smithlib import wafplus, font_tests, font, templater
import os, sys, shutil, time, fnmatch, subprocess, re, json
from xml.etree import ElementTree as et

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

keyfields = ('version', 'appname', 'desc_short',
            'desc_long', 'outdir', 'desc_name', 'docdir')
optkeyfields = ('company', 'instdir', 'zipfile', 'zipdir', 'readme',
            'contact', 'url', 'testfiles', 'buildlabel', 'buildformat',
            'package_files', 'buildversion', 'sile_path', 'sile_scale', 'noalltests')

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

def ascrlf(fname) :
    res = ""
    with open(fname, "r") as f :
        res = "\r\n".join([x.rstrip("\n") for x in f.readlines()]) + "\r\n"
    return res

def prettydict(data, indent, ink, oneline=False, oneliners=None):
    res = ["{"]
    thisoneline = oneline and (oneliners is None or ink not in oneliners)
    for k, v in sorted(data.items()):
        line = ("" if thisoneline else indent) + '"{}": '.format(k)
        if isinstance(v, dict):
            val = prettydict(v, indent + "    ", k,
                             oneline=(oneline if oneliners is None or k not in oneliners else True),
                             oneliners=oneliners)
        else:
            val = json.dumps(v, ensure_ascii=False)
        res.append(line + val + ",")
    res[-1] = res[-1][:-1]
    res.append(("" if thisoneline else indent[:-4]) + "}")
    return (" " if thisoneline else "\n").join(res)

class Package(object) :

    packagestore = []
    packdict = {}
    globalpackage = None
    default_bintypes = ["*.doc*", "*.idml", "*.indd", "*.jp*", "*.mp*", "*.od*", "*.pdf", "*.png", "*.pp*", "*.ttf", "*.woff*", "*.xls*"]

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
        if 'buildversion' not in kw :
            if 'buildformat' not in kw :
                bv = getversion()
            else :
                bv = getversion(buildformat=kw['buildformat'])
            l = kw.get('buildlabel', '')
            if len(l) and bv != '':
                bv = l + " " + bv
            kw['buildversion'] = bv
        bv = kw['buildversion'].replace(" ", "-")
        if 'sile_path' not in kw:
            kw['sile_path'] = os.path.dirname(__file__)
        for k in keyfields :
            if k not in kw: kw[k] = ""

        for k, v in kw.items() :
            setattr(self, k, v)
        self.packagestore.append(self)
        self.fonts = []
        self.keyboards = []
        self.subpackages = {}
        self.reldir = ''
        self.order = []
        self.package = self
        self.fontTests = font_tests.FontTests(**kw)

    def get_build_tools(self, ctx) :
        ctx.find_program('sha512sum', var="CHECKSUMS", mandatory=False)
        ctx.find_program('gpg', var="GPG", mandatory=False)
        ctx.find_program('makefea', var="MAKEFEA", mandatory=False)
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
            for docdir in self.docdir if isList(self.docdir) else [self.docdir]:
                for p, n, fs in os.walk(docdir) :
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

    def build_start(self, bld) :
        self.subrun(bld, lambda p, b: p.build_start(b))
        for f in self.fonts :
            f.build_start(bld)

    def build_fontbakery(self, bld) :
        if 'FONTBAKERY' not in bld.env :
            Logs.warn("fontbakery not installed. Can't complete. See http://github.com/googlefonts/fontbakery")
            return
        self.subrun(bld, lambda p, b: p.build_fontbakery(b))
        for f in self.fonts :
            f.build_fontbakery(bld)

    def build_diffenator2(self, bld) :
        if 'DIFFENATOR2' not in bld.env :
            Logs.warn("diffenator2 not installed. Can't complete.")
            return
        self.subrun(bld, lambda p, b: p.build_diffenator2(b))
        for f in self.fonts :
            f.build_diffenator2(bld)

    def build_checksums(self, bld) :
        if 'CHECKSUMS' not in bld.env :
            Logs.warn("sha512sum not installed. Can't complete.")
            return
        self.subrun(bld, lambda p, b: p.build_checksums(b))
        for f in self.fonts :
            f.build_checksums(bld)

    def build_sign(self, bld) :
        if 'GPG' not in bld.env :
            Logs.warn("gpg not installed. Can't complete.")
            return
        self.subrun(bld, lambda p, b: p.build_sign(b))
        for f in self.fonts :
            f.build_sign(bld)

    def build_buildinfo(self, bld) :
        self.subrun(bld, lambda p, b: p.build_buildinfo(b))
        for f in self.fonts :
            f.build_buildinfo(bld)

    def build_manifest(self, bld):

        self.subrun(bld, lambda p, b: p.build_manifest(b))
        manifest = {}   #'files': {}, 'version': str(self.version)}
        for f in self.fonts:
            files, defaults = f.make_manifest(bld, getattr(f, 'defaultsinaxes', False))
            family = None
            for v in files.values():
                if 'family' in v:
                    family = v['family']
                    del v['family']
            if family is None:
                continue
            famstr = family.lower().replace(" ", "")
            if famstr not in manifest:
                manifest[famstr] = {'files': {}, 'version': str(self.version), 'family': family}
            manifest[famstr]['files'].update(files)
            if len(defaults):
                manifest[famstr].setdefault('defaults', {}).update(defaults)
        mnode = bld.path.find_or_declare('{}_fontmanifest.json'.format(self.appname))
        if len(manifest):
            with open(mnode.abspath(), "w", encoding="utf-8") as outf:
                outf.write(prettydict(manifest, "", None, oneliners=["files"]))
            self.nomanifest = False
        else:
            self.nomanifest = True

    def get_basearc(self, extras="") :
        if self.buildversion != '' :
            return "{0.appname}{1}-{0.version}-{2}".format(self, extras, self.buildversion.replace(" ", "-"))
        else :
            return "{0.appname}{1}-{0.version}".format(self, extras)

    def set_zip(self) :
        if not hasattr(self, 'zipfile') :
            self.zipfile = "{}/{}.zip".format(self.zipdir, self.get_basearc())

    def execute_tar(self, bld) :
        import tarfile
        self.set_zip()
        tnode = bld.path.find_or_declare(self.zipfile.replace(".zip", ".tar.xz"))
        tar = tarfile.open(tnode.abspath(), "w:xz")
        basearc = self.get_basearc()
        for t in sorted(self.get_files(bld), key=lambda x:x[1]) :
            d, x = t[0], t[1]
            if not x : continue
            r = os.path.relpath(os.path.join(d, x), bld.bldnode.abspath())
            y = bld.path.find_or_declare(r)
            archive_name = os.path.join(basearc, t[2] if len(t) > 2 else x)
            if not archive_name.startswith('..') :
                tar.add(y.abspath(), arcname = archive_name)
        tar.close()

    def execute_zip(self, bld) :
        import zipfile
        self.set_zip()
        znode = bld.path.find_or_declare(self.zipfile)      # create dirs
        zip = zipfile.ZipFile(znode.abspath(), 'w', compression=zipfile.ZIP_DEFLATED)
        zipfiles  = set()
        basearc = self.get_basearc()
        self.build_manifest(bld)

        for t in sorted(self.get_files(bld), key=lambda x:x[2] if len(x) > 2 else x[1]) :
            d, x = t[0], t[1]
            if not x : continue
            r = os.path.relpath(os.path.join(d, x), bld.bldnode.abspath())
            y = bld.path.find_or_declare(r)
            archive_name = os.path.join(basearc, t[2] if len(t) > 2 else x)
            if os.path.isfile(y.abspath()) :
                if archive_name in zipfiles:
                    continue
                if self.isTextFile(r) :
                    try:
                        s = ascrlf(y.abspath())
                        zip.writestr(archive_name, s, zipfile.ZIP_DEFLATED)
                    except UnicodeDecodeError as e:
                        print("Badly encoded file {}, {}. Storing as binary".format(r, str(e)))
                        zip.write(y.abspath(), archive_name, zipfile.ZIP_DEFLATED)
                    inf = zip.getinfo(archive_name)
                    inf.internal_attr = 1
                else :
                    zip.write(y.abspath(), archive_name, zipfile.ZIP_DEFLATED)
                    inf = zip.getinfo(archive_name)
                inf.external_attr = 0
                inf.create_system = 0   # pretend we are windows
                zipfiles.add(archive_name)
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

    def get_built_files(self, bld) :
        res = []
        self.subrun(bld, lambda p, c: res.extend(p.get_built_files(c)), onlyfn = True)
        for f in self.fonts :
            if not hasattr(f, 'dontship') :
                res.extend((bld.out_dir, x) for x in f.get_targets(bld))
        for k in self.keyboards :
            if not hasattr(k, 'dontship') :
                res.extend((bld.out_dir, x) for x in k.get_targets(bld))
        return res

    def get_files(self, bld) :
        """ Returns a list of files to go into the generated zip for this package.
            Each entry in the list is (x, y, z) where:
                x is the base path from which the path to y is relative
                y is the path to the file to include
                z is optional and is the full file path to use in the archive
        """
        # This should be refactored to minimise boilerplate in callers
        res = set()
        self.subrun(bld, lambda p, c: res.update(p.get_files(c)), onlyfn = True)

        res.update([(bld.out_dir, x) for x in self.best_practise_files(self.fonts, self.keyboards)])
        res.discard((bld.out_dir, 'README.md'))
        res.update(self.get_built_files(bld))
        if not getattr(self, 'nomanifest', True):
            res.add((bld.out_dir, "{}_fontmanifest.json".format(self.appname), 'fontmanifest.json'))

        def docwalker(base, topout, topin, dpath, dname, fname) :
            if len(dname):
                while dname[0].startswith("."):
                    dname.pop(0)
            prefout = os.path.relpath(topout, base)
            for x in fname:
                if x.startswith(".") or not os.path.isfile(os.path.join(dpath, x)):
                    continue
                lpath = os.path.relpath(os.path.join(dpath, x), topin)
                res.add((topin, lpath, os.path.join(prefout, lpath)))
        if self.docdir :
            if isList(self.docdir):
                docdirs = {x:x for x in self.docdir}
            elif hasattr(self.docdir, 'keys'):
                docdirs = self.docdir
            else:
                docdirs = {self.docdir: self.docdir}
            for din, dout in docdirs.items():
                yout = bld.bldnode.search(dout)
                yin = bld.bldnode.search(din)
                if yin is not None :
                    for x in os.walk(yin.abspath(), topdown=True):
                        docwalker(bld.bldnode.abspath(), yout.abspath(), yin.abspath(), *x)
                yin = bld.srcnode.find_node(din)
                yout = bld.srcnode.search(dout)
                if yin is not None :
                    for x in os.walk(yin.abspath(), topdown=True):
                        docwalker(bld.srcnode.abspath(), yout.abspath(), yin.abspath(), *x)
        if hasattr(self, 'package_files'):
            extras = []
            for k, v in self.package_files.items():
                files = [(bld.srcnode.abspath(), os.path.relpath(x.abspath(), bld.srcnode.abspath())) for x in bld.srcnode.ant_glob(k)]
                files.extend((bld.bldnode.abspath(), os.path.relpath(x.abspath(), bld.bldnode.abspath())) for x in bld.bldnode.ant_glob(k))
                pathbits = k.split("/")
                for i, p in enumerate(pathbits):
                    if '*' in p:
                        break
                else:
                    i = len(pathbits) - 1
                numpath = i
                for p, f in files:
                    if v is None:
                        r = f
                    elif '*.' in v:
                        r = v.replace('*.', os.path.splitext(os.path.basename(f))[0])
                    elif '*' in v:
                        r = v.replace('*', os.path.basename(f))
                    elif v[-1] == '/':
                        bits = f.split("/")[numpath:]
                        r = os.path.join(v[:-1], *bits)
                    else:
                        r = v
                    for t in res:
                        if t[1] == f:
                            res.remove(t)
                            break
                    extras.append((p, f, r))
            res.update(extras)
        return res

    def isTextFile(self, f) :
        for p in self.default_bintypes + getattr(self, 'binarytypes', []) :
            if fnmatch.fnmatch(f, p) :
                return False
        return True

def simplestr(txt):
    return re.sub(r"\.0*$", r"", str(txt))

DSAxesMappings = {
    "weight": "wght",
    "width": "wdth",
    "optical": "opsz",
    "slant": "slnt",
    "italic": "ital"
}

class _Axis(dict):
    def __init__(self, name, tag, default):
        super().__init__()
        self.name = name
        self.tag = tag
        try:
            self.default = float(default)
        except ValueError:
            self.default = 0.

    def __str__(self):
        return self.tag

    def __hash__(self):
        return hash((self.name, self.tag))

    def addmapping(self, inp, outp):
        # Invert the mapping because that's how it really works
        self[float(outp)] = float(inp)

    def isDefault(self, vals):
        return vals[0] == self.default

class _DSSource(object):
    def __init__(self, **kw):
        for k,v in kw.items():
            setattr(self, k, v)
        self.locations = {}
        self.defaults = {}

    def addFloatLocation(self, name, axis, values):
        if axis is None:
            self.locations[name] = [float(x) if x is not None else None for x in values]
        else:
            val = [axis.get(float(x), float(x)) if x is not None else None for x in values]
            self.locations[name] = val
            self.defaults[name] = axis.isDefault(val)

    def same(self, other):
        if len(self.locations) != len(other.locations):
            return False
        if self.name != other.name:
            return False
        if self.familyname != other.familyname:
            return False
        if self.stylename != other.stylename:
            return False
        for k, v in self.locations.items():
            if other.locations[k] != v:
                return False
        return True

    def asDict(self):
        res = {}
        for k, v in self.locations.items():
            if isinstance(v, list):
                v = [x for x in v if x is not None]
                if len(v) == 1:
                    v = v[0]
                elif len(v) == 0:
                    v = None
            if v is not None:
                res[k] = v
        return res

    def isDefault(self):
        return all(self.defaults.values())

def read_plist(fname):
    res = {}
    doc = et.parse(fname)
    plist = doc.getroot()[0]
    for i in range(len(plist), 0, 2):
        res[plist[i].text] = plist[i+1]
    return res


def _let(ex, **kw):
    return eval(ex, globals(), kw)
let = defer(_let)

class DesignSpace(object):
    _modifiermap = {'DASH': lambda x: x.replace(' ', '-'),
                    'BASE': lambda x: os.path.splitext(os.path.basename(x))[0],
                    'NOSPC': lambda x: x.replace(' ', '')}

    def __init__(self, dspace, *k, **kw):
        self.dspace = dspace
        self.kw = kw
        self.fonts = []
        self.axesmap = {}
        self.makefonts()
        self.isbuilt = False

    def makefonts(self):
        self.doc = et.parse(self.dspace)
        self.srcs = {}
        for axis in self.doc.getroot().findall('axes/axis'):
            k = axis.get('name', None)
            v = axis.get('tag', None)
            d = axis.get('default', None)
            a = _Axis(k, v, d)
            if k is not None and v is not None:
                self.axesmap[k] = a
                for m in axis.findall('map'):
                    a.addmapping(m.get("input", 0), m.get("output", 0))
        allaxes = {}
        for src in self.doc.getroot().findall('.//sources/source'):
            sfont = _DSSource(**src.attrib)
            for d in src.findall('./location/dimension'):
                val = (d.get('xvalue', None), d.get("yvalue", None))
                sfont.addFloatLocation(d.get('name'), None, val)
                allaxes.setdefault(d.get('name'), set()).add(val)
            self.srcs[sfont.name] = sfont
        self.delaxis = set([k for k, v in allaxes.items() if len(v) < 2 and k != "weight"])
        for inst in self.doc.getroot().findall('instances/instance'):
            if self.kw.get('instances', None) is None or inst.get('name') in self.kw['instances']:
                self._makefont(inst, True)

    def _makefont(self, inst, isInstance):
        base = os.path.dirname(self.dspace)
        specialvars = dict(("DS:"+k.upper(), v) for k,v in inst.attrib.items())
        copyvars = specialvars.copy()
        specialvars.update((k+"_"+mk, mv(v)) for k,v in copyvars.items() for mk, mv in self._modifiermap.items())
        specialvars.update(("DS:AXIS_"+e.get("name", "").upper(), e.get("xvalue", "")) for e in inst.findall('location/dimension'))
        specialvars['DS:FILE'] = os.path.join(base, specialvars['DS:FILENAME'])
        # we can insert all kinds of useful defaults in here
        newkw = {}
        if 'source' not in self.kw:
            if isInstance:
                srcinst = self.srcs.get(inst.get('name'), None)
                fsrc = _DSSource(**inst.attrib)
                for d in inst.findall("./location/dimension"):
                    fsrc.addFloatLocation(d.get('name'), self.axesmap.get(d.get('name'), None),
                                          [d.get('xvalue', None), d.get("yvalue", None)])
                newkw.setdefault('axes', {}).setdefault('axes', self.kw.get('axes', {}).copy()).update(
                        {str(self.axesmap.get(k, DSAxesMappings.get(k, k))): v for k, v in fsrc.asDict().items() if k not in self.delaxis})
                familyname = inst.get('familyname')
                smfn = inst.get('stylemapfamilyname', familyname)
                newkw['axes']['family'] = familyname
                newkw['axes'].setdefault('axes', {})['ital'] = 1 if 'italic' in inst.get('stylename', '').lower() else 0
                newkw['defaultsinaxes'] = fsrc.isDefault() and not newkw['axes']['axes']['ital']
                if familyname != smfn:
                    newkw['axes']['altfamily'] = smfn
                if self.kw.get('shortcircuit', True) and 'name' in inst.attrib and srcinst is not None:
                    mfont = self.srcs[inst.get('name')]
                    masterFName = os.path.join(base, mfont.filename)
                    for sub in ('kern', 'glyphs', 'info', 'lib', 'familyname', 'stylename', 'stylemapstylename', 'stylemapfamilyname'):
                        if inst.find(sub) is not None and len(inst.find(sub)) > 0:
                            mightbeSame = False
                            break
                    mightbeSame = srcinst.same(fsrc)
                    if mightbeSame:
                        fplist = read_plist(os.path.join(masterFName, 'fontinfo.plist'))
                        for sub in ('styleMapStyleName', 'styleMapFamilyName', 'postscriptFontName'):
                            att = inst.get(sub.lower(), "")
                            if not len(att):
                                continue
                            v = fplist.get(sub, None)
                            if v is not None and v.text != att:
                                mightbeSame = False
                                break
                    if mightbeSame:
                        parmvar = self.kw.get('instanceparams', '')
                        if '-W' in parmvar or '--fixweight' in parmvar:
                            wt = int(fplist.get('openTypeOS2WeightClass', "0"))
                            st = fplist.get('styleMapStyleName', fplist.get('styleName', '')).lower()
                            if (st.startswith('bold') and wt != 700) or wt != 400:
                                mightbeSame = False
                    if mightbeSame:
                        newkw['source'] = masterFName
                if 'source' not in newkw:
                    newkw['source'] = font.DesignInstance(self, specialvars['DS:FILE'], specialvars['DS:NAME'],\
                                                          self.dspace, params=self.kw.get('instanceparams', ''))
            else:
                newkw['source'] = specialvars['DS:FILENAME']
        specialvars['source'] = formatvars(getattr(newkw['source'], 'target', newkw['source']), specialvars)
        newkw.update(dict((k, formatvars(v, specialvars)) for k,v in list(self.kw.items()) if k != 'axes'))
        self.fonts.append(font.Font(**newkw))

def make_srcdist(self) :
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
            if vcs == 'git' or os.path.exists(os.path.join(d, '.git')) :
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
        tarbase = Package.global_package().get_basearc(extras="-src")
        tarname = tarbase
    else :
        tarbase = tarname
    tarfilename = os.path.join(getattr(Context.g_module, 'ZIPDIR', 'releases'), tarname) + '.tar.xz'
    tnode = self.path.find_or_declare(tarfilename)
    tar = tarfile.open(tnode.abspath(), 'w:xz')
    incomplete = False

    for f in sorted(files.keys()) :
        if f.startswith('../') :
            Logs.warn('Sources will not include file: ' + f)
            incomplete = True
            continue
        if files[f] :
            tar.add(files[f].abspath(), arcname = os.path.join(tarbase, f))
    tar.close()
    Logs.warn('Tarball .tar.xz (-src- source release) generated.')
    if incomplete :
        Logs.error("Not all the sources for the project have been included in the tarball(s) so the wscript in it will not build.")


class zipContext(Build.BuildContext) :
    """Create release zip of build results"""
    cmd = 'zip'

    def post_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_zip(self)
            Logs.warn('.zip with build results generated (CR+LF line-endings).')

class tarContext(Build.BuildContext) :
    """Create release tarball of build results"""
    cmd = 'tarball'

    def post_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_tar(self)
            Logs.warn('.tar.xz with build results generated (LF line-endings).')

class releaseContext(Build.BuildContext) :
    """Create release zip and tarball of build results"""
    cmd = 'release'

    def pre_recurse(self, node) :
        super(releaseContext, self).pre_recurse(node)
        sys.argv.append('-r')
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.buildversion = ''

    def post_build(self) :
        if Options.options.debug :
            import pdb; pdb.set_trace()
        for p in Package.packages() :
            p.execute_zip(self)
            Logs.warn('.zip release with build results generated (CR+LF line-endings).')
            p.execute_tar(self)
            Logs.warn('.tar.xz release with build results generated (LF line-endings).')

        # checksums are also created as part of the release target
        checkpath = os.path.join(self.out_dir + '/' + (getattr(Context.g_module, 'ZIPDIR', 'releases')))
        os.chdir(checkpath)
        names = [n for n in os.listdir(checkpath) if not fnmatch.fnmatch(n, '*.txt') if not fnmatch.fnmatch(n, '*-dev-*')]
        if len(names) > 0:
            subprocess.call(['sha512sum'] + names, stdout=open("SHA512SUMS.txt","w"))
            Logs.warn('Checksums file SHA512SUMS.txt generated for all released artifacts.')

class checksumsContext(Build.BuildContext) :
    """Provide separate checksum file SHA512SUMS.txt for all released artifacts"""
    cmd = 'checksums'

    @staticmethod
    def _excluded(n) :
        return '-dev-' in n or n.endswith('.txt')

    def execute(self) :
        checkpath = os.path.join(self.out_dir + '/' + (getattr(Context.g_module, 'ZIPDIR', 'releases')))
        os.chdir(checkpath)
        names = [n for n in os.listdir(checkpath) if not self._excluded(n)] 
        if len(names) > 0:
            subprocess.call(['sha512sum'] + names, stdout=open("SHA512SUMS.txt","w"))
            Logs.warn('Checksums file SHA512SUMS.txt generated for all released artifacts.')

class signContext(Build.BuildContext) :
    """Provide PGP/GPG signatures files for artifacts"""
    cmd = 'sign'
    def execute(self) :
        checkpath = os.path.join(self.out_dir + '/' + (getattr(Context.g_module, 'ZIPDIR', 'releases')))
        os.chdir(checkpath)
        Utils.subprocess.call("gpg --armor --detach-sign SHA512SUMS.txt",  shell = 1)
        for file in os.listdir(checkpath) :
            if not file.endswith('.asc') :
                    cmd = ["gpg", "--verbose", "--armor", "--detach-sign", file]
                    Utils.subprocess.call(cmd)
        Logs.warn('Detached signature .asc files (PGP/GPG) generated for all available artifacts.')

class buildinfoContext(Build.BuildContext) :
    """Provide requirements.txt and BUILDINFO.txt for toolchain component versions"""
    cmd = 'buildinfo'

    def execute(self) :
        checkpath = os.path.join(self.out_dir + '/')
        os.chdir(checkpath)
        subprocess.call(["dpkg-query -W -f '${binary:Package}:\t${Version}\t(${Architecture})\tdependencies: ${Depends}\t${binary:Summary}\t${Homepage}\n\n'"], shell = 1, stdout=open("BUILDINFO.txt","w"))
        subprocess.call(["pip3 freeze"], shell = 1, stdout=open("requirements.txt","w"))
        Logs.warn('Toolchain component versions BUILDINFO.txt and requirements.txt generated.')

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

class crashContext(Context.Context) :
    """Crash and burn with fire"""
    cmd = 'crash'
    def execute(self) :
        Utils.subprocess.Popen("timeout 20 aafire -driver slang ; reset", shell = 1).wait()

class versionContext(Context.Context) :
    """Find out which version of smith (waf) is installed"""
    cmd = 'version'
    def execute(self) :
        Logs.warn('Version of smith (via pip):')
        Utils.subprocess.Popen("python3 -m pip show smith | grep --colour=never Version ", shell = 1).wait()
        Logs.warn('Version of waf:')
        Utils.subprocess.Popen("smith --version", shell = 1).wait()

class startContext(Context.Context):
    """start: create project template folder structure"""
    cmd = 'start'
    def execute(self):
        thisdir = os.path.join(os.path.dirname(__file__), 'templates')
        folders = ('documentation', 'tools', 'tests', 'web')
        for f in folders:
            if not os.path.exists(f):
                os.mkdir(f)
                print("Updating missing template folder: {}".format(f))
        files = dict([(x, x) for x in ('wscript', 'OFL.txt', 'OFL-FAQ.txt', 'FONTLOG.txt', 'README.md', 'README.txt')])
        files.update([('dot.gitattributes', '.gitattributes'), ('dot.gitignore', '.gitignore')])
        for f,o in list(files.items()) :
            if not os.path.exists(o):
                try:
                    shutil.copy(os.path.join(thisdir, f), o)
                except EnvironmentError:
                    print("Error, could not copy/update %s %s" % (f, o))
                else:
                    print("Updating missing template file: %s"  % (f))
        Logs.warn('This project has been smith-ified: any missing standard folders and template files have been added.\nPersonalize the templates and run "smith configure".')

class fbcheckContext(Context.Context) :
    """Run fontbakery checks using the profile in pysilfont."""
    cmd = 'fbchecks'
    def execute(self) :
        outputpath = getattr(Context.g_module, 'out', 'results')
        toppath = getattr(Context.g_module, 'top', '.')
        for files in os.listdir(outputpath):
            if files.endswith('-Regular.ttf'):
                familynames = files.split("-")
                fullfamilynames = familynames[0]
                if os.path.exists(toppath + "/fontbakery.yaml"):
                    print("Running Font Bakery using the local fontbakery.yaml profile on family: " + fullfamilynames + "...")
                    Utils.subprocess.Popen("fontbakery check-profile silfont.fbtests.profile " + outputpath + "/" + fullfamilynames + "-*.ttf" + " --config " + toppath + "/fontbakery.yaml" + " --html " + outputpath + "/fontbakery-report-" + fullfamilynames + ".html" + " -q -S -F -C -j", shell = 1).wait()
                    print("Done, see the generated HTML report for all the details.")
                else:
                    print("Running Font Bakery using the pysilfont profile on family: " + fullfamilynames + "...")
                    Utils.subprocess.Popen("fontbakery check-profile silfont.fbtests.profile " + outputpath + "/" + fullfamilynames + "-*.ttf" + " --html " + outputpath + "/fontbakery-report-" + fullfamilynames + ".html" + " -q -S -F -C -j", shell = 1).wait()
                    print("Done, see the generated HTML report for all the details.")

class differContext(Context.Context) :
    """Run diffenator2 for regression testing."""
    cmd = 'differ'
    def execute(self) :
        outputpath = getattr(Context.g_module, 'out', 'results')
        refpath = getattr(Context.g_module, 'STANDARDS', 'references')
        testspath = getattr(Context.g_module, 'TESTDIR', 'tests')
        if not os.path.exists(refpath):
            print("Stopping, no reference font files to diff against. Please add the font files from your last release to the {} folder.".format(refpath))
        else:
            # need to find a way to get new wordlists from tests/ as param using testpath 
            Utils.subprocess.Popen("diffenator2 diff --fonts-before " + refpath + "/*.ttf " + "--fonts-after " + outputpath + "/*.ttf " + "--out " + outputpath + "/diffenator2/", shell = 1).wait()
            Utils.subprocess.Popen("rm -fv build.ninja .ninja_log", shell = 1).wait()

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
                cfg = configparser.RawConfigParser()
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

def testFile(tgt, *cmds, **kws):
    c = create(tgt, *cmds, **kws)
    gpackage = Package.global_package()
    gpackage.fontTests.addTestFile(c)

def _findvcs(cwd) :
    if cwd == os.path.sep or cwd == '' : return None
    if os.path.exists(os.path.join(cwd, '.git')) :
        return 'git'
    elif os.path.exists(os.path.join(cwd, '.hg')) :
        return 'hg'
    ind = cwd[:-1].rfind(os.path.sep)
    if ind == -1 : return None
    return _findvcs(cwd[:ind])

def getversion(buildformat="dev-{vcssha:.6}{vcsmodified}") :
    curdir = os.path.abspath(os.curdir)
    results = {'vcsmodified' : ''}
    vcssha = os.environ.get('BUILD_VCS_NUMBER', '')
    if '-r' in sys.argv or '--release' in sys.argv :
    #if Options.options.release :   # Can't use this in wscript since Options.parse_args() not run yet
        return ''
    elif vcssha != '' :       # in team city, so no vcs dirs available
        pass
    else:
        results['vcstype'] = 'svn' if os.path.exists(os.path.join(curdir, '.svn')) else _findvcs(curdir)

        if results['vcstype'] == 'git' :
            vcssha = Utils.subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode("ascii")
            results['vcsmodified'] = 'M' if Utils.subprocess.call(['git', 'diff-index', '--quiet', 'HEAD']) else ""
        elif results['vcstype'] == 'hg' :
            vcssha = Utils.subprocess.check_output(['hg', 'identify', '--id']).decode("ascii").strip()
            if vcssha.endswith('+') :
                vcssha = vcssha[:-1]
                results['vcsmodified'] = 'M'
        elif results['vcstype'] == 'svn' :
            # (only in svn 1.9 and above) vcssha = Utils.subprocess.check_output(['svn', 'info', '--show-item=revision'])
            vcssha = Utils.re.search(r'Revision: (\d+)', Utils.subprocess.check_output(['svn', 'info'])).group(1).decode("ascii")
            results['vcsmodified'] = "M" if Utils.subprocess.check_output(['svn', 'status', '-q']) else ""
    results['vcssha'] = vcssha.strip()
    results['buildnumber'] = os.environ.get('BUILD_NUMBER', '')
    return buildformat.format(**results)

def getufoinfo(ufosrc, package=None):
    root = et.parse(os.path.join(ufosrc, "fontinfo.plist"))
    d = root.getroot()[0]
    info = dict((x[0].text, x[1].text) for x in zip(d[::2], d[1::2]))
    majver = 0
    minver = 0
    extra = ""
    m = re.match(r'^version (\d+)\.(\d{3});?\s*(.*)$', info.get('openTypeNameVersion', ''), flags=re.I)
    if m is not None:
        majver = int(m.group(1))
        minver = int(m.group(2))
        if m.group(3) is not None:
            extra = re.sub(r'\s*dev-.*?\s*', '', m.group(3), flags=re.I)
    if 'versionMajor' in info:
        majver = int(info['versionMajor'])
    if 'versionMinor' in info:
        minver = int(info['versionMinor'])
    if package is None:
        import inspect
        caller = inspect.stack()[1]
        caller[0].f_locals.update({'VERSION': "{:d}.{:03d}".format(majver, minver),
                                   'BUILDLABEL': extra})
    else:
        package.version = "{:d}.{:03d}".format(majver, minver)
        package.buildlabel = extra

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
        for k, v in list(Package.packdict.items()) :
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
    varmap = { 'package': Package, 'subdir': subdir,
        'ftmlTest': ftmlTest, 'testCommand': testCommand,
        'getversion': getversion, 'getufoinfo': getufoinfo,
        'designspace': DesignSpace, 'testFile' : testFile,
        'let': let }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)
