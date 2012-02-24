#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context, Task
from wafplus import *
import font, package, keyboard

def init(ctx) :
    for m in (font, package, keyboard) :
        if hasattr(m, 'init') :
            m.init(ctx)

def process(tgt, *cmds, **kw) :
    for c in cmds :
        res = c(tgt)
        modify(res[0], tgt, res[1], **res[2])
    return tgt

def create(tgt, *cmds, **kw) :
    if len(cmds) > 0 :
        res = cmds[0](tgt)
        rule(res[0], res[1], tgt, **res[2])
    for c in cmds[1:] :
        res = c(tgt)
        modify(res[0], tgt, res[1], **res[2])
    return tgt

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
        
def onload(ctx) :
    varmap = { 'process' : process, 'create' : create, 'cmd' : cmd, 
               'init' : init
             }
    for k, v in varmap.items() :
        if hasattr(Context, 'wscript_vars') :
            Context.wscript_vars[k] = v
        else :
            setattr(Context.g_module, k, v)

for m in (font, package, keyboard) :
    if hasattr(m, 'onload') :
        m.onload(Context)
onload(Context)

