#!/usr/bin/python2
''' wsiwaf module '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011-2018 SIL International (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'


from waflib import Context, Task
from .wafplus import *
import os, shlex, re

def formatvars(s, kw=None):
    if isinstance(s, deferred_class):
        return s(kw)
    elif kw is None or not s:
        return s

    def cvt(m):
        return kw.get(m.group(1), '${' + m.group(1) + '}')
    if isinstance(s, str):
        return re.sub(r'\${([a-zA-Z:_/]*)}', cvt, s)
    if hasattr(s, 'items'):
        return dict((k, formatvars(v, kw)) for k,v in s.items())
    elif hasattr(s, '__len__'):
        return [formatvars(x, kw) for x in s]
    return s

class deferred_class(object):
    def __init__(self, c, a, kw):
        self.c = c
        self.a = a
        self.kw = kw

    def __call__(self, kw=None):
        a = [formatvars(x, kw) for x in self.a]
        kwr = dict((k, formatvars(v, kw)) for k,v in self.kw.items())
        return self.c(*a, **kwr)

def defer(c):
    def g(*a, **kw):
        return deferred_class(c, a, kw)
    return g

def undeffered(c):
    def undeffer(*a, **kw):
        newa = list(map(formatvars, a))
        newkw = dict((k, formatvars(v)) for k,v in kw.items())
        return c(*newa, **newkw)
    return undeffer

def isdeferred(c):
    return isinstance(c, deferred_class)

def initval(v):
    return v() if type(v) == 'deferred_class' else v

def initobj(self, kw):
    for k, v in kw.items():
        setattr(self, k, initval(v))

class _create(str) :

    isGenerated = 1
    def __new__(self, tgt, *cmds, **kw) :
        if hasattr(tgt, 'len') : tgt = tgt[0]
        return str.__new__(self, initval(tgt))

    def __init__(self, tgt, *cmds, **kw) :
        tgt = initval(tgt)
        self.cmds = list(map(initval, cmds))
        if len(cmds) > 0 :
            res = cmds[0]()(tgt) if isdeferred(cmds[0]) else cmds[0](tgt)
            res[2].update(kw)
            rule(res[0], res[1], tgt, **res[2])
        for c in cmds[1:] :
            res = c()(tgt) if isdeferred(c) else c(tgt)
            res[2].update(kw)
            modify(res[0], tgt, res[1], **res[2])

    def get_sources(self, ctx) :
        res = []
        for c in self.cmds :
            res.extend(c().get_sources(ctx) if isdeferred(c) else c.get_sources(ctx))
        return res

create = defer(_create)

class _process(_create) :

    def __new__(self, tgt, *cmds, **kw) :
        if not hasattr(tgt, 'len') and os.path.exists(tgt) :
            return super(_process, self).__new__(self, os.path.join("tmp", os.path.basename(tgt)), *cmds, **kw)
        else : return super(_process, self).__new__(self, tgt, *cmds, **kw)

    def __init__(self, tgt, *cmds, **kw) :
        tgt = initval(tgt)
        # if tgt exists in source tree, then become create(munge(tgt), cmd("${CP} ${SRC} ${TGT}", [tgt]), *cmds, **kw)
        if os.path.exists(tgt) :
            cmds = [cmd("cp ${SRC} ${TGT}", [tgt])] + list(cmds)
            tgt = os.path.join("tmp", os.path.basename(tgt))
            super(_process, self).__init__(tgt, *cmds, **kw)
        else :
            self.cmds = list(map(initval, cmds))
            for c in cmds :
                res = c(tgt)
                if 'late' not in res[2]:
                    res[2]['late'] = 1
                elif not res[2]['late']:
                    del res[2]['late']
                res[2].update(kw)
                modify(res[0], tgt, res[1], **res[2])

process = defer(_process)

class test(_process) :

    def __init__(self, tgt, *cmds, **kw) :
        kw['nochange'] = 1
        super(test, self).__init__(tgt, *cmds, **kw)


class _cmd(object) :
    def __init__(self, c, inputs = [], **kw) :
        self.c = initval(c)
        if not isinstance(inputs, list):
            inputs = [inputs]
        self.inputs = list(map(initval, inputs))
        self.opts = dict((k, initval(v)) for k, v in kw.items())

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

cmd = defer(_cmd)

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
            return [x.path_from(ctx.path) for x in n.find_nodes()]
        else :
            return [n.path_from(ctx.path)]
    elif not n :
        return []
    elif os.path.isdir(n.abspath()) :
        return [x.srcpath() for x in n.find_nodes()]
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

@defer
def str_replace(s, i, r):
    return s.replace(i, r)

def onload(ctx) :
    varmap = { 'process' : process, 'create' : create, 'test' : test,
                'cmd' : cmd, 'init' : init, 'str_replace' : str_replace
             }
    for k, v in varmap.items() :
        if hasattr(Context, 'wscript_vars') :
            Context.wscript_vars[k] = v
        else :
            setattr(Context.g_module, k, v)

from . import font, package, keyboard

for m in (font, package, keyboard) :
    if hasattr(m, 'onload') :
        m.onload(Context)
onload(Context)

