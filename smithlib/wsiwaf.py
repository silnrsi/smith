#!/usr/bin/python
# Martin Hosken 2011

from waflib import Context
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

def cmd(c, inputs = [], **kw) :
    def icmd(tgt) :
        return (c, inputs, kw)
    return icmd

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

