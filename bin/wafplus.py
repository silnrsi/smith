#!/usr/bin/python

from waflib import Task, Build, Logs, Context, Utils, Configure, Options
import os, imp, operator, optparse, sys
from waflib.TaskGen import feature, after

def preprocess_args(*opts) :
    res = {}
    for o in opts:
        for a in sys.argv :
            if a.startswith(o['opt']) :
                key, val = a.split('=')
                if val :
                    res[key] = val
                else :
                    res[key] = 1
                sys.argv.remove(a)
    return res

def add_intasks(base) :
    """ task.intasks contains a list of other tasks on which this task is
        dependent. Thus if the other task changes signature, then this task
        will run, regardless of other dependencies. In fact that other task's
        signature is part of this task's signature.
    """
    old_sig = base.signature

    def sig(task) :
        try: return task.cache_sig
        except AttributeError: pass

        res = old_sig(task)
        for t in getattr(task, 'intasks', []) :
            task.m.update(t.signature())
        res = task.cache_sig = task.m.digest()
        return res

    base.signature = sig

@feature('*')
@after('process_rule')
def process_tempcopy(tgen) :
    """ Wrap the task function to do the tempcopy """
    import os, shutil
    if not getattr(tgen, 'tempcopy', None) : return

    (tmpnode, outnode) = tgen.tempcopy
    tmpnode.parent.mkdir()
    for t in tgen.tasks :
        t.tempcopy = tgen.tempcopy
        if hasattr(tgen, 'dep') : 
            t.dep = tgen.dep
            t.tgt = outnode
        fn = t.__class__.run
        def f(self) :
            if os.path.exists(tmpnode.abspath()) :
                os.remove(tmpnode.abspath())
            Logs.debug("runner: " + outnode.abspath() + "-->" + tmpnode.abspath())
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

@feature('*')
@after('process_rule')
def process_taskgens(tg) :
    for o in getattr(tg, 'taskgens', []) :
        og = tg.bld.get_tgen_by_name(o)
        if not og : continue
        if not og.posted : og.post()
        if og :
            t = tg.tasks[0]
            ot = og.tasks[-1]
            try: t.intasks.append(ot)
            except AttributeError : t.intasks = [ot]
            if og in tg.bld.get_group(None) :
                t.set_run_after(ot)

modifications = {}
rules = []

def modify(cmd, infile, inputs = [], shell = 0, **kw) :
    """ modify taskgens are tasks with no formal output, although one is
        given. This output is modified in place. For input purposes it
        is referred to ${DEP} in the cmd, and ${TGT}. A modify task may also
        have other inputs ${SRC}.
    """
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
            temp = dict(kw)
            if isinstance(i[0], basestring) :
                cmd = i[0].replace('${DEP}', tmpnode.bldpath()).replace('${TGT}', outnode.bldpath())
                if not 'name' in temp : temp['name'] = '%s[%d]%s' % (key, count, cmd.split(' ')[0])
            else :
                temp['dep'] = tmpnode
                cmd = i[0]
                if not 'name' in temp : temp['name'] = '%s[%d]' % (key, count)
            temp.update(i[3])
            bld(rule = cmd, source = i[1], shell = i[2], **temp)
            count += 1

def build_rules(bld) :
    for r in rules :
        bld(rule = r[0], source = r[1], target = r[2], shell = r[3], **r[4])


def add_reasons() :
    """ adds support for --zones=reason """
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

def add_sort_tasks(base) :
    old_biter = base.get_build_iterator

    def top_sort(tasks) :
        """ Topologically sort the tasks so that they are processed in
            dependency order. Regardless of what order they were created in. """
        if not tasks or len(tasks) < 2 : return tasks
        icntmap = {}
        amap = {}
        roots = []
        for t in tasks :
            icntmap[id(t)] = 0
        for t in tasks :
            if getattr(t, 'run_after', None) :
                icntmap[id(t)] = len(t.run_after)
                if len(t.run_after) == 0 : roots.append(t)
                for a in t.run_after :
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
                res.append(t)
        Logs.debug("order: " + "\n".join(map(repr,res)))
        for r in res :
            Logs.debug("after: " + str(r) + " comes after " + str(r.run_after))
        return res

    def inject_modifiers(tasks) :
        """ Sort out run_after dependency tree taking modifiers into account.
            Works out where in a chain of modifications a particular dependant task
            should have its direct run_after dependency set. Such tasks are set as
            late in the chain as possible. """
        tmap = {}
        for t in tasks :
            for n in getattr(t, 'outputs', []) :
                tmap[id(n)] = [t]
        for t in tasks :
            tmpnode, outnode = getattr(t, 'tempcopy', (None, None))
            if outnode :
                if id(outnode) in tmap :
                    try: t.intasks.append(tmap[id(outnode)][-1])
                    except AttributeError : t.intasks = [tmap[id(outnode)][-1]]
                    t.set_run_after(tmap[id(outnode)][-1])
                    tmap[id(outnode)].append(t)
                else :
                    tmap[id(outnode)] = [t]
        for t in tasks :
            for n in getattr(t, 'inputs', []) :
                if id(n) in tmap :
                    entry = tmap[id(n)]
                    res = len(entry) - 1
                    for i in range(res + 1) :
                        if entry[i].runs_after(t) :
                            res = i - 1
                            break
                    t.set_run_after(entry[res])

    def wrap_biter(self) :
        for b in old_biter(self) :
            inject_modifiers(b)
            tlist = top_sort(b)
            yield tlist

    base.get_build_iterator = wrap_biter
    Task.TaskBase.runs_after = runs_after

def runs_after(self, task, cache = set()) :
    """ Returns whether this task must run after another task based on run_after """
    res = False
    for t in self.run_after :
        if t == task : return True
        if not id(t) in cache :
            cache.add(id(t))
            res = res or t.runs_after(task, cache = cache)
    return res

def add_build_wafplus() :
    old_prerecurse = Build.BuildContext.pre_recurse
    old_postrecurse = Build.BuildContext.post_recurse
    old_exec = Build.BuildContext.execute

    def pre_recurse(bld, node) :
        old_prerecurse(bld, node)
        build_rules(bld)

    def post_recurse(bld, node) :
        old_postrecurse(bld, node)
        build_modifys(bld)

    def execute(bld) :
        if Options.options.dot :
            return make_dot(bld)
        else :
            return old_exec(bld)

    Build.BuildContext.pre_recurse = pre_recurse
    Build.BuildContext.post_recurse = post_recurse
    Build.BuildContext.execute = execute

def add_unicode_exec() :
    """ tweak to allow commands to be passed unicode strings and to run
        commands containing unicode characters
    """
    old_exec = Context.Context.exec_command

    def unicode_exec_command(self, cmd, **kw) :
        if isinstance(cmd, str) :
            cmd = cmd.decode('utf_8')
        elif isinstance(cmd, list) :
            cmd = map (operator.methodcaller('decode', 'utf_8'), cmd)
        old_exec(self, cmd, **kw)

    Context.Context.exec_command = unicode_exec_command

def add_options() :
    """ Add the --dot option to generate wscript.dot of the given command
        listing all the tasks and their dependency relationships
    """
    oldinit = Options.opt_parser.__init__

    def init(self, ctx) :
        oldinit(self, ctx)
        gr = optparse.OptionGroup(self, 'wafplus options')
        self.add_option_group(gr)
        gr.add_option('--dot', action = 'store_true', help = 'create wscript.dot of build tasks for this command')

    Options.opt_parser.__init__ = init

def make_dot(self):
    self.restore()
    if not self.all_envs:
        self.load_envs()
    self.recurse([self.run_dir])
    self.pre_build()
    self.timer=Utils.Timer()
    tasks = []
    for t in self.get_build_iterator() :
        if len(t) > 0 :
            tasks.extend(t)
        else :
            break
    ofh = open("wscript.dot", "w")
    ofh.write("digraph tasks { rankdir=BT;\n")
    tmap = {}
    count = 0
    for l in tasks :
        nname = "n" + str(count)
        tmap[id(l)] = nname
        count += 1
        ofh.write("    " + nname + ' [label="' + l.name + '"];\n')
    for l in tasks :
        for d in l.run_after :
#                print "    " + tmap[d.name] + " -> " + tmap[l.name]
            ofh.write("    " + tmap[id(l)] + " -> " + tmap[id(d)] + ";\n")
    ofh.write("}\n")

    g = []
    self.group_names['dot'] = g
    self.groups = [g]       # delete all the tasks except ours
    self.set_group(0)
#        self(cmd='echo Create wscript.dot', target='wscript.dot', shell = 1)
    self(rule='${DOT} -Tps -o ${TGT} ${SRC}', source='wscript.dot', target='wscript.ps', shell=1)

    self.compile()


def load_module(file_path) :
    """ Add global pushing to WSCRIPT when it loads """
    try:
        return Context.cache_modules[file_path]
    except KeyError:
        pass

    module = imp.new_module(Context.WSCRIPT_FILE)
    try:
        code = Utils.readf(file_path, m='rU')
    except (IOError, OSError) :
        raise Errors.WafError('Could not read the file %r' % file_path)

    module_dir = os.path.dirname(file_path)
    sys.path.insert(0, module_dir)

    for k, v in Context.wscript_vars.items() : setattr(module, k, v)

    Context.g_module = module
    try:
        exec(code, module.__dict__)
    except Exception as e:
        raise Errors.WafError(ex=a, pyfile=file_path)
    sys.path.remove(module_dir)

    Context.cache_modules[file_path] = module
    return module

add_sort_tasks(Build.BuildContext)
add_reasons()
add_intasks(Task.Task)
add_build_wafplus()
add_options()
#add_unicode_exec()
Context.load_module = load_module
Context.wscript_vars = {}
varmap = { 'modify' : modify,
            'rule' : rule,
            'preprocess_args' : preprocess_args }
for k, v in varmap.items() :
    Context.wscript_vars[k] = v

