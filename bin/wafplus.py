#!/usr/bin/python

from waflib import Task, Build, Logs, Context
import os
from waflib.TaskGen import feature, after

def add_depend_after(base) :
    old_runnable_status = base.runnable_status
    old_post_run = base.post_run

    def runnable_status(self) :
        """ A depend_after relationship between two tasks says that if the 
            first task runs then that is a sufficient condition to make the
            second task run. This is because the first task may create the
            file the second task uses, but give it the same task signature
            it had before, thus the second task may not fire based on the
            file signature alone
        """
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

    base.runnable_status = runnable_status
    base.set_depend_after = set_depend_after

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

def add_build_wafplus() :
    old_prerecurse = Build.BuildContext.pre_recurse
    old_postrecurse = Build.BuildContext.post_recurse

    def pre_recurse(bld, node) :
        old_prerecurse(bld, node)
        build_rules(bld)

    def post_recurse(bld, node) :
        old_postrecurse(bld, node)
        build_modifys(bld)

    Build.BuildContext.pre_recurse = pre_recurse
    Build.BuildContext.post_recurse = post_recurse

sort_tasks(Build.BuildContext)
add_reasons()
add_depend_after(Task.Task)
Context.g_module.modify = modify
Context.g_module.rule = rule
add_build_wafplus()

