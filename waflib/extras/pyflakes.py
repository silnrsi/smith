#! /usr/bin/env python
# encoding: utf-8
#
# written by Sylvain Rouquette, 2011

'''
Install pyflakes module:
$ easy_install pyflakes
    or
$ pip install pyflakes

To add the boost tool to the waf file:
$ ./waf-light --tools=compat15,pyflakes
    or, if you have waf >= 1.6.2
$ ./waf update --files=pyflakes


Then add this to your wscript:

[at]extension('.py', 'wscript')
def run_pyflakes(self, node):
    self.create_task('PyFlakes', node)

'''

import compiler
from waflib import TaskGen, Task, Options, Logs

pyflakes = __import__('pyflakes.checker')


class PyFlakes(Task.Task):
    color = 'PINK'

    def run(self):
        tree = compiler.parse(self.inputs[0].read())
        w = pyflakes.checker.Checker(tree, self.inputs[0].abspath())
        if len(w.messages):
            for warning in w.messages:
                Logs.warn(warning)
