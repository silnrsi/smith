#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Task
from wafplus import *

class create(str) :

    isGenerated = 1
    def __new__(self, tgt, *cmds, **kw) :
        return str.__new__(self, tgt)

    def __init__(self, tgt, *cmds, **kw) :
        self.cmds = cmds
        if len(cmds) > 0 :
            res = cmds[0](tgt)
            rule(res[0], res[1], tgt, **res[2])
        for c in cmds[1:] :
            res = c(tgt)
            modify(res[0], tgt, res[1], **res[2])

    def get_sources(self, ctx) :
        res = []
        for c in self.cmds :
            for i in c.inputs :
                if hasattr(i, 'get_sources') :
                    res.extend(i.get_sources(ctx))
                else :
                    res.append(i)
        return res


class process(create) :

    def __init__(self, tgt, *cmds, **kw) :
        self.cmds = cmds
        for c in cmds :
            res = c(tgt)
            modify(res[0], tgt, res[1], **res[2])


class cmd(object) :
    def __init__(self, c, inputs = [], **kw) :
        self.c = c
        self.inputs = inputs
        self.opts = kw

    def __call__(self, tgt) :
        return (self.c, self.inputs, self.opts)

    def build(self, ctx, inputs, tgt, **kw) :
        def repl(match) :
            g = match.group
            if g('dollar') : return '$'
            elif g('backslash') : return '\\\\'
            elif g('subst') :
                if not g('code') and g('var') in kw :
                    return kw[g('var')]
                else : return '${' + g('var') + g('code') + '}'
        if kw : c = Task.reg_act.sub(repl, self.c)
        return ctx(rule = c, source = inputs, target = tgt)


def get_all_sources(self, ctx, *attrs) :
    res = []
    for a in (getattr(self, x, None) for x in attrs) :
        if a :
            if hasattr(a, 'get_sources') :
                res.extend(a.get_sources(ctx))
            else :
                res.append(a)
    return res
        
def init(ctx) :
    for m in (font, package, keyboard) :
        if hasattr(m, 'init') :
            m.init(ctx)
        
def onload(ctx) :
    varmap = { 'process' : process, 'create' : create, 'cmd' : cmd, 
               'init' : init
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

