#! /usr/bin/env python
# encoding: utf-8
#
# easy_install pyflakes
# or
# pip install pyflakes
#
# written by Sylvain Rouquette, 2011

import compiler
from waflib import TaskGen, Task, Options, Logs

pyflakes = __import__('pyflakes.checker')


@TaskGen.extension('.py', 'wscript')
def run_pyflakes(self, node):
    self.create_task('PyFlakes', node)


class PyFlakes(Task.Task):
    color = 'PINK'

    def run(self):
        tree = compiler.parse(self.inputs[0].read())
        w = pyflakes.checker.Checker(tree, self.inputs[0].abspath())
        if len(w.messages):
            for warning in w.messages:
                Logs.warn(warning)
