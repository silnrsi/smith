"Yet Another Python Templating Utility, Version 1.2"

import sys, re, os
from waflib import Task 

# utility stuff to avoid tests in the mainline code
def identity(string, why):
    "A do-nothing-special-to-the-input, just-return-it function"
    return string
def nohandle(string):
    "A do-nothing handler that just re-raises the exception"
    raise

# and now the real thing
class Copier(Task.Task):
    "Smart-copier (YAPTU) class"
    def copyblock(self, i=0, last=None):
        "Main copy method: process lines [i,last) of block"
        def repl(match, self=self):
            "return the eval of a found expression, for replacement"
            # uncomment for debug: print '!!! replacing',match.group(1)
            # expr = self.preproc(match.group(1), 'eval')
            #try: return str(eval(expr, self.globals, self.locals))
            return str(eval(match.group(1), self.globals, self.locals))
            #except: return str(self.handle(expr))
        block = self.locals['_bl']
        if last is None: last = len(block)
        while i<last:
            line = block[i]
            match = self.restat.match(line)
            if match:   # a statement starts "here" (at line block[i])
                # i is the last line to _not_ process
                stat = match.string[match.end(0):].strip()
                j=i+1   # look for 'finish' from here onwards
                nest=1  # count nesting levels of statements
                while j<last:
                    line = block[j]
                    # first look for nested statements or 'finish' lines
                    if self.restend.match(line):    # found a statement-end
                        nest = nest - 1     # update (decrease) nesting
                        if nest==0: break   # j is first line to _not_ process
                    elif self.restat.match(line):   # found a nested statement
                        nest = nest + 1     # update (increase) nesting
                    elif nest==1:   # look for continuation only at this nesting
                        match = self.recont.match(line)
                        if match:                   # found a contin.-statement
                            nestat = match.string[match.end(0):].strip()
                            stat = '%s _cb(%s,%s)\n%s' % (stat,i+1,j,nestat)
                            i=j     # again, i is the last line to _not_ process
                    j=j+1
                # stat = self.preproc(stat, 'exec')
                stat = '%s _cb(%s,%s)' % (stat,i+1,j)
                # print "-> Executing: {"+stat+"}"
                exec stat in self.globals,self.locals
                i=j+1
            else:       # normal line, just copy with substitution
                self.outf.write(self.regex.sub(repl,line))
                i=i+1

    def __init__(self,  *k, **kw) :
        "Initialize self's attributes"
        Task.Task.__init__(self, *k, **kw)
        self.vars = kw
        self.regex   = re.compile(kw.get('regex', '(?<!@)@([^@]+)@'))
        self.locals  = { '_cb':self.copyblock }
        self.restat  = re.compile(kw.get('restat', '\+'))
        self.restend = re.compile(kw.get('restend', '-'))
        self.recont  = re.compile(kw.get('recont', '= '))

    def run(self) :
        self.locals['_bl'] = [t + "\n" for t in self.inputs[0].read().split('\n')]
        self.globals = { 'gen' : self.generator, 'ctx' : self.generator.bld, 'task' : self, 'os' : os }
        for k, v in self.vars.items() : self.globals[k] = v
        self.outf = open(self.outputs[0].abspath(), "w")
#        import pdb; pdb.set_trace()
        self.copyblock()
        self.outf.close()
        return 0

