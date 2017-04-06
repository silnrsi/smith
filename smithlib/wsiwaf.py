#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Task
from wafplus import *
import os, shlex

class create(str) :

    isGenerated = 1
    def __new__(self, tgt, *cmds, **kw) :
        if hasattr(tgt, 'len') : tgt = tgt[0]
        return str.__new__(self, tgt)

    def __init__(self, tgt, *cmds, **kw) :
        self.cmds = cmds
        if len(cmds) > 0 :
            res = cmds[0](tgt)
            res[2].update(kw)
            rule(res[0], res[1], tgt, **res[2])
        for c in cmds[1:] :
            res = c(tgt)
            res[2].update(kw)
            modify(res[0], tgt, res[1], **res[2])

    def get_sources(self, ctx) :
        #import pdb; pdb.set_trace()
        res = []
        for c in self.cmds :
            res.extend(c.get_sources(ctx))
        return res


class process(create) :

    def __new__(self, tgt, *cmds, **kw) :
        if not hasattr(tgt, 'len') and os.path.exists(tgt) :
            return create.__new__(self, os.path.join("tmp", os.path.basename(tgt)), *cmds, **kw)
        else : return create.__new__(self, tgt, *cmds, **kw)

    def __init__(self, tgt, *cmds, **kw) :
        # if tgt exists in source tree, then become create(munge(tgt), cmd("${CP} ${SRC} ${TGT}", [tgt]), *cmds, **kw)
        if os.path.exists(tgt) :
            cmds = [cmd("cp ${SRC} ${TGT}", [tgt])] + list(cmds)
            tgt = os.path.join("tmp", os.path.basename(tgt))
            super(process, self).__init__(tgt, *cmds, **kw)
        else :
            self.cmds = cmds
            for c in cmds :
                res = c(tgt)
                res[2]['late'] = 1
                res[2].update(kw)
                modify(res[0], tgt, res[1], **res[2])


class test(process) :

    def __init__(self, tgt, *cmds, **kw) :
        kw['nochange'] = 1
        super(test, self).__init__(tgt, *cmds, **kw)

class cmd(object) :
    def __init__(self, c, inputs = [], **kw) :
        self.c = c
        self.inputs = inputs
        self.opts = kw

    def __call__(self, tgt) :
        return (self.c, self.inputs, self.opts)

    def get_sources(self, ctx) :
        res = get_all_sources(self, ctx, 'inputs')
        c = shlex.split(self.parse(ctx))[0]
        if not os.path.isabs(c) :
            n = ctx.bldnode.find_node(c)
            if n and not n.is_child_of(ctx.bldnode) :
                pat = n.abspath()
                res.append(n.srcpath())
        return res

    def parse(self, ctx, kw = None) :
        if kw is None : kw = self.opts
        def repl(match) :
            g = match.group
            if g('dollar') : return '$'
            elif g('backslash') : return '\\\\'
            elif g('subst') :
                if not g('code') and g('var') in kw :
                    return kw[g('var')]
                else : return '${' + g('var') + g('code') + '}'
        return Task.reg_act.sub(repl, self.c)

    def build(self, ctx, inputs, tgt, **kw) :
        return ctx(rule = self.parse(ctx, kw), source = inputs, target = tgt)

def isList(l) :
    return (not hasattr(l, 'strip') and
                hasattr(l, '__getitem__') and
                hasattr(l, '__iter__'))

def _get_source(self, ctx, a) :
    n = ctx.path.find_node(a)
    if not hasattr(ctx, 'bldnode') : # then we are a simple context
        if not n :
            return []
        elif os.path.isdir(n.abspath()) :
            return map(lambda x: x.path_from(ctx.path), n.find_nodes())
        else :
            return [n.path_from(ctx.path)]
    elif not n :
        return []
    elif os.path.isdir(n.abspath()) :
        return map(lambda x: x.srcpath(), n.find_nodes())
    else :
        return [n.srcpath()]

def get_all_sources(self, ctx, *attrs) :
    res = []
    for a in (getattr(self, x, None) for x in attrs) :
        if a :
            if hasattr(a, 'get_sources') :
                res.extend(a.get_sources(ctx))
            elif isList(a) :
                for t in a :
                    res.extend(_get_source(self, ctx, t))
            else :
                res.extend(_get_source(self, ctx, a))
    return res
        
def init(ctx) :
    for m in (font, package, keyboard) :
        if hasattr(m, 'init') :
            m.init(ctx)
        
def onload(ctx) :
    varmap = { 'process' : process, 'create' : create, 'test' : test,
                'cmd' : cmd, 'init' : init
             }
    for k, v in varmap.items() :
        if hasattr(Context, 'wscript_vars') :
            Context.wscript_vars[k] = v
        else :
            setattr(Context.g_module, k, v)

import font, package, keyboard

for m in (font, package, keyboard) :
    if hasattr(m, 'onload') :
        m.onload(Context)
onload(Context)

