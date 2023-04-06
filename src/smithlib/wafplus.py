#!/usr/bin/env python3
''' wafplus module '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011-2018 SIL International (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'



from waflib import Task, Build, Logs, Context, Utils, Configure, Options, Errors, Node
import os, imp, operator, optparse, sys, re, shlex
from waflib.TaskGen import feature, after

def _parsearg(a, o, res):
    if a.startswith(o['opt']) :
        if '=' in a :
            key, val = a.split('=')
            res[key.strip()] = val.strip()
        else :
            res[a.strip()] = 1
        return True
    return False

def preprocess_args(*opts) :
    res = {}
    oldenvstr = os.getenv("SMITHARGS")
    envargs = shlex.split(oldenvstr) if oldenvstr is not None else []
    for o in opts:
        for a in sys.argv:
            if _parsearg(a, o, res):
                sys.argv.remove(a)
        for a in envargs:
            if _parsearg(a, o, res):
                envargs.remove(a)
    envstr = " ".join(envargs)
    if oldenvstr is not None and oldenvstr != "":
        if envstr == "":
            del os.environ["SMITHARGS"]
        else:
            os.environ["SMITHARGS"] = envstr
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
            if outnode.is_bld() and os.path.exists(outnode.abspath()) :
                Logs.debug("runner: moving")
                shutil.move(outnode.abspath(), tmpnode.abspath())
            else :
                sourcenode = outnode.get_src()
                Logs.debug("runner: Can't copy built, copying " + str(sourcenode.abspath()))
                shutil.copy2(sourcenode.abspath(), tmpnode.abspath())
                t.outputs.append(outnode.get_bld())
            ret = fn(self)
            if not ret : os.remove(tmpnode.abspath())
            return ret
        t.__class__.run = f

@feature('*')
@after('process_rule')
def process_taskgens(tg) :
    """ process taskgens attribute to create intasks relationships in the task
    """
    for o in getattr(tg, 'taskgens', []) :
        try :
            og = tg.bld.get_tgen_by_name(o)
        except Errors.WafError :
            continue
        if not og : continue
        if not og.posted : og.post()
        if og :
            t = tg.tasks[0]
            ot = og.tasks[-1]
            try: t.intasks.append(ot)
            except AttributeError : t.intasks = [ot]
            #if og in tg.bld.get_group(None) :
            t.set_run_after(ot)

    if hasattr(tg, 'deps') :
        for d in getattr(tg, 'deps', []) :
            n = tg.bld.path.find_resource(d)
            tg.tasks[0].dep_nodes.append(n)
        tg.deps = []

modifications = {}
rules = {}

def getpath() :
    src = Context.wscript_vars.get('src', None)
    if src :
        return src('wscript')
    else :
        return os.path.abspath('wscript')

def modify(cmd, infile, inputs = [], shell = 0, path = None, **kw) :
    """ modify taskgens are tasks with no formal output, although one is
        given. This output is modified in place. For input purposes it
        is referred to ${DEP} in the cmd, and ${TGT}. A modify task may also
        have other inputs ${SRC}.
    """
    # can't create taskgens here because we have no bld context
    if not path : path = os.path.abspath(getpath())
    if path not in modifications :
        modifications[path] = {}
    if isinstance(infile, list) :
        inf = infile[0]
        if len(infile) > 1 :
            kw['targets'] = infile[1:]
    else : inf = str(infile)
    if not inf in modifications[path] :
        modifications[path][inf] = []
    if not len(inputs) : shell = 1      # workaround assert in Task.py
    # print(path, inf, cmd, inputs, kw)
    modifications[path][inf].append((cmd, inputs, shell, kw))

def ismodified(infile, path = None) :
    if not path : path = getpath()
    if path not in modifications : return False
    return infile in modifications[path]

def rule(cmd, inputs, outputs, shell = 0, path = None, **kw) :
    if not path : path = getpath()
    if path not in rules :
        rules[path] = []
    rules[path].append((cmd, inputs, outputs, shell, kw))

def make_tempnode(n, bld) :
    path = ".tmp" + os.sep + n.get_bld().bld_dir()
    tdir = bld.bldnode.abspath() + os.sep + path
    if not os.path.exists(tdir) :
        os.makedirs(tdir, 0o771)
    res = bld.bldnode.find_or_declare(path + os.sep + n.name)
    return res

def build_modifys(bld) :
    path = bld.srcnode.find_node('wscript').abspath()
    if path not in modifications : return
    count = 0
    for key, item in modifications[path].items() :
        def local_cmp(a, b) :
            if 'late' in item[a][3] :
                if 'late' in item[b][3] : return cmp(a, b)
                return 1
            elif 'late' in item[b][3] :
                return -1
            else :
                return cmp(a, b)
        outnode = bld.path.find_or_declare(key)
        # print(key, len(item))
        for i in sorted(range(len(item)), key=lambda x:(item[x][3].get('late', 0), x)):
            # print(i, item[i])
            tmpnode = make_tempnode(outnode, bld)
            if 'nochange' in item[i][3] :
                kw = {}
            else :
                kw = {'tempcopy' : [tmpnode, outnode]}
            temp = dict(kw)
            if isinstance(item[i][0], str) :
                cmd = item[i][0].replace('${DEP}', tmpnode.bldpath()).replace('${TGT}', outnode.get_bld().bldpath())
                cmd = re.sub(r'\${TGT\[([0-9])\]([^}]*)}', lambda m: "${TGT["+str(int(m.group(1))-1)+"]"+m.group(2)+"}" if m.group(1) != "0" else outnode.get_bld().bldpath(), cmd)
                if not 'name' in temp : temp['name'] = '%s[%d]%s' % (key, count, cmd.split(' ')[0])
            else :
                temp['dep'] = tmpnode
                cmd = item[i][0]
                if not 'name' in temp : temp['name'] = '%s[%d]' % (key, count)
            temp.update(item[i][3])
            if 'targets' in temp :
                if len(temp['targets']) > 1:
                    temp['target'] = temp['targets'][0]
                    temp['targets'] = temp['target'][1:]
                else:
                    temp['target'] = temp['targets']
                    del temp['targets']
            bld(rule = cmd, source = item[i][1], shell = item[i][2], **temp)
            count += 1
    del modifications[path]

def build_rules(bld) :
    path = bld.srcnode.find_node('wscript').abspath()
    if path in rules :
        for r in rules[path] :
            for t in (r[2] if hasattr(r[2], 'len') else [r[2]]) :
                c = bld.bldnode.find_or_declare(t)
                if not c.is_bld() and 'nochange' not in r[4] :
                    raise Errors.WafError("Cannot create() already existing file: %s" % t)
            bld(rule = r[0], source = r[1], target = r[2], shell = r[3], **r[4])
        del rules[path]

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
            if icntmap.get(id(t), 0):
                if any(icntmap.get(id(x), 0) for x in t.run_after):
                    print("Circular dependency: " + str(t))
                    print("   comes after: " + str(t.run_after))
                res.append(t)
        Logs.debug("order: " + "\n".join(map(repr,res)))
        for r in res :
            Logs.debug("after: " + str(r) + " comes after " + str(r.run_after))
        return res

    def inject_modifiers(tasks) :
        """ Sort out run_after dependency tree taking modifiers into account.
            Works out where in a chain of modifications a particular dependent task
            should have its direct run_after dependency set. Such tasks are set as
            late in the chain as possible. """
        tmap = {}
        for t in tasks :
            for n in getattr(t, 'outputs', []) :
                if id(n) not in tmap : tmap[id(n)] = []
                tmap[id(n)].append(t)
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
                    res = len(entry)
                    for i in range(res) :
                        if entry[i].runs_after(t) or id(entry[i]) == id(t) :
                            res = i
                            break
                    if res :
                        e = entry[res - 1]
                        try: t.intasks.append(e)
                        except AttributeError : t.intasks = [e]
                        t.set_run_after(e)

    def wrap_biter(self) :
        for b in old_biter(self) :
            inject_modifiers(b)
#            print(b)
            tlist = top_sort(b)
            yield tlist
#            yield b

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
    old_pre_recurse = Context.Context.pre_recurse

    def cpre_recurse(ctx, node) :
        def src(path) :
            return ctx.srcnode.find_node(path).srcpath()
        Context.wscript_vars['src'] = src
        if old_pre_recurse : old_pre_recurse(ctx, node)

    Context.Context.pre_recurse = cpre_recurse
    old_prerecurse = Build.BuildContext.pre_recurse
    old_prebuild = Build.BuildContext.pre_build
    old_exec = Build.BuildContext.execute

    def pre_recurse(bld, node) :
        old_prerecurse(bld, node)
        build_rules(bld)
#        super(Build.BuildContext, bld).pre_recurse(node)

    def pre_build(bld) :
        old_prebuild(bld)
        build_modifys(bld)

    def execute(bld) :
        if Options.options.dot :
            return make_dot(bld)
        else :
            return old_exec(bld)

    Build.BuildContext.pre_recurse = pre_recurse
    Build.BuildContext.pre_build = pre_build
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
            cmd = list(map (operator.methodcaller('decode', 'utf_8'), cmd))
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
        gr.add_option('--debug', action = 'store_true', help = 'break out into the debugger')
        gr.add_option('-r','--release', action = 'store_true', help = 'Build for release, no special version numbers')
        gr.add_option('--standards', help = 'Alternative source of base files for testing')
        gr.add_option('--extratestdir', help = 'Set the EXTRATESTDIR from a ; separated list of paths')

    Options.opt_parser.__init__ = init

def patch_waf() :
    """ Patch various waflib methods and functions:
            Node.find_resource
            Utils.h_file
    """
    def find_resource(self, lst):
        if isinstance(lst, str):
            lst = [x for x in Node.split_path(lst) if x and x != '.']

        node = self.get_bld().search(lst)
        if not node:
            self = self.get_src()
            node = self.search(lst)
            if not node:
                node = self.find_node(lst)
        return node
    Node.Node.find_resource = find_resource

    def h_file(filename) :
        m = Utils.md5()
        if os.path.isdir(filename) :
            for (dp, ds, fs) in os.walk(filename) :
                st = os.stat(dp)
                m.update(str(st.st_mtime).encode("utf-8"))
                m.update(str(st.st_size).encode("utf-8"))
                m.update(dp.encode("utf-8"))
        else :
            f = open(filename, 'rb')
            try :
                while filename :
                    filename = f.read(100000)
                    m.update(filename)
            finally :
                f.close()
        return m.digest()
    Utils.h_file = h_file

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
    for t in tasks :
        nname = "n" + str(count)
        tmap[id(t)] = nname
        count += 1
        name = getattr(t, 'name', str(type(t)))
        ofh.write("    " + nname + ' [label="' + name + '"];\n')
        for a in ('inputs', 'outputs', 'dep_nodes') :
            l = getattr(t, a, [])
            if not len(l) : continue
            for n in l :
                if id(n) not in tmap :
                    nname = "f" + str(count)
                    count += 1
                    tmap[id(n)] = nname
                    name = os.path.relpath(repr(n))
                    ofh.write("    " + nname + ' [label="' + name + '",shape=box];\n')
    for t in tasks :
        for d in t.run_after :
            ofh.write("    " + tmap[id(t)] + " -> " + tmap[id(d)] + "[style=dashed];\n")
        for a in ('inputs', 'dep_nodes', 'outputs') :
            l = getattr(t, a, [])
            if not len(l) : continue
            for n in l :
                if a == 'outputs' :
                    ofh.write("    " + tmap[id(n)] + " -> " + tmap[id(t)] + ";\n")
                else :
                    ofh.write("    " + tmap[id(t)] + " -> " + tmap[id(n)] + ";\n")
    ofh.write("}\n")
    ofh.close()

    g = []
    self.group_names['dot'] = g
    self.groups = [g]       # delete all the tasks except ours
    self.set_group(0)
#        self(cmd='echo Create wscript.dot', target='wscript.dot', shell = 1)
    self(rule='/usr/bin/dot -Tps -o ${TGT} ${SRC}', source=['wscript.dot'], target='wscript.ps', shell=True)

    self.compile()

def nulltask(task):
    return 0

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
    if not hasattr(module, 'src') :
        def src(x) :
            import os.path
            return os.path.abspath(x)
        module.src = src

    Context.g_module = module
    exec(compile(code, file_path, 'exec'), module.__dict__)
    sys.path.remove(module_dir)
    if not hasattr(module, 'root_path') : module.root_path = file_path

    Context.cache_modules[file_path] = module
    return module

add_sort_tasks(Build.BuildContext)
add_reasons()
add_intasks(Task.Task)
add_build_wafplus()
add_options()
patch_waf()
#add_unicode_exec()
Context.load_module = load_module
Context.wscript_vars = {}
varmap = { 'modify' : modify,
            'rule' : rule,
            'preprocess_args' : preprocess_args }
for k, v in varmap.items() :
    if k not in Context.wscript_vars : Context.wscript_vars[k] = v

