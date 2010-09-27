#!/usr/bin/python

from waflib import Context, Task, Build, Logs
from waflib.TaskGen import feature, after
import font_tests, templater
import sys, os, re

def add_depend_after(base) :
    old_runnable_status = base.runnable_status
    old_post_run = base.post_run

    def runnable_status(self) :
        state = old_runnable_status(self)
        if state == Task.SKIP_ME and getattr(self, 'depend_after', None) :
            for t in self.depend_after :
                if t.hasrun == Task.SUCCESS :
                    state = Task.RUN_ME
                    break
        return state

    def set_depend_after(self, t) :
        if getattr(self, 'depend_after', None) :
            self.depend_after.append(t)
        else :
            self.depend_after = [t]
        self.set_run_after(t)       # can't run before t

#    def post_run(self) :
#        old_post_run(self)
#        try :
#            for t in self.depend_after :
#                t.post_run()
#        except :
#            pass

    base.runnable_status = runnable_status
    base.set_depend_after = set_depend_after
#    base.post_run = post_run

@feature('*')
@after('process_rule')
def process_tempcopy(tgen) :
    import os, shutil
    if not getattr(tgen, 'tempcopy', None) : return

    (tmpnode, outnode) = tgen.tempcopy
    tmpnode.parent.mkdir()
    for t in tgen.tasks :
        t.tempcopy = tgen.tempcopy
        fn = t.__class__.run
        def f(self) :
            if os.path.exists(tmpnode.abspath()) :
                os.remove(tmpnode.abspath())
#            sys.stderr.write(outnode.abspath() + "-->" + tmpnode.abspath())
            if os.path.exists(outnode.abspath()) :
                shutil.move(outnode.abspath(), tmpnode.abspath())
            else :
                sourcenode = outnode.get_src()
                shutil.copy2(sourcenode.abspath(), tmpnode.abspath())
                t.outputs.append(outnode)
            ret = fn(self)
            if not ret : os.remove(tmpnode.abspath())
            return ret
        t.__class__.run = f

class Font(object) :
    fonts = []

    def __init__(self, *k, **kw) :
        if not 'id' in kw :
            kw['id'] = kw['test_suffix'] if 'test_suffix' in kw else kw['target'].lower().replace('.ttf','')
        self.volt_params = ""
        self.gdl_params = ""

        for k, item in kw.items() :
            setattr(self, k, item)
        self.fonts.append(self)

    def get_build_tools(self) :
        res = set()
        if getattr(self, 'source', "").endswith(".sfd") :
            res.add('fontforge')
            res.add('sfdmeld')
            if getattr(self, 'source_ap', None) :
                res.add('sfd2ap')
        if getattr(self, 'legacy', None) :
            res.add('ttfbuilder')
        if getattr(self, 'classes', None) :
            res.add('add_classes')
        if getattr(self, 'gdl_source', None) or getattr(self, 'gdl_master', None):
            res.add('grcompiler')
            res.add('make_gdl')
        if getattr(self, 'volt_source', None) :
            res.add('volt2ttf')
            res.add('make_volt')
        return res

    def build(self, bld) :
        res = {}

        # convert from legacy
        if getattr(self, 'legacy', None) :
            cmd = ""
            srcs = [self.legacy, self.legacy_xml]
            if getattr(self, 'legacy_ap', None) :
                srcs.append(self.legacy_ap)
                cmd += " -x ${SRC[2].bldpath()}"
            trgt = [re.sub(r'\..*', '.ttf', self.source)]
            if getattr(self, 'source_ap', None) :
                trgt.append(self.source_ap)
                cmd += " -z ${TGT[1].abspath()}"
            leggen = bld(rule = "${TTFBUILDER} -c ${SRC[1].bldpath()}" + cmd + " ${SRC[0].bldpath()} ${TGT[0].abspath()}", source = srcs, target = trgt)
            res[trgt[0]] = leggen
            if len(trgt) > 1 : res[trgt[1]] = leggen
            if self.source.endswith(".sfd") :
                ffgen = bld(rule = "${FONTFORGE} -nosplash -lang=ff -c 'Open($1); Save($2)' ${SRC} ${TGT}", source = trgt[0], target = self.source, shell = 1)
                res[self.source] = ffgen

        # build font
        if self.source.endswith(".ttf") :
            bgen = bld(rule = "${COPY} ${SRC} ${TGT}", source = self.source, target = self.target)
        else :
            srcnode = bld.path.find_or_declare(self.source)
            if getattr(self, "sfd_master", None) and self.sfd_master != self.source:
                tarnode = srcnode.get_bld()
                modify("${SFDMELD} ${SRC} ${DEP} ${TGT}", self.source, [self.sfd_master], before = self.target)
                srcnode = tarnode
            bgen = bld(rule = "${FONTFORGE} -lang=ff -c 'Open($1); Generate($2)' ${SRC} ${TGT}", source = srcnode, target = self.target)
        res[self.target] = bgen

        # add smarts
        if getattr(self, 'source_ap', None) and self.source.endswith(".sfd") :
            agen = bld(rule = "${SFD2AP} ${SRC} ${TGT}", source = self.source, target = self.source_ap)
            res[self.source_ap] = agen
        if getattr(self, 'classes', None) :
            cgen = modify("${ADD_CLASSES} -c ${SRC} ${DEP} > ${TGT}", self.source_ap, [self.classes], shell = 1)
        
        # add OT
        if getattr(self, 'volt_source', None) :
            cmd = getattr(self, 'make_volt_params', "") + " "
            ind = 0
            srcs = []
            if getattr(self, 'source_ap', None) :
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                srcs.append(self.source_ap)
                ind += 1
            if getattr(self, 'volt_master', None) :
                cmd += "-i ${SRC[" + str(ind) + "].bldpath()} "
                srcs.append(self.volt_master)
                ind += 1
            vgen = bld(rule = "${MAKE_VOLT} " + cmd + "-t " + bld.path.find_or_declare(self.target).bldpath() + " > ${TGT}", shell = 1, after = [res[self.target]], source = srcs, target = self.volt_source)
            res[self.volt_source] = vgen
            vtgen = modify("${VOLT2TTF} " + self.volt_params + " -t ${SRC} ${DEP} ${TGT}", self.target, [self.volt_source])

        # add graphite
        if getattr(self, 'gdl_source', None) :
            srcs = []
            cmd = getattr(self, 'make_gdl_params', '') + " "
            ind = 0
            if getattr(self, 'source_ap', None) :
                cmd += "-a ${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
                srcs.append(self.source_ap)
            if getattr(self, 'gdl_master', None) :
                cmd += "-i ../${SRC[" + str(ind) + "].bldpath()} "
                ind += 1
                srcs.append(self.gdl_master)
            ggen = bld(rule = "${MAKE_GDL} " + cmd + bld.path.find_or_declare(self.target).bldpath() + " ${TGT}", shell = 1, after = [res[self.target]], source = srcs, target = self.gdl_source)
            res[self.gdl_source] = ggen
            gtgen = modify("${GRCOMPILER} " + self.gdl_params + " ${SRC} ${DEP} ${TGT}", self.target, [self.gdl_source])
        elif getattr(self, 'gdl_master', None) :
            gtgen = modify("${GRCOMPILER} " + self.gdl_params + " ${SRC} ${DEP} ${TGT}", self.target, [self.gdl_master])

        return self

modifications = {}
rules = []

def modify(cmd, infile, inputs = [], shell = 0, **kw) :
    # can't create taskgens here because we have no bld context
    if not infile in modifications :
        modifications[infile] = []
    if not len(inputs) : shell = 1      # workaround assert in Task.py
    modifications[infile].append((cmd, inputs, shell, kw))

def rule(cmd, inputs, outputs, shell = 0, **kw) :
    rules.append((cmd, inputs, outputs, shell, kw))

def make_tempnode(n, bld) :
    path = ".tmp" + os.sep + n.get_bld().bld_dir()
    tdir = bld.bldnode.abspath() + os.sep + path
    if not os.path.exists(tdir) :
        os.makedirs(tdir, 0771)
    res = bld.bldnode.find_or_declare(path + os.sep + n.name)
    return res

def build_modifys(bld) :
    count = 0
    for key, item in modifications.items() :
        outnode = bld.path.find_or_declare(key)
        for i in item :
            tmpnode = make_tempnode(outnode, bld)
            kw = {'tempcopy' : [tmpnode, outnode]}
            cmd = i[0].replace('${DEP}', tmpnode.bldpath()).replace('${TGT}', outnode.bldpath())
            temp = dict(kw)
            temp.update(i[3])
            if not 'name' in temp : temp['name'] = '%s[%d]%s' % (key, count, cmd.split(' ')[0])
            bld(rule = cmd, source = i[1], shell = i[2], **temp)
            count += 1

def build_rules(bld) :
    for r in rules :
        bld(rule = r[0], source = r[1], target = r[2], shell = r[3], **r[4])


def add_reasons() :
    oldrunner = Task.Task.runnable_status

    def reasonable_runnable(self) :
        res = oldrunner(self)
        Logs.debug("reason: testing %r" % self)
        if res == Task.RUN_ME :
            new_sig = self.signature()
            prev_sig = self.generator.bld.task_sigs.get(self.uid(), '')
            if new_sig != prev_sig :
                Logs.debug("reason: %r runs because its signature (%r) has changed from (%r)" % (self, new_sig, prev_sig))
            for node in self.outputs :
                if getattr(node, 'sig', '') != new_sig :
                    Logs.debug("reason: %r runs because %s (%r) differs from (%r)" % (self, node, getattr(node, 'sig', ''), new_sig))
        return res

#    def hack_postrun(self) :
#        oldpostrun(self)
#        for node in self.outputs :
#            if node.abspath() == "/home/mhosken/Work/MSEA/scripts/script-mymr/fonts/padauk/build/font-source/padauk_src.ttf" :

    Task.Task.runnable_status = reasonable_runnable
def sort_tasks(base) :
    old_biter = base.get_build_iterator

    def top_sort(tasks) :
        if not tasks or len(tasks) < 2 : return tasks
#        print "input: " + str(tasks)
        icntmap = {}
        amap = {}
        roots = []
        for t in tasks :
            icntmap[id(t)] = 0
        for t in tasks :
#            print str(t) + ":--"
            if getattr(t, 'run_after', None) :
                icntmap[id(t)] = len(t.run_after)
                if len(t.run_after) == 0 : roots.append(t)
                for a in t.run_after :
#                    print "     " + str(a)
                    if id(a) in amap :
                        amap[id(a)].append(t)
                    else :
                        amap[id(a)] = [t]
            else :
                roots.append(t)
        res = []
        for r in roots :
            res.append(r)
            if id(r) in amap :
                for a in amap[id(r)] :
                    icntmap[id(a)] -= 1
                    if icntmap[id(a)] == 0 :
                        roots.append(a)
        for t in tasks :
            if icntmap.get(id(t), 0) :
                print "Circular dependency: " + str(t)
                print "   comes after: " + str(t.run_after)
#        print "output: " + str(res)
        return res

    def inject_modifiers(tasks) :
        tmap = {}
        for t in tasks :
            for n in getattr(t, 'outputs', []) :
                tmap[id(n)] = t
        for t in tasks :
            tmpnode, outnode = getattr(t, 'tempcopy', (None, None))
            if outnode :
                if id(outnode) in tmap :
                    t.set_depend_after(tmap[id(outnode)])
#                    print str(t) + " run_after " + str(tmap[id(outnode)])
                tmap[id(outnode)] = t
        for t in tasks :
            for n in getattr(t, 'inputs', []) :
                if id(n) in tmap :
                    t.set_run_after(tmap[id(n)])
#                    print str(t) + " run_after: " + str(tmap[id(n)])

    def wrap_biter(self) :
        for b in old_biter(self) :
#            import pdb; pdb.set_trace()
            inject_modifiers(b)
            tlist = top_sort(b)
            yield tlist

    base.get_build_iterator = wrap_biter

def add_configure() :
    old_config = getattr(Context.g_module, "configure", None)

    def configure(ctx) :
        programs = set()
        for f in Font.fonts :
            programs.update(f.get_build_tools())
        programs.update(font_tests.configure_tests(ctx, Font.fonts))
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
        build_rules(bld)
        for f in Font.fonts :
            f.build(bld)
        build_modifys(bld)

    Context.g_module.build = build

class pdfContext(Build.BuildContext) :
    cmd = 'pdfs'
    func = 'pdfs'

    def pre_build(self) :
        self.add_group('pdfs')
        font_tests.build_tests(self, Font.fonts, 'pdfs')

class svgContext(Build.BuildContext) :
    cmd = 'svg'
    func = 'svg'

    def pre_build(self) :
        self.add_group('svg')
        font_tests.build_tests(self, Font.fonts, 'svg')

class exeContext(Build.BuildContext) :
    cmd = 'exe'

    def pre_build(self) :
        
        thisdir = os.path.dirname(__file__)
        self.add_group('exe')
        # create a taskgen to expand the installer.nsi
        self.env.fonts = Font.fonts
        self.env.basedir = thisdir
        task = templater.Copier(env = self.env)
        task.set_inputs(self.root.find_resource(os.path.join(thisdir, 'installer.nsi')))
        task.set_outputs(self.path.find_or_declare('installer.nsi'))
        self.add_to_group(task)

        # taskgen to run nsismake
        self(rule='makensis -Oinstaller.log ${SRC}', source = 'installer.nsi', target = '%s-%s.exe' % (self.env['DESC_NAME'] or self.env['APPNAME'].title(), self.env['VERSION']))

sort_tasks(Build.BuildContext)
add_configure()
add_build()
add_reasons()
add_depend_after(Task.Task)
Context.g_module.font = Font
Context.g_module.modify = modify
Context.g_module.rule = rule
